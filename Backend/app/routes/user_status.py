from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Usuario
from app.auth_utils import get_password_hash, get_current_user
import secrets

router = APIRouter()

@router.get("/user/status")
def user_status(email: str = Query(...), db: Session = Depends(get_db)):
    """
    Si el email no existe en nuestra tabla usuarios (porque entró por Supabase por primera vez),
    lo creamos automáticamente como FREE con 2 preguntas. Así /stripe, /chat, etc. funcionan.
    """
    user = db.query(Usuario).filter(Usuario.email == email).first()
    if not user:
        # Creamos un usuario "semilla" con contraseña aleatoria (no se usará para login)
        random_pw = secrets.token_urlsafe(24)
        user = Usuario(
            email=email,
            hashed_password=get_password_hash(random_pw),
            is_premium=False,
            plan_type="FREE",
            chat_uses_free=2
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return {
        "exists": True,
        "is_premium": bool(user.is_premium),
        "plan_type": user.plan_type,
        "chat_uses_free": user.chat_uses_free
    }

@router.get("/api/user/me")
async def get_current_user_data(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtiene datos completos del usuario actual desde la BD"""
    
    # current_user YA ES el objeto Usuario completo de la BD
    # No necesitamos hacer ninguna query adicional
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "plan_type": current_user.plan_type or "FREE",
        "is_premium": current_user.is_premium or False,
        "onboarding_completed": current_user.onboarding_completed or False,
        "profile_picture": getattr(current_user, 'profile_picture', None),
        "chat_uses_free": getattr(current_user, 'chat_uses_free', 2),
        "stripe_customer_id": getattr(current_user, 'stripe_customer_id', None),
        "stripe_subscription_id": getattr(current_user, 'stripe_subscription_id', None),
        "subscription_type": getattr(current_user, 'subscription_type', None),
    }
