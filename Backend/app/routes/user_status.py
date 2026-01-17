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
        # Calcular onboarding_completed dinámicamente
        # Si tiene current_routine válida o tiene un Plan, consideramos que completó onboarding
        has_valid_routine = False
        if current_user.current_routine:
            try:
                routine_data = json.loads(current_user.current_routine)
                # Verificar que no sea solo el objeto vacío por defecto
                if isinstance(routine_data, dict) and routine_data.get("exercises"):
                    has_valid_routine = len(routine_data.get("exercises", [])) > 0
                # También verificar formato alternativo con "dias"
                elif isinstance(routine_data, dict) and routine_data.get("dias"):
                    has_valid_routine = len(routine_data.get("dias", [])) > 0
            except (json.JSONDecodeError, AttributeError, KeyError):
                pass
        
        # Verificar si tiene Plan(es) en la BD - usar order_by(Plan.id.desc()).first() para obtener el más reciente
        has_plan = False
        last_plan = None
        try:
            # Obtener el plan más reciente ordenado por ID descendente
            last_plan = db.query(Plan).filter(Plan.user_id == current_user.id).order_by(Plan.id.desc()).first()
            has_plan = last_plan is not None
        except Exception as e:
            print(f"⚠️ [USER_ME] Error obteniendo plan del usuario: {e}")
            has_plan = False
            last_plan = None
        
        # ⚠️ REGLA CRÍTICA: Si el usuario tiene planes, onboarding_completed DEBE ser True obligatoriamente
        # onboarding_completed = True si:
        # 1. Tiene un Plan guardado (OBLIGATORIO), O
        # 2. Está marcado explícitamente como True en BD, O
        # 3. Tiene una rutina válida
        if has_plan:
            onboarding_completed = True  # OBLIGATORIO si tiene planes
        else:
            onboarding_completed = bool(
                current_user.onboarding_completed or 
                has_valid_routine
            )
        
        # Obtener session_duration del último Plan o usar valor por defecto
        session_duration = "45-60"  # Valor por defecto
        if last_plan and last_plan.session_duration:
            session_duration = last_plan.session_duration
        
        # 🔥 Asegurar que todos los campos necesarios estén presentes
        # 🔥 CRÍTICO: Expirar todos los objetos cacheados y refrescar current_user
        # Esto es necesario porque estamos haciendo cambios manuales en Railway y SQLAlchemy
        # está sirviendo datos cacheados que no reflejan la realidad
        db.expire_all()  # Expirar todos los objetos cacheados en la sesión
        db.refresh(current_user)  # Forzar refresh del usuario para obtener datos frescos de la BD
        
        # Preparar valores para la respuesta
        user_id = current_user.id
        user_email = current_user.email
        user_plan_type = current_user.plan_type or "FREE"
        user_is_premium = bool(current_user.is_premium)
        user_stripe_customer_id = getattr(current_user, 'stripe_customer_id', None)
        user_stripe_subscription_id = getattr(current_user, 'stripe_subscription_id', None)
        user_subscription_type = getattr(current_user, 'subscription_type', None)
        
        # 🔥 LOG DE SINCRONIZACIÓN para depuración en Railway
        print(f"[SYNC] Enviando estado al frontend: Usuario ID: {user_id}, Email: {user_email}, Premium: {user_is_premium}, Plan: {user_plan_type}, Onboarding: {onboarding_completed}, Stripe Customer: {user_stripe_customer_id}")
        
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
        
        # 🔥 Intentar refrescar datos antes de usar valores por defecto
        # Esto puede ayudar si el error fue por datos cacheados
        if current_user:
            try:
                db.expire_all()  # Expirar todos los objetos cacheados
                db.refresh(current_user)  # Refrescar usuario para obtener datos frescos
            except Exception as refresh_error:
                print(f"⚠️ [USER_ME] No se pudo refrescar usuario en bloque de error: {refresh_error}")
        
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
