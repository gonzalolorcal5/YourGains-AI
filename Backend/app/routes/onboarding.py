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
from app.utils.json_helpers import serialize_json

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
    🛡️ PROTEGIDO: Una sola generación por usuario
    """
    try:
        # 🛡️ PROTECCIÓN 1: Verificar si ya tiene un plan
        existing_plan = db.query(Plan).filter(Plan.user_id == usuario.id).first()
        if existing_plan:
            print(f"⚠️ Usuario {usuario.id} ya tiene plan, retornando existente")
            return {
                "message": "Ya tienes un plan personalizado", 
                "plan_id": existing_plan.id,
                "rutina": json.loads(existing_plan.rutina),
                "dieta": json.loads(existing_plan.dieta),
                "motivacion": existing_plan.motivacion
            }

        # 🛡️ PROTECCIÓN 2: Logging antes de generar
        print(f"🔄 Generando NUEVO plan para usuario {usuario.id}")
        
        # Generar plan personalizado con GPT (UNA SOLA VEZ)
        # Convertir OnboardingRequest a diccionario
        user_data = {
            'altura': data.altura,
            'peso': data.peso,
            'edad': data.edad,
            'sexo': data.sexo,
            'objetivo': data.objetivo,
            'experiencia': data.experiencia,
            'materiales': data.materiales,
            'tipo_cuerpo': data.tipo_cuerpo,
            'alergias': data.alergias or 'Ninguna',
            'restricciones': data.restricciones_dieta or 'Ninguna',
            'lesiones': data.lesiones or 'Ninguna',
            'idioma': data.idioma,
            'puntos_fuertes': data.puntos_fuertes or 'Ninguno',
            'puntos_debiles': data.puntos_debiles or 'Ninguno',
            'entrenar_fuerte': data.entrenar_fuerte
        }
        plan_data = generar_plan_personalizado(user_data)
        
        # 🛡️ PROTECCIÓN 3: Logging detallado del plan generado
        print(f"🔍 Plan generado:")
        print(f"   - Rutina: {plan_data.get('rutina', 'NO EXISTE')}")
        print(f"   - Dieta: {plan_data.get('dieta', 'NO EXISTE')}")
        print(f"✅ Plan generado para usuario {usuario.id}")
        
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
        
        # 🛡️ PROTECCIÓN 4: Guardar también en current_routine y current_diet para modificaciones dinámicas
        from app.utils.json_helpers import serialize_json
        
        # Convertir rutina de formato "dias" a formato "exercises" para current_routine
        exercises = []
        if "dias" in plan_data["rutina"]:
            for dia in plan_data["rutina"]["dias"]:
                for ejercicio in dia.get("ejercicios", []):
                    exercises.append({
                        "name": ejercicio.get("nombre", ""),
                        "sets": ejercicio.get("series", 3),
                        "reps": ejercicio.get("repeticiones", "10-12"),
                        "weight": "moderado",
                        "day": dia.get("dia", "")
                    })
        
        current_routine = {
            "exercises": exercises,
            "schedule": {},
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
        
        # Convertir dieta al formato current_diet
        current_diet = {
            "meals": plan_data["dieta"].get("comidas", []),
            "total_kcal": sum([meal.get("kcal", 0) for meal in plan_data["dieta"].get("comidas", [])]),
            "macros": {},
            "objetivo": user_data['objetivo'],
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
        
        # Marcar onboarding como completado y guardar current_routine/current_diet
        db.query(Usuario).filter(Usuario.id == usuario.id).update({
            "onboarding_completed": True,
            "current_routine": serialize_json(current_routine, "current_routine"),
            "current_diet": serialize_json(current_diet, "current_diet")
        })
        
        # 🛡️ PROTECCIÓN 5: Commit y return inmediato
        db.commit()
        db.refresh(nuevo_plan)
        
        print(f"✅ Plan guardado en BD para usuario {usuario.id}")
        print(f"📊 Resumen guardado:")
        print(f"   - current_routine: {len(exercises)} ejercicios")
        print(f"   - current_diet: {len(current_diet.get('meals', []))} comidas")
        
        # 🔍 LOGGING CRÍTICO: Verificar que se guardó correctamente
        print(f"🔍 Verificando guardado para user_id: {usuario.id}")
        usuario_check = db.query(Usuario).filter(Usuario.id == usuario.id).first()
        if usuario_check and usuario_check.current_routine:
            print(f"✅ Verificación: current_routine guardado ({len(usuario_check.current_routine)} chars)")
            print(f"🔍 Primeros 100 chars: {usuario_check.current_routine[:100]}")
        else:
            print(f"❌ ERROR: current_routine NO guardado para user_id {usuario.id}")
            print(f"❌ Usuario encontrado: {bool(usuario_check)}")
            if usuario_check:
                print(f"❌ current_routine es: {usuario_check.current_routine}")

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
