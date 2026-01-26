from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import timedelta
from dotenv import load_dotenv
import os
import json
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.auth_utils import (
    create_access_token,
    verify_password,
    get_password_hash
)
from app.database import get_db
from app import models, schemas
from app.auth_utils import ACCESS_TOKEN_EXPIRE_MINUTES

limiter = Limiter(key_func=get_remote_address)

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
# ACCESS_TOKEN_EXPIRE_MINUTES se importa desde auth_utils

router = APIRouter()


# Pydantic model para capturar JSON en lugar de Form
class UserCredentials(BaseModel):
    email: str
    password: str


@router.post("/register")
@limiter.limit("5/minute")  # Máximo 5 registros por minuto
async def register(
    request: Request,  # IMPORTANTE: añadir este parámetro para rate limiting
    user: UserCredentials,
    db: Session = Depends(get_db)
):
    existing_user = db.query(models.Usuario).filter(models.Usuario.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Usuario ya existe")

    hashed_password = get_password_hash(user.password)
    new_user = models.Usuario(email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "Usuario creado con éxito"}


@router.post("/login")
@limiter.limit("10/minute")  # Máximo 10 intentos por minuto
async def login(
    request: Request,  # IMPORTANTE: añadir este parámetro para rate limiting
    user: UserCredentials,
    db: Session = Depends(get_db)
):
    db_user = db.query(models.Usuario).filter(models.Usuario.email == user.email).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="Credenciales incorrectas")

    # Bloquear login tradicional SOLO para cuentas OAuth puras (sin password)
    if getattr(db_user, "oauth_provider", None) and not db_user.hashed_password:
        raise HTTPException(
            status_code=400,
            detail=f"Esta cuenta usa inicio de sesión con {db_user.oauth_provider.title()}. Usa el botón correspondiente."
        )

    # Verificar password (funciona tanto para cuentas tradicionales como vinculadas)
    if db_user.hashed_password and not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Credenciales incorrectas")

    # Si llegamos aquí sin password pero sin oauth_provider, el estado de la cuenta es inconsistente
    if not db_user.hashed_password and not getattr(db_user, "oauth_provider", None):
        raise HTTPException(status_code=500, detail="Cuenta en estado inválido, contacta soporte")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(db_user.id)},
        expires_delta=access_token_expires
    )
    
    # ✅ LÓGICA CONSISTENTE: Verificar Plan PRIMERO (es lo más confiable)
    has_plan = db.query(models.Plan).filter(models.Plan.user_id == db_user.id).first() is not None

    # Si tiene plan, onboarding_completed = True OBLIGATORIAMENTE
    if has_plan:
        onboarding_completed = True
    else:
        # Si no tiene plan, verificar otros indicadores
        has_valid_routine = False
        if db_user.current_routine:
            try:
                routine_data = json.loads(db_user.current_routine)
                if isinstance(routine_data, dict):
                    has_valid_routine = (
                        (routine_data.get("exercises") and len(routine_data.get("exercises", [])) > 0) or
                        (routine_data.get("dias") and len(routine_data.get("dias", [])) > 0)
                    )
            except (json.JSONDecodeError, AttributeError, KeyError):
                pass
        
        onboarding_completed = bool(
            db_user.onboarding_completed or 
            has_valid_routine
        )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "onboarding_completed": onboarding_completed
    }
