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
    experiencia: str
    materiales: List[str]
    tipo_cuerpo: str
    nivel_actividad: str  # NUEVO - Para cálculo TMB: sedentario, ligero, moderado, activo, muy_activo
    alergias: Optional[str] = None
    restricciones_dieta: Optional[str] = None
    lesiones: Optional[str] = None
    idioma: str = "es"
    puntos_fuertes: Optional[str] = None
    puntos_debiles: Optional[str] = None
    entrenar_fuerte: bool = True
    
    # NUEVOS CAMPOS - Onboarding avanzado
    gym_goal: str  # ganar_musculo, ganar_fuerza
    nutrition_goal: str  # volumen, definicion, mantenimiento
    training_frequency: int  # 3, 4, 5, 6
    training_days: List[str]  # ["lunes", "martes", "miércoles", ...]

@router.post("/onboarding")
async def process_onboarding(
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

        # 🛡️ PROTECCIÓN 2: Verificar premium ANTES de generar
        is_premium = usuario.is_premium or usuario.plan_type == "PREMIUM"
        print(f"🔍 DEBUG ONBOARDING:")
        print(f"   Usuario ID: {usuario.id}")
        print(f"   is_premium: {usuario.is_premium}")
        print(f"   plan_type: {usuario.plan_type}")
        print(f"   ¿Usará GPT?: {is_premium}")
        
        # Convertir OnboardingRequest a diccionario
        user_data = {
            'altura': data.altura,
            'peso': data.peso,
            'edad': data.edad,
            'sexo': data.sexo,
            'experiencia': data.experiencia,
            'materiales': data.materiales,
            'tipo_cuerpo': data.tipo_cuerpo,
            'nivel_actividad': data.nivel_actividad,  # NUEVO - Para cálculo TMB
            'alergias': data.alergias or 'Ninguna',
            'restricciones': data.restricciones_dieta or 'Ninguna',
            'lesiones': data.lesiones or 'Ninguna',
            'idioma': data.idioma,
            'puntos_fuertes': data.puntos_fuertes or 'Ninguno',
            'puntos_debiles': data.puntos_debiles or 'Ninguno',
            'entrenar_fuerte': data.entrenar_fuerte,
            
            # NUEVOS CAMPOS - Onboarding avanzado
            'gym_goal': data.gym_goal,
            'nutrition_goal': data.nutrition_goal,
            'training_frequency': data.training_frequency,
            'training_days': data.training_days
        }
        
        # 🔧 FIX: Generar según tipo de usuario ANTES de guardar
        print(f"🔄 Generando NUEVO plan para usuario {usuario.id} (premium={is_premium})...")
        if is_premium:
            print(f"🤖 Generando plan personalizado con GPT (usuario premium)...")
            try:
                # 🔧 FIX: Usar directamente generar_plan_personalizado (NO usar generar_plan_safe que tenía fallback)
                from app.utils.gpt import generar_plan_personalizado
                plan_data = await generar_plan_personalizado(user_data)
                print(f"✅ Plan GPT generado: {len(plan_data.get('dieta', {}).get('comidas', []))} comidas")
            except Exception as e:
                # 🔧 FIX: Si GPT falla para premium, usar template con logs MUY claros
                print(f"❌ ERROR: GPT falló para usuario PREMIUM: {e}")
                print(f"⚠️ FALLBACK: Usando template genérico como respaldo temporal")
                print(f"⚠️ Esto NO debería pasar normalmente - verificar API key y créditos de OpenAI")
                from app.utils.routine_templates import get_generic_plan
                plan_data = get_generic_plan(user_data)
                print(f"✅ Template genérico generado como FALLBACK: {len(plan_data.get('dieta', {}).get('comidas', []))} comidas")
        else:
            print(f"📋 Generando plan genérico (usuario free)...")
            from app.utils.routine_templates import get_generic_plan
            plan_data = get_generic_plan(user_data)
            print(f"✅ Template genérico generado: {len(plan_data.get('dieta', {}).get('comidas', []))} comidas")
        
        # 🛡️ PROTECCIÓN 3: Logging detallado del plan generado
        print(f"🔍 Plan generado:")
        print(f"   - Rutina: {plan_data.get('rutina', 'NO EXISTE')}")
        print(f"   - Dieta: {plan_data.get('dieta', 'NO EXISTE')}")
        print(f"✅ Plan generado para usuario {usuario.id}")
        
        # Añadir metadata a rutina y dieta
        rutina_json = plan_data["rutina"]
        dieta_json = plan_data["dieta"]
        
        # Asegurar que la metadata esté presente
        if 'metadata' not in rutina_json:
            rutina_json['metadata'] = {}
        rutina_json['metadata'].update({
            'gym_goal': data.gym_goal,
            'training_frequency': data.training_frequency,
            'training_days': data.training_days
        })
        
        if 'metadata' not in dieta_json:
            dieta_json['metadata'] = {}
        dieta_json['metadata'].update({
            'nutrition_goal': data.nutrition_goal
        })
        
        # Guardar plan en la base de datos (tabla histórica)
        nuevo_plan = Plan(
            user_id=usuario.id,
            altura=data.altura,
            peso=str(data.peso),
            edad=data.edad,
            sexo=data.sexo,
            experiencia=data.experiencia,
            objetivo=f"{data.gym_goal} + {data.nutrition_goal}",  # Combinar objetivos para compatibilidad
            materiales=",".join(data.materiales),
            tipo_cuerpo=data.tipo_cuerpo,
            nivel_actividad=data.nivel_actividad,  # NUEVO - Para cálculo TMB
            idioma=data.idioma,
            puntos_fuertes=data.puntos_fuertes,
            puntos_debiles=data.puntos_debiles,
            entrenar_fuerte=str(data.entrenar_fuerte),
            lesiones=data.lesiones,
            alergias=data.alergias,
            restricciones_dieta=data.restricciones_dieta,
            rutina=json.dumps(rutina_json, ensure_ascii=False),
            dieta=json.dumps(dieta_json, ensure_ascii=False),
            motivacion=plan_data.get("motivacion", ""),
            fecha_creacion=datetime.utcnow()
        )

        db.add(nuevo_plan)
        # Asegurar que se asigne el ID antes del commit y guardar una copia segura
        db.flush()
        plan_id = nuevo_plan.id
        
        # 🛡️ PROTECCIÓN 4: Guardar también en current_routine y current_diet para modificaciones dinámicas
        from app.utils.json_helpers import serialize_json
        
        # Convertir rutina de formato "dias" a formato "exercises" para current_routine
        exercises = []
        if "dias" in rutina_json:
            for dia in rutina_json["dias"]:
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
            "version": "1.0.0",
            "metadata": {
                "gym_goal": data.gym_goal,
                "training_frequency": data.training_frequency,
                "training_days": data.training_days
            }
        }
        
        # Convertir dieta al formato current_diet
        # Extraer macros del plan generado (ahora están en dieta_json.macros gracias a gpt.py)
        macros_plan = dieta_json.get("macros", {})
        # Si no están en el nivel raíz, intentar desde metadata
        if not macros_plan or (isinstance(macros_plan, dict) and len(macros_plan) == 0):
            metadata_macros = dieta_json.get("metadata", {}).get("macros_objetivo", {})
            if metadata_macros:
                macros_plan = {
                    "proteina": metadata_macros.get("proteina", 0),
                    "carbohidratos": metadata_macros.get("carbohidratos", 0),
                    "grasas": metadata_macros.get("grasas", 0)
                }
        
        # 🔧 FIX CRÍTICO: Usar kcal_objetivo calculado en lugar de sumar comidas
        # El problema era que GPT puede generar comidas que suman volumen (2816.25) 
        # cuando debería ser definición (2216.25). Usamos el kcal_objetivo calculado
        # científicamente que está en dieta_json.macros.calorias
        kcal_objetivo_calculado = macros_plan.get("calorias") if isinstance(macros_plan, dict) else None
        
        # Si no hay kcal_objetivo en macros, intentar calcularlo desde el objetivo nutricional
        if not kcal_objetivo_calculado:
            from app.utils.nutrition_calculator import get_complete_nutrition_plan
            user_data_nutrition = {
                'peso': data.peso,
                'altura': data.altura,
                'edad': data.edad,
                'sexo': data.sexo,
                'nivel_actividad': data.nivel_actividad
            }
            try:
                nutrition_plan = get_complete_nutrition_plan(user_data_nutrition, data.nutrition_goal)
                kcal_objetivo_calculado = nutrition_plan.get("calorias_objetivo")
                print(f"✅ kcal_objetivo calculado desde nutrition_plan: {kcal_objetivo_calculado} kcal")
            except Exception as e:
                print(f"⚠️ Error calculando kcal_objetivo: {e}")
                # Fallback: sumar comidas (no ideal pero mejor que nada)
                kcal_objetivo_calculado = sum([meal.get("kcal", 0) for meal in dieta_json.get("comidas", [])])
                print(f"⚠️ Usando suma de comidas como fallback: {kcal_objetivo_calculado} kcal")
        
        # Si aún no hay valor, usar suma como último recurso
        if not kcal_objetivo_calculado or kcal_objetivo_calculado <= 0:
            kcal_objetivo_calculado = sum([meal.get("kcal", 0) for meal in dieta_json.get("comidas", [])])
            print(f"⚠️ Usando suma de comidas como último recurso: {kcal_objetivo_calculado} kcal")
        else:
            print(f"✅ Usando kcal_objetivo calculado: {kcal_objetivo_calculado} kcal (objetivo: {data.nutrition_goal})")
        
        current_diet = {
            "meals": dieta_json.get("comidas", []),
            "total_kcal": int(kcal_objetivo_calculado),  # 🔧 FIX: Usar kcal_objetivo calculado
            "macros": macros_plan,  # ✅ Usar macros del plan generado en lugar de {}
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "metadata": {
                "nutrition_goal": data.nutrition_goal
            }
        }
        
        # Marcar onboarding como completado y guardar current_routine/current_diet
        db.query(Usuario).filter(Usuario.id == usuario.id).update({
            "onboarding_completed": True,
            "current_routine": serialize_json(current_routine, "current_routine"),
            "current_diet": serialize_json(current_diet, "current_diet")
        })
        
        # ════════════════════════════════════════════════════════════
        # CREAR REGISTRO EN TABLA PLANES (TANTO PARA FREE COMO PREMIUM)
        # ════════════════════════════════════════════════════════════
        
        # Crear registro en tabla planes con datos reales del usuario
        nuevo_plan = Plan(
            user_id=usuario.id,
            altura=data.altura,
            peso=str(int(data.peso)),  # Guardar SIN "kg" para evitar problemas
            edad=data.edad,
            sexo=data.sexo,
            experiencia=data.experiencia,
            objetivo=f"{data.gym_goal} + {data.nutrition_goal}",  # Combinar objetivos (legacy)
            objetivo_gym=data.gym_goal,  # Objetivo de gimnasio separado
            objetivo_dieta=data.nutrition_goal,  # Objetivo nutricional separado (legacy)
            objetivo_nutricional=data.nutrition_goal,  # Objetivo nutricional separado (nuevo)
            materiales=", ".join(data.materiales),
            tipo_cuerpo=data.tipo_cuerpo if hasattr(data, 'tipo_cuerpo') else None,
            nivel_actividad=data.nivel_actividad,  # ✅ Campo obligatorio del onboarding
            idioma="es",
            puntos_fuertes=None,
            puntos_debiles=None,
            entrenar_fuerte=None,
            lesiones=data.lesiones if hasattr(data, 'lesiones') else None,
            alergias=data.alergias if hasattr(data, 'alergias') else None,
            restricciones_dieta=data.restricciones_dieta if hasattr(data, 'restricciones_dieta') else None,
            rutina=serialize_json(rutina_json, "rutina"),
            dieta=serialize_json(dieta_json, "dieta"),
            motivacion=plan_data.get("motivacion", ""),
            fecha_creacion=datetime.utcnow()
        )
        
        db.add(nuevo_plan)
        db.flush()  # Para obtener el ID del plan
        
        print(f"✅ Plan creado en tabla planes (ID: {nuevo_plan.id}) para usuario {usuario.id}")
        print(f"📊 Datos guardados en planes:")
        print(f"   - Altura: {data.altura}cm")
        print(f"   - Peso: {data.peso}kg")
        print(f"   - Edad: {data.edad} años")
        print(f"   - Sexo: {data.sexo}")
        print(f"   - Objetivo Gym: {data.gym_goal}")
        print(f"   - Objetivo Nutricional: {data.nutrition_goal}")
        print(f"   - Objetivo Combinado: {data.gym_goal} + {data.nutrition_goal}")
        
        # 🛡️ PROTECCIÓN 5: Commit y return inmediato
        db.commit()
        
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
            "plan_id": plan_id,
            "rutina": rutina_json,
            "dieta": dieta_json,
            "motivacion": plan_data.get("motivacion", "¡Vamos a por ello! Con constancia y dedicación alcanzarás tu objetivo.")
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear el plan: {str(e)}")
