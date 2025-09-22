from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth_utils import get_current_user
from app.schemas import PlanRequest, PlanResponse
from app.models import Usuario, Plan
from datetime import datetime
from fastapi.security import HTTPBearer
from typing import List
import json
from app.utils.pdf_generator import generate_routine_pdf

# 👇 importa tu generador GPT
from app.utils.gpt import generar_plan_personalizado

router = APIRouter()
security = HTTPBearer()


# ---------- helpers FREEMIUM ----------

def _generar_plan_basico_local(datos: PlanRequest) -> dict:
    """
    Genera un plan 'teaser' sencillo para cuentas FREE.
    No llama a GPT (cero coste) y devuelve rutina/dieta parciales.
    """
    # Rutina: solo 2 días ejemplo
    rutina = {
        "dias": [
            {
                "nombre": "Día 1 - Full Body (parcial)",
                "ejercicios": [
                    {"nombre": "Sentadilla", "series": 3, "reps": "8-10"},
                    {"nombre": "Press banca", "series": 3, "reps": "8-10"},
                    {"nombre": "Remo con barra", "series": 3, "reps": "8-10"},
                ]
            },
            {
                "nombre": "Día 2 - Empuje (parcial)",
                "ejercicios": [
                    {"nombre": "Press militar", "series": 3, "reps": "8-10"},
                    {"nombre": "Fondos", "series": 3, "reps": "8-10"},
                    {"nombre": "Elevaciones laterales", "series": 3, "reps": "12-15"},
                ]
            }
        ],
        "consejos": [
            "Calienta 10 min antes de empezar.",
            "Progresión: añade 1-2 repeticiones o 2.5 kg si completas el rango.",
            "Descansa 60-90s entre series."
        ],
        "locked": True,  # indicamos al frontend que esto es parcial
        "cta": "Desbloquea los 4-5 días restantes y todos los ajustes premium."
    }

    # Dieta: 2 comidas ejemplo
    dieta = {
        "resumen": "Este es un ejemplo parcial. Calcularemos todo al detalle cuando pases a Premium.",
        "comidas": [
            {
                "nombre": "Desayuno (parcial)",
                "kcal": 450,
                "macros": {"proteinas": 30, "hidratos": 55, "grasas": 12},
                "alimentos": [
                    "250ml leche o bebida vegetal",
                    "40g avena",
                    "1 plátano",
                    "10g mantequilla cacahuete"
                ],
                "alternativas": [
                    "Yogur con frutos rojos y avena"
                ]
            },
            {
                "nombre": "Comida (parcial)",
                "kcal": 650,
                "macros": {"proteinas": 40, "hidratos": 70, "grasas": 18},
                "alimentos": [
                    "200g pollo",
                    "150g arroz",
                    "100g brócoli",
                    "1 cda aceite de oliva"
                ],
                "alternativas": [
                    "Pasta integral con atún y tomate"
                ]
            }
        ],
        "consejos_finales": [
            "2-3L de agua/día.",
            "Proteínas 1.6–2.2 g/kg.",
            "Mejorarás la precisión con Premium."
        ],
        "locked": True,
        "cta": "Desbloquea la dieta completa (5 comidas, macros y alternativas)."
    }

    motivacion = "¡Vas por buen camino! Desbloquea el plan completo para maximizar resultados."

    return {"rutina": rutina, "dieta": dieta, "motivacion": motivacion}


# ---------- endpoints ----------

