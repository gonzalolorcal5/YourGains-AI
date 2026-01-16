from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import timedelta
import httpx
import os
from dotenv import load_dotenv
from urllib.parse import urlencode

from app.database import get_db
from app.models import Usuario
from app.auth_utils import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES


load_dotenv()


router = APIRouter(prefix="/auth/google", tags=["oauth"])


# Configuración Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


@router.get("/login")
async def google_login():
    """Redirige al usuario a la página de login de Google"""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth no configurado")
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def google_callback(
    code: str = Query(...),
    db: Session = Depends(get_db)
):
    """Procesa el callback de Google y crea/autentica al usuario"""
    try:
        # 1. Intercambiar código por access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code"
                }
            )
            
            if token_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Error al obtener token de Google")
            
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                raise HTTPException(status_code=400, detail="No se recibió access token")
            
            # 2. Obtener información del usuario
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if userinfo_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Error al obtener información del usuario")
            
            userinfo = userinfo_response.json()
        
        # 3. Extraer datos del usuario
        google_id = userinfo.get("sub")
        email = userinfo.get("email")
        profile_picture = userinfo.get("picture")
        
        if not google_id or not email:
            raise HTTPException(status_code=400, detail="Datos de usuario incompletos")
        
        # 4. Buscar o crear usuario
        user = db.query(Usuario).filter(Usuario.google_id == google_id).first()
        
        if not user:
            # Verificar si existe cuenta con ese email (para vincular)
            user = db.query(Usuario).filter(Usuario.email == email).first()
            
            if user:
                # Vincular cuenta existente con Google
                user.google_id = google_id
                user.oauth_provider = 'google'
                user.profile_picture = profile_picture
            else:
                # Crear nuevo usuario
                user = Usuario(
                    email=email,
                    google_id=google_id,
                    oauth_provider='google',
                    profile_picture=profile_picture,
                    hashed_password=None,
                    onboarding_completed=False,
                    is_premium=False,
                    plan_type='FREE',
                    chat_uses_free=2
                )
                db.add(user)
            
            db.commit()
            db.refresh(user)
        
        # 5. Calcular onboarding_completed dinámicamente (igual que en auth.py)
        # Si tiene current_routine válida o tiene un Plan, consideramos que completó onboarding
        has_valid_routine = False
        if user.current_routine:
            try:
                import json
                routine_data = json.loads(user.current_routine)
                # Verificar que no sea solo el objeto vacío por defecto
                if isinstance(routine_data, dict) and routine_data.get("exercises"):
                    has_valid_routine = len(routine_data.get("exercises", [])) > 0
                # También verificar formato alternativo con "dias"
                elif isinstance(routine_data, dict) and routine_data.get("dias"):
                    has_valid_routine = len(routine_data.get("dias", [])) > 0
            except (json.JSONDecodeError, AttributeError, KeyError):
                pass
        
        # Verificar si tiene un Plan en la BD
        from app.models import Plan
        has_plan = db.query(Plan).filter(Plan.user_id == user.id).first() is not None
        
        # onboarding_completed = True si:
        # 1. Está marcado explícitamente como True en BD, O
        # 2. Tiene una rutina válida, O
        # 3. Tiene un Plan guardado
        onboarding_completed = bool(
            user.onboarding_completed or 
            has_valid_routine or 
            has_plan
        )
        
        # 6. Generar JWT token (solo incluye user_id, igual que auth.py)
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        jwt_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        )
        
        # 7. Redirigir al frontend con token
        # El frontend capturará el token del query string
        redirect_url = f"/login.html?token={jwt_token}&onboarding={str(onboarding_completed).lower()}"
        return RedirectResponse(url=redirect_url)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] OAuth callback: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error en autenticación: {str(e)}")
