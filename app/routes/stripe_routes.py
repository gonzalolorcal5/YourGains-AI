# app/routes/stripe_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import stripe

router = APIRouter(tags=["stripe"])

# === Config Stripe / Entorno ===
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

class CheckoutSessionRequest(BaseModel):
    price_id: str  # recibido desde pago.html

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
