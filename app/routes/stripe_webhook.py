from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
import stripe
import os

from app.database import SessionLocal
from app.models import Usuario

router = APIRouter()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

def set_customer_id_by_email(db: Session, email: str, customer_id: str):
    user = db.query(Usuario).filter(Usuario.email == email).first()
    if user:
        user.stripe_customer_id = customer_id
        db.commit()

def set_premium_by_customer(db: Session, customer_id: str, is_premium: bool):
    user = db.query(Usuario).filter(Usuario.stripe_customer_id == customer_id).first()
    if user:
        user.is_premium = is_premium
        user.plan_type = "PREMIUM" if is_premium else "FREE"
        if not is_premium:
            # si baja a FREE, reseteamos las 2 preguntas gratuitas
            user.chat_uses_free = 2
        db.commit()

@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not endpoint_secret:
        raise HTTPException(status_code=500, detail="Stripe webhook secret no configurado")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        raise HTTPException(status_code=400, detail="Payload inválido")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Firma webhook inválida")

    db = SessionLocal()
    try:
        etype = event["type"]
        obj = event["data"]["object"]

        # Al completar el checkout asociamos el customer al email
        if etype == "checkout.session.completed":
            customer_id = obj.get("customer")
            email = (obj.get("customer_details") or {}).get("email")
            if customer_id and email:
                set_customer_id_by_email(db, email, customer_id)

        # Suscripción creada/actualizada → premium si status activo o trial
        elif etype in ("customer.subscription.created", "customer.subscription.updated"):
            status = obj.get("status")          # active, trialing, past_due, canceled...
            customer_id = obj.get("customer")
            if customer_id and status:
                set_premium_by_customer(db, customer_id, status in ("active", "trialing"))

        # Suscripción cancelada → premium = False
        elif etype == "customer.subscription.deleted":
            customer_id = obj.get("customer")
            if customer_id:
                set_premium_by_customer(db, customer_id, False)

        return {"status": "ok"}
    finally:
        db.close()
