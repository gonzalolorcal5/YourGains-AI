from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth_utils import get_current_user
from app.models import Usuario
import random

router = APIRouter()
security = HTTPBearer()

@router.post("/analizar-imagen")
async def analizar_imagen(
    foto: UploadFile = File(...),
    altura: int = Form(...),
    peso: int = Form(...),
    edad: int = Form(...),
    sexo: str = Form(...),
    objetivo: str = Form(...),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    # Simulación básica de análisis corporal
    tipos_cuerpo = ["ectomorfo", "mesomorfo", "endomorfo"]
    puntos_fuertes = ["piernas", "espalda", "tríceps", "glúteos"]
    puntos_debiles = ["pecho", "hombros", "bíceps", "abdomen"]

    analisis = {
        "tipo_cuerpo": random.choice(tipos_cuerpo),
        "porcentaje_grasa": random.randint(10, 25),
        "puntos_fuertes": random.sample(puntos_fuertes, 2),
        "puntos_debiles": random.sample(puntos_debiles, 2),
        "altura": altura,
        "peso": peso,
        "edad": edad,
        "sexo": sexo,
        "objetivo": objetivo
    }

    return JSONResponse(content=analisis)
