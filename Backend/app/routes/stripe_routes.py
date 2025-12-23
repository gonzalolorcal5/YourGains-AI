# app/routes/stripe_routes.py
from fastapi import APIRouter, HTTPException, Request, Depends, Header
from sqlalchemy.orm import Session
import traceback
import logging
from app.database import get_db
from app.models import Usuario
from app.auth_utils import get_user_id_from_token
from pydantic import BaseModel
import os
import stripe
from dotenv import load_dotenv

router = APIRouter(tags=["stripe"])
logger = logging.getLogger(__name__)

# === Config Stripe / Entorno ===
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))
STRIPE_SECRET = os.getenv("STRIPE_SECRET_KEY")
if not STRIPE_SECRET:
    print("⚠️ STRIPE no configurado - Modo desarrollo activado")
    STRIPE_SECRET = "sk_test_placeholder"
stripe.api_key = STRIPE_SECRET

# URLs y price IDs
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:8000/frontend").rstrip("/")
PRICE_ID_MENSUAL = os.getenv("STRIPE_PRICE_MENSUAL")
PRICE_ID_ANUAL = os.getenv("STRIPE_PRICE_ANUAL")
ALLOWED_PRICE_IDS = {p for p in [PRICE_ID_MENSUAL, PRICE_ID_ANUAL] if p}
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")

# Models
class CheckoutSessionRequest(BaseModel):
    price_id: str

class PaymentIntentRequest(BaseModel):
    plan_type: str  # 'monthly' o 'yearly'
    price_id: str

