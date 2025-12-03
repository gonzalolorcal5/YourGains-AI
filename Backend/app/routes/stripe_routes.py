from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging
import traceback
import os
import stripe
from dotenv import load_dotenv
from datetime import datetime

from app.database import get_db
from app.models import Usuario

router = APIRouter(tags=["stripe"])
logger = logging.getLogger(__name__)

# === Config Stripe / Entorno ===
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

STRIPE_SECRET = os.getenv("STRIPE_SECRET_KEY")
if not STRIPE_SECRET:
    print("⚠️ STRIPE_SECRET_KEY no configurada - modo dev")
    STRIPE_SECRET = "sk_test_placeholder"

stripe.api_key = STRIPE_SECRET

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:8000/frontend").rstrip("/")

PRICE_ID_MENSUAL = os.getenv("STRIPE_PRICE_MENSUAL")
PRICE_ID_ANUAL = os.getenv("STRIPE_PRICE_ANUAL")
ALLOWED_PRICE_IDS = {p for p in [PRICE_ID_MENSUAL, PRICE_ID_ANUAL] if p}

STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")


class CheckoutSessionRequest(BaseModel):
    price_id: str


class PaymentIntentRequest(BaseModel):
    plan_type: str
    price_id: str
    user_id: int


class CustomerPortalRequest(BaseModel):
    user_id: int


@router.post("/create-checkout-session")
async def create_checkout_session(data: CheckoutSessionRequest):
    """Crea sesión de Stripe Checkout"""
    if not ALLOWED_PRICE_IDS:
        raise HTTPException(status_code=500, detail="Precios no configurados")

    if data.price_id not in ALLOWED_PRICE_IDS:
        raise HTTPException(status_code=400, detail="price_id inválido")

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
        raise HTTPException(status_code=400, detail=e.user_message or str(e))


@router.get("/check-subscription-eligibility")
async def check_subscription_eligibility():
    """Verifica elegibilidad para compra"""
    return {
        "can_buy_monthly": True,
        "can_buy_yearly": True,
        "current_plan": None,
    }


@router.post("/create-payment-intent")
async def create_payment_intent(data: PaymentIntentRequest, db: Session = Depends(get_db)):
    """
    🔥 SOLUCIÓN DEFINITIVA: Crear PaymentIntent MANUAL
    
    El problema era que payment_behavior='default_incomplete' crea una estructura
    donde el payment_intent no es directamente accesible.
    
    NUEVA ESTRATEGIA:
    1. Crear PaymentIntent manualmente
    2. Guardar price_id en metadata
    3. Frontend confirma el pago
    4. Webhook crea la subscription cuando el pago se confirma
    """
    try:
        print("\n" + "="*80)
        print("🚀 CREATE PAYMENT INTENT - MÉTODO MANUAL")
        print("="*80)
        
        # 🔒 LOCK: Evitar race conditions
        user = (
            db.query(Usuario)
            .filter(Usuario.id == data.user_id)
            .with_for_update()
            .first()
        )

        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # Validación de plan existente
        if user.is_premium:
            current_sub = getattr(user, "subscription_type", None)
            if current_sub == "yearly":
                raise HTTPException(status_code=400, detail="Ya tienes plan anual activo")
            elif current_sub == "monthly" and data.plan_type == "monthly":
                raise HTTPException(status_code=400, detail="Ya tienes plan mensual activo")

        # Validar price_id
        if data.price_id not in ALLOWED_PRICE_IDS:
            raise HTTPException(status_code=400, detail="price_id inválido")

        customer_id = user.stripe_customer_id

        # 🔧 CREAR O RECUPERAR CUSTOMER
        if not customer_id:
            try:
                existing_customers = stripe.Customer.list(email=user.email, limit=1)

                if existing_customers.data:
                    customer_id = existing_customers.data[0].id
                    print(f"♻️ Customer existente encontrado: {customer_id}")
                else:
                    customer = stripe.Customer.create(
                        email=user.email,
                        metadata={"user_id": str(user.id)},
                    )
                    customer_id = customer.id
                    print(f"✅ Customer nuevo creado: {customer_id}")

                user.stripe_customer_id = customer_id
                db.commit()
                print(f"💾 Customer ID guardado en DB para usuario {user.id}")

            except stripe.error.StripeError as e:
                print(f"❌ Error creando customer en Stripe: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Error creando customer en Stripe",
                )
        else:
            print(f"♻️ Usuario {user.id} ya tiene customer: {customer_id}")

        # 🔥 MÉTODO NUEVO: Obtener el precio para calcular amount
        try:
            price = stripe.Price.retrieve(data.price_id)
            amount = price.unit_amount  # En centavos
            currency = price.currency
            
            print(f"💰 Precio recuperado: {amount/100} {currency.upper()}")
            
        except stripe.error.StripeError as e:
            print(f"❌ Error recuperando precio: {e}")
            raise HTTPException(status_code=500, detail="Error recuperando información del precio")

        # 🔥 CREAR PAYMENT INTENT MANUAL (como hacíamos antes)
        try:
            print(f"💳 Creando PaymentIntent manual...")
            
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                customer=customer_id,
                setup_future_usage="off_session",  # Guardar método de pago para futuro
                metadata={
                    "user_id": str(data.user_id),
                    "plan_type": data.plan_type,
                    "price_id": data.price_id,
                    "integration_type": "manual_subscription"
                }
            )
            
            print(f"✅ PaymentIntent creado: {payment_intent.id}")
            print(f"💳 Amount: {payment_intent.amount} {payment_intent.currency}")
            print(f"🔐 Client secret: {payment_intent.client_secret[:30]}...")
            
            print("="*80 + "\n")
            
            return {
                "client_secret": payment_intent.client_secret,
                "payment_intent_id": payment_intent.id
            }
            
        except stripe.error.StripeError as e:
            print(f"❌ Error creando PaymentIntent: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error creando PaymentIntent: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error general: {e}")
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/upgrade-to-premium")
async def upgrade_to_premium(user_id: int, db: Session = Depends(get_db)):
    """Actualiza usuario a premium (desarrollo)"""
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id requerido")

    result = (
        db.query(Usuario)
        .filter(Usuario.id == user_id)
        .update(
            {
                "plan_type": "PREMIUM",
                "is_premium": True,
                "chat_uses_free": 999,
                "subscription_type": "monthly",
                "subscription_start_date": datetime.utcnow(),
            }
        )
    )
    db.commit()

    if result == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return {"message": "Usuario actualizado a premium", "user_id": user_id}


