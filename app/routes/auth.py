from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from dotenv import load_dotenv
import os
from pydantic import BaseModel

from app.auth_utils import (
    create_access_token,
    verify_password,
    get_password_hash
)
from app.database import get_db
from app import models, schemas

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ACCESS_TOKEN_EXPIRE_MINUTES = 5

router = APIRouter()


# Pydantic model para capturar JSON en lugar de Form
class UserCredentials(BaseModel):
    email: str
    password: str


@router.post("/register")
def register(
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


@router.post("/login", response_model=schemas.TokenResponse)
def login(
    user: UserCredentials,
    db: Session = Depends(get_db)
):
    db_user = db.query(models.Usuario).filter(models.Usuario.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Credenciales incorrectas")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(db_user.id)},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