# ==========================================
# CHECKOUT SESSION
# ==========================================
@router.post("/create-checkout-session")
async def create_checkout_session(
    data: CheckoutSessionRequest,
    user_id: int = Depends(get_user_id_from_token),
    db: Session = Depends(get_db)
):
    """
    Crea sesión de Stripe Checkout para suscripción.
    Requiere autenticación JWT.
    """
    if not ALLOWED_PRICE_IDS:
        raise HTTPException(
            status_code=500,
            detail="Precios Stripe no configurados en .env"
        )
    
    if data.price_id not in ALLOWED_PRICE_IDS:
        raise HTTPException(status_code=400, detail="price_id inválido")
    
    # Obtener usuario
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    try:
        # Crear o reutilizar customer
        customer_id = user.stripe_customer_id
        if not customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={"user_id": str(user_id)}
            )
            customer_id = customer.id
            user.stripe_customer_id = customer_id
            db.commit()
            logger.info(f"✅ Customer creado: {customer_id} para user {user_id}")
        
        # Crear sesión de checkout
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": data.price_id, "quantity": 1}],
            success_url=f"{FRONTEND_URL}/tarifas.html?success=1&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/tarifas.html?cancel=1",
            allow_promotion_codes=True,
            metadata={"user_id": str(user_id)},
            subscription_data={"metadata": {"user_id": str(user_id)}}
        )
        
        logger.info(f"✅ Checkout session creada: {session.id} para user {user_id}")
        return {"url": session.url}
        
    except stripe.error.StripeError as e:
        logger.error(f"Error Stripe: {e}")
        raise HTTPException(status_code=400, detail=e.user_message or str(e))
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# PAYMENT INTENT (Modal de pago)
# ==========================================
@router.post("/create-payment-intent")
async def create_payment_intent(
    data: PaymentIntentRequest,
    user_id: int = Depends(get_user_id_from_token),
    db: Session = Depends(get_db)
):
    """
    ⚠️ DEPRECADO: Este endpoint usa Payment Intent que NO crea suscripciones.
    ⚠️ Usar /create-checkout-session en su lugar para suscripciones recurrentes.
    
    Crea Payment Intent para modal de pago integrado (solo pagos únicos).
    Requiere autenticación JWT.
    """
    logger.warning("⚠️ DEPRECADO: Este endpoint usa Payment Intent que NO crea suscripciones")
    logger.warning("⚠️ Usar /create-checkout-session en su lugar")
    if data.price_id not in ALLOWED_PRICE_IDS:
        raise HTTPException(status_code=400, detail="price_id inválido")
    
    # Obtener usuario
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    try:
        price = stripe.Price.retrieve(data.price_id)
        
        # Crear o reutilizar customer
        customer_id = user.stripe_customer_id
        if not customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={"user_id": str(user_id)}
            )
            customer_id = customer.id
            user.stripe_customer_id = customer_id
            db.commit()
        
        # Crear Payment Intent
        intent = stripe.PaymentIntent.create(
            amount=price.unit_amount,
            currency='eur',
            customer=customer_id,
            metadata={
                'plan_type': data.plan_type,
                'price_id': data.price_id,
                'user_id': str(user_id)
            }
        )
        
        logger.info(f"✅ Payment Intent creado: {intent.id} para user {user_id}")
        return {"client_secret": intent.client_secret}
        
    except stripe.error.StripeError as e:
        logger.error(f"Error Stripe: {e}")
        raise HTTPException(status_code=400, detail=e.user_message or str(e))
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# PORTAL DE CLIENTE (NUEVO)
# ==========================================
@router.post("/create-portal-session")
async def create_portal_session(
    user_id: int = Depends(get_user_id_from_token),
    db: Session = Depends(get_db)
):
    """
    Crea sesión del Portal de Cliente de Stripe.
    Permite gestionar suscripción (cancelar, cambiar tarjeta, etc).
    Requiere autenticación JWT.
    """
    try:
        user = db.query(Usuario).filter(Usuario.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        if not user.stripe_customer_id:
            raise HTTPException(
                status_code=400,
                detail="Usuario sin suscripción activa en Stripe"
            )
        
        # Verificar que tiene suscripción activa
        if not user.stripe_subscription_id:
            # Intentar obtener suscripción activa desde Stripe
            try:
                subscriptions = stripe.Subscription.list(
                    customer=user.stripe_customer_id,
                    status='active',
                    limit=1
                )
                if subscriptions.data:
                    user.stripe_subscription_id = subscriptions.data[0].id
                    db.commit()
                    logger.info(f"✅ Subscription ID recuperado para portal: {user.stripe_subscription_id}")
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="No se encontró una suscripción activa. Por favor, suscríbete primero."
                    )
            except stripe.error.StripeError as e:
                logger.error(f"Error verificando suscripción: {e}")
                raise HTTPException(
                    status_code=400,
                    detail="No se pudo verificar la suscripción. Por favor, contacta con soporte."
                )
        
        # Crear sesión del portal
        portal_session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=f"{FRONTEND_URL}/tarifas.html"
        )
        
        logger.info(f"✅ Portal creado para user {user_id}: {portal_session.url}")
        return {"url": portal_session.url}
        
    except stripe.error.StripeError as e:
        logger.error(f"Error Stripe: {e}")
        raise HTTPException(status_code=400, detail=e.user_message or str(e))
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# SUBSCRIPTION STATUS (NUEVO)
# ==========================================
@router.get("/subscription-status")
async def get_subscription_status(
    user_id: int = Depends(get_user_id_from_token),
    db: Session = Depends(get_db)
):
    """
    Obtiene estado detallado de la suscripción del usuario.
    Maneja race conditions y errores de atributos faltantes.
    """
    try:
        user = db.query(Usuario).filter(Usuario.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        response = {
            "plan_type": user.plan_type,
            "is_premium": user.is_premium,
            "stripe_customer_id": user.stripe_customer_id,
            "stripe_subscription_id": user.stripe_subscription_id,
            "has_active_subscription": bool(user.stripe_subscription_id),
        }
        
        subscription_id = user.stripe_subscription_id
        
        # CASO 1: No hay subscription_id pero hay customer_id (race condition)
        if not subscription_id and user.stripe_customer_id:
            logger.info(f"⏳ Buscando subscription en Stripe para user {user_id}...")
            
            try:
                subscriptions = stripe.Subscription.list(
                    customer=user.stripe_customer_id,
                    status='active',
                    limit=1
                )
                
                if subscriptions.data:
                    subscription = subscriptions.data[0]
                    subscription_id = subscription.id
                    
                    # Guardar en BD
                    user.stripe_subscription_id = subscription_id
                    
                    # Detectar tipo de plan (compatible v12+)
                    try:
                        items_data = subscription.get('items', {}).get('data', [])
                        if items_data and len(items_data) > 0:
                            price_id = items_data[0].get('price', {}).get('id')
                            if price_id == PRICE_ID_ANUAL:
                                user.plan_type = "PREMIUM_YEARLY"
                            elif price_id == PRICE_ID_MENSUAL:
                                user.plan_type = "PREMIUM_MONTHLY"
                            else:
                                user.plan_type = "PREMIUM_MONTHLY"
                    except Exception as e:
                        logger.warning(f"⚠️ Error obteniendo price_id: {e}")
                        user.plan_type = "PREMIUM_MONTHLY"
                    
                    user.is_premium = True
                    db.commit()
                    
                    logger.info(f"✅ Subscription recuperada: {subscription_id}")
                    
                    response.update({
                        "stripe_subscription_id": subscription_id,
                        "has_active_subscription": True,
                        "plan_type": user.plan_type,
                        "is_premium": True
                    })
                    
            except stripe.error.StripeError as e:
                logger.error(f"❌ Error buscando subscription: {e}")
                return response
        
        # CASO 2: Hay subscription_id - obtener detalles con acceso seguro
        if subscription_id:
            try:
                subscription = stripe.Subscription.retrieve(subscription_id)
                
                # Acceso seguro a atributos con getattr
                response.update({
                    "subscription_status": getattr(subscription, 'status', None),
                    "current_period_end": getattr(subscription, 'current_period_end', None),
                    "cancel_at_period_end": getattr(subscription, 'cancel_at_period_end', False),
                    "canceled_at": getattr(subscription, 'canceled_at', None),
                })
                
                # Detectar tipo de plan (compatible v12+)
                try:
                    items_data = subscription.get('items', {}).get('data', [])
                    if items_data and len(items_data) > 0:
                        price_id = items_data[0].get('price', {}).get('id')
                        
                        if price_id:
                            response["current_price_id"] = price_id
                            response["is_monthly"] = (price_id == PRICE_ID_MENSUAL)
                            response["is_yearly"] = (price_id == PRICE_ID_ANUAL)
                            
                            # Actualizar BD si plan_type está mal
                            if user.plan_type == "FREE" and user.is_premium:
                                if price_id == PRICE_ID_ANUAL:
                                    user.plan_type = "PREMIUM_YEARLY"
                                elif price_id == PRICE_ID_MENSUAL:
                                    user.plan_type = "PREMIUM_MONTHLY"
                                db.commit()
                                response["plan_type"] = user.plan_type
                                logger.info(f"✅ Plan type corregido: {user.plan_type}")
                except Exception as e:
                    logger.warning(f"⚠️ Error detectando plan type: {e}")
                
                logger.info(f"✅ Status obtenido para user {user_id}")
                
            except stripe.error.InvalidRequestError:
                logger.error(f"❌ Subscription {subscription_id} no existe en Stripe")
                user.stripe_subscription_id = None
                user.is_premium = False
                user.plan_type = "FREE"
                db.commit()
                response.update({
                    "stripe_subscription_id": None,
                    "has_active_subscription": False,
                    "plan_type": "FREE",
                    "is_premium": False
                })
                
            except stripe.error.StripeError as e:
                logger.warning(f"⚠️ Error obteniendo subscription: {e}")
                response["stripe_error"] = str(e)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error crítico: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# ==========================================
# STRIPE CONFIG (público)
# ==========================================
@router.get("/stripe-config")
async def get_stripe_config():
    """
    Devuelve configuración pública de Stripe para el frontend.
    NO requiere autenticación (es info pública).
    """
    if not STRIPE_PUBLISHABLE_KEY:
        raise HTTPException(
            status_code=500,
            detail="STRIPE_PUBLISHABLE_KEY no configurada en .env"
        )
    
    return {
        "publishable_key": STRIPE_PUBLISHABLE_KEY,
        "price_ids": {
            "monthly": PRICE_ID_MENSUAL,
            "yearly": PRICE_ID_ANUAL
        }
    }

# ==========================================
# USER STATUS (Legacy - mantenido por compatibilidad)
# ==========================================
@router.get("/user-status")
async def get_user_status(
    user_id: int = Depends(get_user_id_from_token),
    db: Session = Depends(get_db)
):
    """
    Devuelve el estado premium del usuario (legacy).
    Usa /subscription-status para info completa.
    """
    try:
        user = db.query(Usuario).filter(Usuario.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        return {
            "user_id": user.id,
            "email": user.email,
            "plan_type": user.plan_type,
            "is_premium": user.is_premium,
            "chat_uses_free": user.chat_uses_free
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estado: {str(e)}")

# ==========================================
# FALLBACK PREMIUM (DEV)
# ==========================================
@router.post("/stripe/activate-premium")
async def activate_premium_fallback(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Fallback para activar premium cuando el webhook no llega (desarrollo).
    En producción, el webhook debe encargarse de esto.
    """
    try:
        body = await request.json()
        user_id = body.get("user_id")
        session_id = body.get("session_id")

        if not user_id:
            return {"success": False, "error": "user_id requerido"}

        logger.info(f"🔄 Fallback premium: user_id={user_id}, session_id={session_id}")

        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user:
            logger.error(f"❌ Usuario {user_id} no encontrado")
            return {"success": False, "error": "Usuario no encontrado"}

        # Si ya es premium
        if user.is_premium:
            logger.info(f"✅ Usuario {user_id} ya es premium")
            return {
                "success": True,
                "is_premium": True,
                "plan_type": user.plan_type,
                "activated_by": "already_premium"
            }

        # Intentar verificar con Stripe si tenemos session_id
        if session_id:
            try:
                session = stripe.checkout.Session.retrieve(session_id)
                
                if session.payment_status == "paid":
                    subscription_id = session.subscription
                    plan_type = "PREMIUM_MONTHLY"  # Default
                    
                    if subscription_id:
                        subscription = stripe.Subscription.retrieve(subscription_id)
                        
                        # Acceso compatible v12+
                        try:
                            items_data = subscription.get('items', {}).get('data', [])
                            if items_data and len(items_data) > 0:
                                price_id = items_data[0].get('price', {}).get('id')
                            else:
                                price_id = None
                        except Exception:
                            price_id = None
                        
                        # 🆕 Detectar tipo de plan
                        if price_id == PRICE_ID_ANUAL:
                            plan_type = "PREMIUM_YEARLY"
                        elif price_id == PRICE_ID_MENSUAL:
                            plan_type = "PREMIUM_MONTHLY"
                        else:
                            plan_type = "PREMIUM_MONTHLY"
                        
                        user.stripe_subscription_id = subscription_id
                    
                    user.is_premium = True
                    user.plan_type = plan_type
                    user.stripe_customer_id = session.customer
                    
                    db.commit()
                    logger.info(f"✅ Usuario {user_id} actualizado a {plan_type}")
                    
                    return {
                        "success": True,
                        "is_premium": True,
                        "plan_type": plan_type,
                        "activated_by": "fallback_verified"
                    }
                else:
                    return {"success": False, "error": f"Pago no completado: {session.payment_status}"}
                    
            except stripe.error.StripeError as e:
                logger.error(f"❌ Error verificando con Stripe: {e}")
                # En desarrollo, activar igualmente
                user.is_premium = True
                user.plan_type = "PREMIUM_MONTHLY"
                db.commit()
                return {
                    "success": True,
                    "is_premium": True,
                    "activated_by": "fallback_dev_error"
                }

        # Sin session_id: activar directamente (modo dev)
        user.is_premium = True
        user.plan_type = "PREMIUM_MONTHLY"
        db.commit()
        
        logger.info(f"✅ Usuario {user_id} activado en modo dev")
        return {
            "success": True,
            "is_premium": True,
            "activated_by": "fallback_direct"
        }

    except Exception as e:
        logger.error(f"❌ Error en fallback: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}