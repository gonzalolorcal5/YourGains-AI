from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Usuario
from app.auth_utils import get_password_hash
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
        "subscription_type": user.subscription_type,
        "chat_uses_free": user.chat_uses_free
    }