@router.get("/user-status")
async def get_user_status(user_id: int, db: Session = Depends(get_db)):
    """Devuelve estado del usuario"""
    user = db.query(Usuario).filter(Usuario.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return {
        "user_id": user.id,
        "email": user.email,
        "plan_type": user.plan_type,
        "is_premium": user.is_premium,
        "subscription_type": getattr(user, "subscription_type", None),
        "chat_uses_free": user.chat_uses_free,
    }


@router.get("/stripe-config")
async def get_stripe_config():
    """Configuración de Stripe para frontend"""
    if not STRIPE_PUBLISHABLE_KEY:
        raise HTTPException(
            status_code=500, detail="STRIPE_PUBLISHABLE_KEY no configurada"
        )

    return {
        "publishable_key": STRIPE_PUBLISHABLE_KEY,
        "price_ids": {"monthly": PRICE_ID_MENSUAL, "yearly": PRICE_ID_ANUAL},
    }


@router.post("/create-customer-portal-session")
async def create_customer_portal_session(
    data: CustomerPortalRequest, db: Session = Depends(get_db)
):
    """Crea sesión del Customer Portal"""
    user = db.query(Usuario).filter(Usuario.id == data.user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if not user.stripe_customer_id:
        raise HTTPException(
            status_code=400, detail="No se encontró información de suscripción"
        )

    try:
        # Verificar que el customer existe en Stripe
        try:
            stripe.Customer.retrieve(user.stripe_customer_id)
        except stripe.error.InvalidRequestError:
            raise HTTPException(
                status_code=400, detail="Customer no válido en Stripe"
            )

        session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=f"{FRONTEND_URL}/dashboard.html",
        )
        return {"url": session.url}

    except HTTPException:
        raise
    except stripe.error.StripeError as e:
        logger.error(f"❌ Error Stripe: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail="Error interno")


@router.post("/stripe/activate-premium")
async def activate_premium_fallback(request: Request, db: Session = Depends(get_db)):
    """
    Fallback para desarrollo sin webhook.
    Solo para DEV, no usar en producción.
    """
    try:
        body = await request.json()
        user_id = body.get("user_id")

        if not user_id:
            return {"success": False, "error": "user_id requerido"}

        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user:
            return {"success": False, "error": "Usuario no encontrado"}

        if user.is_premium:
            logger.info(f"✅ Usuario {user_id} ya premium (webhook ejecutó)")
            return {"success": True, "is_premium": True, "activated_by": "webhook"}

        if not user.stripe_customer_id:
            logger.warning(
                f"⚠️ Usando fallback para usuario {user_id} - webhook no llegó"
            )

            try:
                customers = stripe.Customer.list(email=user.email, limit=1)
                if customers.data:
                    user.stripe_customer_id = customers.data[0].id
            except Exception as e:
                logger.error(f"Error buscando customer: {e}")

        user.is_premium = True
        user.plan_type = "PREMIUM"
        user.subscription_type = "monthly"
        user.subscription_start_date = datetime.utcnow()
        db.commit()

        return {"success": True, "is_premium": True, "activated_by": "fallback"}

    except Exception as e:
        logger.error(f"❌ Error en fallback: {e}")
        return {"success": False, "error": str(e)}