from datetime import datetime, timedelta, timezone
from typing import Optional
import os
from pathlib import Path

from dotenv import load_dotenv, find_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Usuario

# ---------------------------
# CARGA .ENV ROBUSTA
# ---------------------------
env_path = os.getenv("ENV_PATH") or find_dotenv(".env", raise_error_if_not_found=False)
if env_path:
    load_dotenv(env_path, override=False)
else:
    base = Path(__file__).resolve().parents[1]  # .../backend
    candidate = base / ".env"
    if candidate.exists():
        load_dotenv(candidate, override=False)

# ---------------------------
# VARIABLES DE CONFIG
# ---------------------------
SECRET_KEY = (os.getenv("SECRET_KEY") or "").strip().strip('"').strip("'")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise RuntimeError("SECRET_KEY no encontrada o demasiado corta. Define una clave fuerte (≥32) en .env")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 días

# ---------------------------
# PASSWORD HASHING
# ---------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ---------------------------
# JWT
# ---------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")  # ajusta a "/auth/login" si tu ruta real es esa

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    if "sub" not in data:
        raise ValueError("Falta 'sub' en data para crear el token (usa el id de usuario).")
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "sub": str(to_encode["sub"])})  # sub como string siempre
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("sub") or not payload.get("exp"):
            return None
        return payload
    except JWTError:
        return None

# ---------------------------
# DB SESSION + USUARIO ACTUAL
# ---------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Usuario:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")

    sub = payload.get("sub")
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido (sub no es ID)")

    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    return user
