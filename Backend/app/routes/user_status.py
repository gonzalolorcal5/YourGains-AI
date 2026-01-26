from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Usuario, Plan
from app.auth_utils import get_password_hash, get_current_user
from app.schemas import UserResponse
import secrets
import json

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

@router.get("/api/user/me", response_model=UserResponse)
async def get_current_user_data(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene datos completos del usuario actual desde la BD.
    Calcula onboarding_completed dinámicamente y devuelve valores por defecto para campos nuevos.
    Envuelto en try/except para evitar errores 500 con usuarios antiguos.
    """
    try:
        # 🔥 SOLO aquí hacemos refresh porque es el endpoint que devuelve datos al frontend
        # No en get_current_user() que se ejecuta en cada request
        db.expire_all()  # Expirar todos los objetos cacheados en la sesión
        db.refresh(current_user)  # Forzar refresh del usuario para obtener datos frescos de la BD
        
        # Verificar si tiene Plan(es) en la BD - ESTO ES PRIORITARIO
        last_plan = db.query(Plan).filter(Plan.user_id == current_user.id).order_by(Plan.id.desc()).first()
        has_plan = last_plan is not None
        
        # ✅ REGLA CRÍTICA: Si tiene Plan → onboarding_completed = True OBLIGATORIAMENTE
        if has_plan:
            onboarding_completed = True
            session_duration = last_plan.session_duration if last_plan.session_duration else "45-60"
        else:
            # Si no tiene plan, verificar otros indicadores
            has_valid_routine = False
            if current_user.current_routine:
                try:
                    routine_data = json.loads(current_user.current_routine)
                    if isinstance(routine_data, dict):
                        has_valid_routine = (
                            (routine_data.get("exercises") and len(routine_data.get("exercises", [])) > 0) or
                            (routine_data.get("dias") and len(routine_data.get("dias", [])) > 0)
                        )
                except (json.JSONDecodeError, AttributeError, KeyError):
                    pass
            
            onboarding_completed = bool(
                current_user.onboarding_completed or 
                has_valid_routine
            )
            session_duration = "45-60"
        
        # Preparar valores para la respuesta
        user_id = current_user.id
        user_email = current_user.email
        user_plan_type = current_user.plan_type or "FREE"
        user_is_premium = bool(current_user.is_premium)
        user_stripe_customer_id = getattr(current_user, 'stripe_customer_id', None)
        user_stripe_subscription_id = getattr(current_user, 'stripe_subscription_id', None)
        user_subscription_type = getattr(current_user, 'subscription_type', None)
        
        # 🔥 LOG DE SINCRONIZACIÓN para depuración en Railway
        print(f"[USER_ME] Usuario ID: {user_id}, Email: {user_email}, "
              f"Premium: {user_is_premium}, Plan: {user_plan_type}, "
              f"Onboarding: {onboarding_completed}, Has Plan in DB: {has_plan}, "
              f"Stripe Customer: {user_stripe_customer_id}")
        
        return UserResponse(
            id=user_id,
            email=user_email,
            plan_type=user_plan_type,
            is_premium=user_is_premium,
            onboarding_completed=onboarding_completed,
            session_duration=session_duration,
            profile_picture=getattr(current_user, 'profile_picture', None),
            chat_uses_free=getattr(current_user, 'chat_uses_free', 2),
            stripe_customer_id=user_stripe_customer_id,
            stripe_subscription_id=user_stripe_subscription_id,
            subscription_type=user_subscription_type,
        )
    
    except Exception as e:
        # Si algo falla, devolver valores por defecto en lugar de error 500
        print(f"❌ [USER_ME] Error crítico en get_current_user_data: {e}")
        import traceback
        traceback.print_exc()
        
        # Preparar valores por defecto seguros
        user_id = current_user.id if current_user else 0
        user_email = current_user.email if current_user else ""
        user_plan_type = getattr(current_user, 'plan_type', 'FREE') or "FREE"
        user_is_premium = bool(getattr(current_user, 'is_premium', False))
        user_stripe_customer_id = getattr(current_user, 'stripe_customer_id', None) if current_user else None
        
        # 🔥 LOG DE SINCRONIZACIÓN incluso en caso de error (con valores por defecto)
        print(f"[SYNC] Enviando estado al frontend (ERROR): Usuario ID: {user_id}, Email: {user_email}, Premium: {user_is_premium}, Plan: {user_plan_type}, Onboarding: False (error), Stripe Customer: {user_stripe_customer_id}")
        
        # Retornar valores por defecto seguros
        return UserResponse(
            id=user_id,
            email=user_email,
            plan_type=user_plan_type,
            is_premium=user_is_premium,
            onboarding_completed=False,  # Por defecto False si hay error
            session_duration="45-60",  # Valor por defecto
            profile_picture=getattr(current_user, 'profile_picture', None) if current_user else None,
            chat_uses_free=getattr(current_user, 'chat_uses_free', 2) if current_user else 2,
            stripe_customer_id=user_stripe_customer_id,
            stripe_subscription_id=getattr(current_user, 'stripe_subscription_id', None) if current_user else None,
            subscription_type=getattr(current_user, 'subscription_type', None) if current_user else None,
        )
