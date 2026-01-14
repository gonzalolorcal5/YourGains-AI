import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Usuario

def clean_stripe_ids(email):
    """Limpia stripe_customer_id y stripe_subscription_id de un usuario"""
    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.email == email).first()
        
        if not user:
            print(f"[ERROR] Usuario no encontrado: {email}")
            return
        
        print(f"\n{'='*80}")
        print(f"LIMPIEZA DE STRIPE IDs - {email}")
        print(f"{'='*80}")
        
        print(f"\n[ANTES]")
        print(f"   is_premium: {user.is_premium}")
        print(f"   plan_type: {user.plan_type}")
        print(f"   stripe_customer_id: {user.stripe_customer_id}")
        print(f"   stripe_subscription_id: {user.stripe_subscription_id}")
        
        # Limpiar IDs
        user.stripe_customer_id = None
        user.stripe_subscription_id = None
        
        # Asegurar que está como FREE
        user.is_premium = False
        user.plan_type = "FREE"
        user.chat_uses_free = 2
        
        db.commit()
        db.refresh(user)
        
        print(f"\n[DESPUES]")
        print(f"   is_premium: {user.is_premium}")
        print(f"   plan_type: {user.plan_type}")
        print(f"   stripe_customer_id: {user.stripe_customer_id}")
        print(f"   stripe_subscription_id: {user.stripe_subscription_id}")
        
        print(f"\n[OK] Stripe IDs limpiados correctamente")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clean_stripe_ids("gonzalouni05@gmail.com")

