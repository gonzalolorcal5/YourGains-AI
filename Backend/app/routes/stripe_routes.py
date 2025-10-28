# app/routes/stripe_routes.py
from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.orm import Session
import traceback
import logging
from app.database import get_db
from app.models import Usuario
from pydantic import BaseModel
import os
import stripe
from dotenv import load_dotenv

router = APIRouter(tags=["stripe"])
logger = logging.getLogger(__name__)

# === Config Stripe / Entorno ===
# Cargar .env desde la raíz del proyecto Backend
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))
STRIPE_SECRET = os.getenv("STRIPE_SECRET_KEY")
if not STRIPE_SECRET:
    # 🛠️ MODO DESARROLLO: Permitir continuar sin Stripe configurado
    print("⚠️ STRIPE no configurado - Modo desarrollo activado")
    STRIPE_SECRET = "sk_test_placeholder"
stripe.api_key = STRIPE_SECRET

# Donde está tu frontend
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:8000/frontend").rstrip("/")

# Price IDs permitidos (desde .env)
PRICE_ID_MENSUAL = os.getenv("STRIPE_PRICE_MENSUAL")
PRICE_ID_ANUAL = os.getenv("STRIPE_PRICE_ANUAL")
ALLOWED_PRICE_IDS = {p for p in [PRICE_ID_MENSUAL, PRICE_ID_ANUAL] if p}

# Clave pública de Stripe (solo para el frontend)
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")

class CheckoutSessionRequest(BaseModel):
    price_id: str  # recibido desde pago.html

class PaymentIntentRequest(BaseModel):
    plan_type: str  # 'monthly' o 'yearly'
    price_id: str
    user_id: int  # ID del usuario que está pagando

@router.post("/create-checkout-session")
async def create_checkout_session(data: CheckoutSessionRequest):
    """
    Crea una sesión de Stripe Checkout para suscripción (SIN prueba gratuita).
    Valida que el price_id sea uno de los permitidos.
    """
    # 1) Validaciones de entorno
    if not ALLOWED_PRICE_IDS:
        raise HTTPException(
            status_code=500,
            detail="Precios Stripe no configurados. Define STRIPE_PRICE_MENSUAL y STRIPE_PRICE_ANUAL en .env."
        )

    # 2) Validar que el price_id venga de tus dos precios
    if data.price_id not in ALLOWED_PRICE_IDS:
        raise HTTPException(status_code=400, detail="price_id inválido")

    # 3) Crear sesión de Checkout
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": data.price_id, "quantity": 1}],
            success_url=f"{FRONTEND_URL}/dashboard.html?success=1&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/tarifas.html?cancel=1",
            allow_promotion_codes=True,
        )
        return {"url": session.url}
    except stripe.error.StripeError as e:
        # Mensaje amigable si Stripe devuelve error
        raise HTTPException(status_code=400, detail=e.user_message or str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/create-payment-intent")
async def create_payment_intent(data: PaymentIntentRequest):
    """
    Crea un Payment Intent para el modal de pago integrado.
    """
    # Validar price_id
    if data.price_id not in ALLOWED_PRICE_IDS:
        raise HTTPException(status_code=400, detail="price_id inválido")
    
    # Obtener precio desde Stripe
    try:
        price = stripe.Price.retrieve(data.price_id)
        amount = price.unit_amount  # Ya está en centavos
        
        # Crear Payment Intent
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='eur',
            metadata={
                'plan_type': data.plan_type,
                'price_id': data.price_id,
                'user_id': str(data.user_id)  # Añadir user_id a metadata
            }
        )
        
        return {"client_secret": intent.client_secret}
    
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=e.user_message or str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/upgrade-to-premium")
async def upgrade_to_premium(user_id: int = None):
    """
    Actualiza el usuario actual a premium.
    En un entorno real, esto se haría desde el webhook de Stripe.
    """
    from sqlalchemy.orm import Session
    from app.database import get_db
    from app.models import Usuario
    
    try:
        # Para desarrollo, usar user_id del parámetro o del header
        if not user_id:
            # Intentar obtener del header Authorization
            from fastapi import Request
            # Por ahora, usar un ID fijo para testing
            user_id = 63  # Tu user_id del log
        
        # Actualizar a premium en la base de datos
        db = next(get_db())
        result = db.query(Usuario).filter(Usuario.id == user_id).update({
            "plan_type": "PREMIUM",
            "is_premium": True,
            "chat_uses_free": 999
        })
        db.commit()
        
        if result == 0:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        return {"message": "Usuario actualizado a premium", "plan": "premium", "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando usuario: {str(e)}")

@router.get("/user-status")
async def get_user_status(user_id: int):
    """
    Devuelve el estado premium del usuario.
    """
    from sqlalchemy.orm import Session
    from app.database import get_db
    from app.models import Usuario
    
    try:
        db = next(get_db())
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

@router.get("/stripe-config")
async def get_stripe_config():
    """
    Devuelve la configuración de Stripe necesaria para el frontend.
    Solo incluye la clave pública, nunca la secreta.
    """
    if not STRIPE_PUBLISHABLE_KEY:
        raise HTTPException(status_code=500, detail="STRIPE_PUBLISHABLE_KEY no configurada")
    
    return {
        "publishable_key": STRIPE_PUBLISHABLE_KEY,
        "price_ids": {
            "monthly": PRICE_ID_MENSUAL,
            "yearly": PRICE_ID_ANUAL
        }
    }

# ================= FALLBACK PREMIUM (DEV) =================
@router.post("/stripe/activate-premium")
async def activate_premium_fallback(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Fallback para activar premium cuando el usuario vuelve de Stripe y el webhook
    no llegó (entornos de desarrollo sin Stripe CLI). En producción, el webhook
    debe encargarse de esto.
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

        # Si ya es premium, no hacer nada
        if user.is_premium or user.plan_type == "PREMIUM":
            logger.info(f"✅ Usuario {user_id} ya es premium (probable webhook)")
            return {"success": True, "is_premium": True, "activated_by": "webhook"}

        # Intentar verificar con Stripe si tenemos session_id
        if session_id:
            try:
                session = stripe.checkout.Session.retrieve(session_id)
                status = getattr(session, "payment_status", None)
                if status == "paid":
                    logger.info(f"💳 Pago verificado para user_id={user_id}")
                    user.is_premium = True
                    user.plan_type = "PREMIUM"
                    if getattr(session, "customer", None):
                        user.stripe_customer_id = session.customer
                    db.commit()
                    db.refresh(user)
                    return {"success": True, "is_premium": True, "activated_by": "fallback"}
                else:
                    logger.warning(f"⚠️ Pago no completado: {status}")
                    return {"success": False, "error": f"Pago no completado: {status}"}
            except Exception as e:
                logger.error(f"❌ Error verificando con Stripe: {e}")
                # En desarrollo, activar igualmente
                user.is_premium = True
                user.plan_type = "PREMIUM"
                db.commit()
                db.refresh(user)
                return {"success": True, "is_premium": True, "activated_by": "fallback_dev"}

        # Sin session_id: activar directamente (modo dev)
        user.is_premium = True
        user.plan_type = "PREMIUM"
        db.commit()
        db.refresh(user)
        return {"success": True, "is_premium": True, "activated_by": "fallback_direct"}

    except Exception as e:
        logger.error(f"❌ Error en activate_premium_fallback: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}
