# app/routes/onboarding.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json

from app.database import get_db
from app.models import Usuario, Plan
from app.auth_utils import get_current_user
from app.utils.gpt import generar_plan_personalizado

router = APIRouter()

class OnboardingRequest(BaseModel):
    altura: int
    peso: float
    edad: int
    sexo: str
    objetivo: str
    experiencia: str
    materiales: List[str]
    tipo_cuerpo: str
    alergias: Optional[str] = None
    restricciones_dieta: Optional[str] = None
    lesiones: Optional[str] = None
    idioma: str = "es"
    puntos_fuertes: Optional[str] = None
    puntos_debiles: Optional[str] = None
    entrenar_fuerte: bool = True

@router.post("/onboarding")
def process_onboarding(
    data: OnboardingRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    """
    Procesa el formulario de onboarding y genera un plan personalizado
    """
    try:
        # Verificar si ya tiene un plan
        existing_plan = db.query(Plan).filter(Plan.user_id == usuario.id).first()
        if existing_plan:
            return {"message": "Ya tienes un plan personalizado", "plan_id": existing_plan.id}

        # Generar plan personalizado con GPT
        plan_data = generar_plan_personalizado(data)
        
        # Guardar plan en la base de datos
        nuevo_plan = Plan(
            user_id=usuario.id,
            altura=data.altura,
            peso=str(data.peso),
            edad=data.edad,
            sexo=data.sexo,
            experiencia=data.experiencia,
            objetivo=data.objetivo,
            materiales=",".join(data.materiales),
            tipo_cuerpo=data.tipo_cuerpo,
            idioma=data.idioma,
            puntos_fuertes=data.puntos_fuertes,
            puntos_debiles=data.puntos_debiles,
            entrenar_fuerte=str(data.entrenar_fuerte),
            lesiones=data.lesiones,
            alergias=data.alergias,
            restricciones_dieta=data.restricciones_dieta,
            rutina=json.dumps(plan_data["rutina"], ensure_ascii=False),
            dieta=json.dumps(plan_data["dieta"], ensure_ascii=False),
            motivacion=plan_data["motivacion"],
            fecha_creacion=datetime.utcnow()
        )

        db.add(nuevo_plan)
        
        # Marcar onboarding como completado - actualizar directamente en la base de datos
        db.query(Usuario).filter(Usuario.id == usuario.id).update({
            "onboarding_completed": True
        })
        
        db.commit()
        db.refresh(nuevo_plan)

        return {
            "message": "Plan personalizado creado exitosamente",
            "plan_id": nuevo_plan.id,
            "rutina": plan_data["rutina"],
            "dieta": plan_data["dieta"],
            "motivacion": plan_data["motivacion"]
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear el plan: {str(e)}")
