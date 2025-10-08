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
from app.utils.json_helpers import deserialize_json

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
    """
    Obtiene los datos actuales del usuario desde current_routine y current_diet
    NO devuelve planes antiguos, sino la rutina y dieta actuales
    """
    try:
        # Obtener datos actuales del usuario
        current_routine = deserialize_json(usuario.current_routine or "{}", "current_routine")
        current_diet = deserialize_json(usuario.current_diet or "{}", "current_diet")
        
        # Si no hay datos actuales, obtener el último plan como fallback
        if not current_routine.get("exercises") and not current_diet.get("meals"):
            planes = db.query(Plan).filter(Plan.user_id == usuario.id).order_by(Plan.fecha_creacion.desc()).limit(1).all()
            if planes:
                plan = planes[0]
                current_routine = json.loads(plan.rutina)
                current_diet = json.loads(plan.dieta)
        
        # Devolver como si fuera un plan (manteniendo compatibilidad)
        return [
            PlanResponse(
                rutina=current_routine,
                dieta=current_diet,
                motivacion="Rutina y dieta actualizadas dinámicamente"
            )
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo datos actuales: {str(e)}")


@router.get("/user/current-routine")
def obtener_rutina_actual(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene la rutina actual del usuario desde current_routine o planes (para usuarios free)
    """
    try:
        print(f"📥 Solicitando rutina para user_id: {user_id}")
        usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not usuario:
            print(f"❌ Usuario {user_id} no encontrado")
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # 🔍 LOGGING CRÍTICO: Verificar estado del usuario
        print(f"🔍 Usuario encontrado: ID={usuario.id}, Email={usuario.email}")
        print(f"🔍 Onboarding completado: {usuario.onboarding_completed}")
        print(f"🔍 current_routine existe: {bool(usuario.current_routine)}")
        if usuario.current_routine:
            print(f"🔍 current_routine length: {len(usuario.current_routine)} chars")
            print(f"🔍 Primeros 100 chars: {usuario.current_routine[:100]}")
        else:
            print(f"❌ current_routine es NULL o vacío")
        
        # Verificar si es premium
        is_premium = usuario.is_premium or usuario.plan_type == "PREMIUM"
        print(f"💎 Usuario premium: {is_premium}")
        print(f"💎 is_premium raw: {usuario.is_premium}")
        print(f"💎 plan_type raw: {usuario.plan_type}")
        print(f"💎 Resultado final is_premium: {is_premium}")
        
        # Si es premium, usar current_routine
        if is_premium and usuario.current_routine:
            print(f"📤 Usando current_routine para usuario premium")
            current_routine = deserialize_json(usuario.current_routine, "current_routine")
            current_diet = deserialize_json(usuario.current_diet or "{}", "current_diet")
        else:
            # Si es free, usar template genérico
            print(f"📤 Usando template genérico para usuario free")
            
            # Obtener datos del usuario desde la tabla planes para personalizar el template
            plan_data = db.query(Plan).filter(Plan.user_id == user_id).first()
            if plan_data:
                user_data = {
                    "sexo": plan_data.sexo or 'masculino',
                    "altura": float(plan_data.altura) / 100 if plan_data.altura else 1.75,  # Convertir cm a metros
                    "peso": float(plan_data.peso) if plan_data.peso else 75.0,
                    "edad": int(plan_data.edad) if plan_data.edad else 25,
                    "objetivo": plan_data.objetivo or 'ganar músculo'
                }
            else:
                # Datos por defecto si no hay plan
                user_data = {
                    "sexo": 'masculino',
                    "altura": 1.75,
                    "peso": 75.0,
                    "edad": 25,
                    "objetivo": 'ganar músculo'
                }
            
            # Importar y usar template genérico
            from app.utils.routine_templates import get_generic_plan
            generic_plan = get_generic_plan(user_data)
            
            # Convertir rutina genérica al formato esperado por el frontend
            exercises = []
            if "dias" in generic_plan["rutina"]:
                for dia in generic_plan["rutina"]["dias"]:
                    if "ejercicios" in dia:  # Solo días con ejercicios
                        for ejercicio in dia["ejercicios"]:
                            exercises.append({
                                "name": ejercicio.get("nombre", ""),
                                "sets": ejercicio.get("series", 3),
                                "reps": ejercicio.get("reps", "10-12"),
                                "weight": ejercicio.get("peso", "moderado"),
                                "day": dia.get("dia", "")
                            })
            
            current_routine = {
                "exercises": exercises,
                "schedule": {},
                "created_at": "2024-01-01T00:00:00",
                "version": "generic-1.0.0",
                "is_generic": True,  # Marcar como genérico
                "titulo": generic_plan["rutina"]["titulo"]  # Incluir título personalizado
            }
            
            # Convertir dieta genérica al formato esperado
            meals = []
            for comida in generic_plan["dieta"]["comidas"]:
                meals.append({
                    "nombre": comida.get("tipo", ""),
                    "kcal": sum([alimento.get("calorias", 0) for alimento in comida.get("alimentos", [])]),
                    "alimentos": [f"{alimento['nombre']} - {alimento['cantidad']}" for alimento in comida.get("alimentos", [])],
                    "total": comida.get("total", "0 kcal")
                })
            
            current_diet = {
                "meals": meals,
                "total_kcal": sum([meal["kcal"] for meal in meals]),
                "macros": {},
                "objetivo": user_data["objetivo"],
                "created_at": "2024-01-01T00:00:00",
                "version": "generic-1.0.0",
                "is_generic": True,  # Marcar como genérico
                "titulo": generic_plan["dieta"]["titulo"]  # Incluir título personalizado
            }
        
        print(f"📊 Rutina preparada: {len(current_routine.get('exercises', []))} ejercicios")
        print(f"📊 Dieta preparada: {len(current_diet.get('meals', []))} comidas")
        
        # 🔍 LOGGING FINAL: Verificar qué se devuelve
        print(f"🚀 Devolviendo respuesta para user_id: {user_id}")
        print(f"🚀 is_premium que se devuelve: {is_premium}")
        print(f"🚀 success: True")
        print(f"🚀 current_routine existe: {bool(current_routine)}")
        print(f"🚀 current_diet existe: {bool(current_diet)}")
        
        return {
            "success": True,
            "current_routine": current_routine,
            "current_diet": current_diet,
            "user_id": usuario.id,
            "is_premium": is_premium
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo rutina actual: {str(e)}")


@router.get("/user/current-diet", dependencies=[Depends(security)])
def obtener_dieta_actual(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    """
    Obtiene la dieta actual del usuario desde current_diet
    """
    try:
        current_diet = deserialize_json(usuario.current_diet or "{}", "current_diet")
        return {
            "success": True,
            "current_diet": current_diet,
            "user_id": usuario.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo dieta actual: {str(e)}")


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