@router.post("/generar-rutina", response_model=PlanResponse, dependencies=[Depends(security)])
def generar_rutina(
    datos: PlanRequest = Body(...),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    try:
        es_premium = bool(usuario.is_premium) or (usuario.plan_type == "PREMIUM")

        if es_premium:
            # Plan completo con GPT
            plan_generado = generar_plan_personalizado(datos)
        else:
            # Plan parcial local (sin GPT)
            plan_generado = _generar_plan_basico_local(datos)

        rutina_str = json.dumps(plan_generado["rutina"]) if isinstance(plan_generado["rutina"], (dict, list)) else plan_generado["rutina"]
        dieta_str = json.dumps(plan_generado["dieta"]) if isinstance(plan_generado["dieta"], (dict, list)) else plan_generado["dieta"]
        motivacion_str = json.dumps(plan_generado["motivacion"]) if isinstance(plan_generado["motivacion"], (dict, list)) else plan_generado["motivacion"]

        nuevo_plan = Plan(
            user_id=usuario.id,
            altura=datos.altura,
            peso=datos.peso,
            edad=datos.edad,
            sexo=datos.sexo,
            experiencia=datos.experiencia,
            objetivo=datos.objetivo,
            materiales=datos.materiales,
            tipo_cuerpo=datos.tipo_cuerpo,
            idioma=datos.idioma,
            puntos_fuertes=datos.puntos_fuertes,
            puntos_debiles=datos.puntos_debiles,
            entrenar_fuerte=datos.entrenar_fuerte,
            lesiones=datos.lesiones,
            alergias=datos.alergias,
            restricciones_dieta=datos.restricciones_dieta,
            rutina=rutina_str,
            dieta=dieta_str,
            motivacion=motivacion_str,
            fecha_creacion=datetime.utcnow()
        )

        db.add(nuevo_plan)
        db.commit()
        db.refresh(nuevo_plan)

        return PlanResponse(
            rutina=plan_generado["rutina"],
            dieta=plan_generado["dieta"],
            motivacion=plan_generado["motivacion"]
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al generar plan: {str(e)}")


@router.get("/planes", response_model=List[PlanResponse], dependencies=[Depends(security)])
def obtener_planes(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    planes = db.query(Plan).filter(Plan.user_id == usuario.id).order_by(Plan.fecha_creacion.desc()).all()
    return [
        PlanResponse(
            rutina=json.loads(plan.rutina),
            dieta=json.loads(plan.dieta),
            motivacion=plan.motivacion if isinstance(plan.motivacion, str) else json.dumps(plan.motivacion)
        )
        for plan in planes
    ]


@router.get("/planes/{plan_id}/pdf", dependencies=[Depends(security)])
def descargar_plan_pdf(
    plan_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    """
    Descarga un plan específico como PDF.
    """
    try:
        # Buscar el plan del usuario
        plan = db.query(Plan).filter(
            Plan.id == plan_id,
            Plan.user_id == usuario.id
        ).first()
        
        if not plan:
            raise HTTPException(status_code=404, detail="Plan no encontrado")
        
        # Preparar los datos del plan
        plan_data = {
            "rutina": json.loads(plan.rutina) if isinstance(plan.rutina, str) else plan.rutina,
            "dieta": json.loads(plan.dieta) if isinstance(plan.dieta, str) else plan.dieta,
            "motivacion": plan.motivacion if isinstance(plan.motivacion, str) else json.loads(plan.motivacion)
        }
        
        # Generar el PDF
        pdf_content = generate_routine_pdf(plan_data, usuario.email)
        
        # Crear nombre de archivo con fecha
        fecha_str = plan.fecha_creacion.strftime("%Y%m%d")
        filename = f"rutina_personalizada_{fecha_str}.pdf"
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(pdf_content))
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar PDF: {str(e)}")


@router.get("/planes/ultimo/pdf", dependencies=[Depends(security)])
def descargar_ultimo_plan_pdf(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    """
    Descarga el último plan del usuario como PDF.
    """
    try:
        # Buscar el último plan del usuario
        plan = db.query(Plan).filter(
            Plan.user_id == usuario.id
        ).order_by(Plan.fecha_creacion.desc()).first()
        
        if not plan:
            raise HTTPException(status_code=404, detail="No tienes planes generados")
        
        # Preparar los datos del plan
        plan_data = {
            "rutina": json.loads(plan.rutina) if isinstance(plan.rutina, str) else plan.rutina,
            "dieta": json.loads(plan.dieta) if isinstance(plan.dieta, str) else plan.dieta,
            "motivacion": plan.motivacion if isinstance(plan.motivacion, str) else json.loads(plan.motivacion)
        }
        
        # Generar el PDF
        pdf_content = generate_routine_pdf(plan_data, usuario.email)
        
        # Crear nombre de archivo con fecha
        fecha_str = plan.fecha_creacion.strftime("%Y%m%d")
        filename = f"rutina_personalizada_{fecha_str}.pdf"
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(pdf_content))
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar PDF: {str(e)}")
