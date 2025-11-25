# Ejemplo de endpoints para integrar con Stripe Payment Element
# Añade estos endpoints a tu main.py

import stripe
from fastapi import HTTPException
from pydantic import BaseModel

# Configura tu clave secreta de Stripe
stripe.api_key = "sk_test_your_secret_key_here"

class PaymentIntentRequest(BaseModel):
    plan_type: str  # 'monthly' o 'yearly'
    price_id: str

class UpgradeRequest(BaseModel):
    user_id: str

@app.post("/create-payment-intent")
async def create_payment_intent(request: PaymentIntentRequest, current_user: User = Depends(get_current_user)):
    try:
        # Crear Payment Intent
        intent = stripe.PaymentIntent.create(
            amount=999 if request.plan_type == 'monthly' else 7999,  # En centavos
            currency='eur',
            metadata={
                'user_id': current_user.id,
                'plan_type': request.plan_type,
                'price_id': request.price_id
            }
        )
        
        return {"client_secret": intent.client_secret}
    
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/upgrade-to-premium")
async def upgrade_to_premium(current_user: User = Depends(get_current_user)):
    try:
        # Actualizar usuario a premium en tu base de datos
        # Esto depende de tu modelo de usuario
        current_user.plan = "premium"
        current_user.save()  # O tu método de guardado
        
        return {"message": "Usuario actualizado a premium", "plan": "premium"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error actualizando usuario")

# Webhook para confirmar pagos exitosos
@app.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, "whsec_your_webhook_secret"
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Manejar evento de pago exitoso
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        user_id = payment_intent['metadata']['user_id']
        plan_type = payment_intent['metadata']['plan_type']
        
        # Actualizar usuario a premium
        # Tu lógica aquí para actualizar en base de datos
        
        print(f"Pago exitoso para usuario {user_id}, plan: {plan_type}")
    
    return {"status": "success"}









