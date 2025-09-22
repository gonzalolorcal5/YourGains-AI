# app/routes/stripe_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import stripe
from dotenv import load_dotenv

router = APIRouter(tags=["stripe"])

# === Config Stripe / Entorno ===
# Cargar .env desde la raíz del proyecto Backend
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))
STRIPE_SECRET = os.getenv("STRIPE_SECRET_KEY")
if not STRIPE_SECRET:
    # Fallamos rápido si no hay clave secreta, para evitar pagos mal configurados
    raise RuntimeError("Falta STRIPE_SECRET_KEY en .env")
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
                'price_id': data.price_id
            }
        )
        
        return {"client_secret": intent.client_secret}
    
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=e.user_message or str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/upgrade-to-premium")
async def upgrade_to_premium():
    """
    Actualiza el usuario actual a premium.
    En un entorno real, esto se haría desde el webhook de Stripe.
    """
    # TODO: Implementar actualización real en base de datos
    # Por ahora solo devolvemos éxito
    return {"message": "Usuario actualizado a premium", "plan": "premium"}

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
