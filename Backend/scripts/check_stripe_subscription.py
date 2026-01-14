import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import stripe
from dotenv import load_dotenv
from app.database import SessionLocal
from app.models import Usuario

# Cargar variables de entorno
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

def check_subscription_status(email):
    """Verifica el estado real de la suscripción en Stripe"""
    db = SessionLocal()
    try:
        # Obtener usuario de BD
        user = db.query(Usuario).filter(Usuario.email == email).first()
        
        if not user:
            print(f"[ERROR] Usuario no encontrado: {email}")
            return
        
        print(f"\n{'='*80}")
        print(f"VERIFICACION DE SUSCRIPCION - {email}")
        print(f"{'='*80}")
        
        print(f"\n[DATOS EN BD LOCAL]")
        print(f"   is_premium: {user.is_premium}")
        print(f"   plan_type: {user.plan_type}")
        print(f"   stripe_customer_id: {user.stripe_customer_id}")
        print(f"   stripe_subscription_id: {user.stripe_subscription_id}")
        
        # Verificar en Stripe
        if user.stripe_subscription_id:
            try:
                print(f"\n[CONSULTANDO STRIPE...]")
                subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)
                
                print(f"\n[DATOS EN STRIPE]")
                print(f"   Subscription ID: {subscription.id}")
                print(f"   Status: {subscription.status}")
                print(f"   Customer: {subscription.customer}")
                
                # Algunos campos pueden no existir en suscripciones canceladas
                if hasattr(subscription, 'current_period_end') and subscription.current_period_end:
                    from datetime import datetime
                    period_end = datetime.fromtimestamp(subscription.current_period_end)
                    print(f"   Current Period End: {period_end} ({subscription.current_period_end})")
                
                if hasattr(subscription, 'cancel_at_period_end'):
                    print(f"   Cancel at Period End: {subscription.cancel_at_period_end}")
                
                # Obtener price_id
                try:
                    items = subscription.items
                    if items and hasattr(items, 'data') and items.data:
                        price_id = items.data[0].price.id
                        print(f"   Price ID: {price_id}")
                except (AttributeError, IndexError, TypeError):
                    pass
                
                print(f"\n[ANALISIS]")
                if subscription.status == 'active':
                    print(f"   [OK] Suscripcion ACTIVA en Stripe")
                    print(f"   [ERROR] BD dice FREE - DESINCRONIZACION DETECTADA")
                    print(f"\n[RECOMENDACION] Actualizar BD a PREMIUM")
                elif subscription.status in ['canceled', 'unpaid', 'past_due']:
                    print(f"   [ERROR] Suscripcion NO ACTIVA en Stripe (status: {subscription.status})")
                    print(f"   [OK] BD esta correcta como FREE")
                    print(f"\n[RECOMENDACION] Limpiar stripe_ids de la BD")
                else:
                    print(f"   [ADVERTENCIA] Estado inusual: {subscription.status}")
                
            except stripe.error.InvalidRequestError as e:
                print(f"\n[ERROR] consultando Stripe: {e}")
                print(f"   La suscripcion probablemente no existe en Stripe")
                print(f"\n[RECOMENDACION] Limpiar stripe_ids de la BD")
        else:
            print(f"\n[OK] Usuario no tiene stripe_subscription_id - Todo OK")
        
        print(f"\n{'='*80}\n")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_subscription_status("gonzalouni05@gmail.com")

