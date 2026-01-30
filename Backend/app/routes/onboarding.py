# app/routes/onboarding.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
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
    experiencia: str
    materiales: str
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
    session_duration: Optional[str] = "45-60"  # Duración de sesión: "30-45", "45-60", "60-75", "75-90", "90+"

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
        # 🛡️ PROTECCIÓN: Limpiar transacciones pendientes y caché de sesión
        try:
            db.rollback()
            db.expire_all()
            print(f"✅ Sesión limpiada al inicio para user_id {usuario.id}")
        except Exception as cleanup_err:
            print(f"⚠️ Error en limpieza inicial: {cleanup_err}")

        # 🔍 VERIFICACIÓN: Eliminar plan existente si hay uno
        existing_check = db.query(Plan).filter(Plan.user_id == usuario.id).first()
        if existing_check:
            print(f"⚠️ Plan existente encontrado (id: {existing_check.id}), eliminando...")
            try:
                db.delete(existing_check)
                db.commit()
                print(f"✅ Plan existente eliminado")
            except Exception as del_err:
                print(f"❌ Error eliminando: {del_err}")
                db.rollback()

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
            'training_days': data.training_days,
            'session_duration': data.session_duration or '45-60'  # Duración de sesión
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
            materiales=data.materiales,
            tipo_cuerpo=data.tipo_cuerpo,
            nivel_actividad=data.nivel_actividad,  # NUEVO - Para cálculo TMB
            idioma=data.idioma,
            puntos_fuertes=data.puntos_fuertes,
            puntos_debiles=data.puntos_debiles,
            entrenar_fuerte=str(data.entrenar_fuerte),
            lesiones=data.lesiones,
            alergias=data.alergias,
            restricciones_dieta=data.restricciones_dieta,
            session_duration=data.session_duration if hasattr(data, 'session_duration') else '45-60',  # Guardar duración de sesión
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
        
        try:
            # Marcar onboarding como completado y guardar current_routine/current_diet
            db.query(Usuario).filter(Usuario.id == usuario.id).update({
                "onboarding_completed": True,
                "current_routine": json.dumps(current_routine, ensure_ascii=False),
                "current_diet": json.dumps(current_diet, ensure_ascii=False)
            })
            
            # ════════════════════════════════════════════════════════════
            # CREAR REGISTRO EN TABLA PLANES (TANTO PARA FREE COMO PREMIUM)
            # ════════════════════════════════════════════════════════════
            
            # ✅ SINCRONIZAR current_routine y current_diet con el Plan ANTES de crearlo
            # Esto asegura que el dashboard pueda leer los datos desde Usuario.current_routine/current_diet
            # Convertir rutina_json al formato current_routine
            exercises_plan = []
            if "dias" in rutina_json:
                for dia in rutina_json.get("dias", []):
                    for ejercicio in dia.get("ejercicios", []):
                        exercises_plan.append({
                            "name": ejercicio.get("nombre", ""),
                            "sets": ejercicio.get("series", 3),
                            "reps": ejercicio.get("repeticiones", "10-12"),
                            "weight": "moderado",
                            "day": dia.get("dia", "")
                        })
            
            current_routine_plan = {
                "exercises": exercises_plan,
                "schedule": {},
                "created_at": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "metadata": {
                    "gym_goal": data.gym_goal,
                    "training_frequency": data.training_frequency,
                    "training_days": data.training_days
                }
            }
            
            # Convertir dieta_json al formato current_diet
            # Extraer macros y calorías del plan generado
            macros_plan_diet = dieta_json.get("macros", {})
            if not macros_plan_diet or (isinstance(macros_plan_diet, dict) and len(macros_plan_diet) == 0):
                metadata_macros = dieta_json.get("metadata", {}).get("macros_objetivo", {})
                if metadata_macros:
                    macros_plan_diet = {
                        "proteina": metadata_macros.get("proteina", 0),
                        "carbohidratos": metadata_macros.get("carbohidratos", 0),
                        "grasas": metadata_macros.get("grasas", 0)
                    }
            
            # Calcular total_kcal
            total_kcal_plan = macros_plan_diet.get("calorias") if isinstance(macros_plan_diet, dict) else None
            if not total_kcal_plan or total_kcal_plan <= 0:
                total_kcal_plan = sum([meal.get("kcal", 0) for meal in dieta_json.get("comidas", [])])
            
            current_diet_plan = {
                "meals": dieta_json.get("comidas", []),
                "total_kcal": int(total_kcal_plan) if total_kcal_plan else 2200,
                "macros": macros_plan_diet,
                "objetivo": f"{data.gym_goal} + {data.nutrition_goal}",
                "created_at": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "metadata": {
                    "nutrition_goal": data.nutrition_goal
                }
            }
            
            # Actualizar Usuario con current_routine y current_diet ANTES de crear el Plan
            db.query(Usuario).filter(Usuario.id == usuario.id).update({
                "current_routine": json.dumps(current_routine_plan, ensure_ascii=False),
                "current_diet": json.dumps(current_diet_plan, ensure_ascii=False)
            })
            
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
                materiales=data.materiales,
                tipo_cuerpo=data.tipo_cuerpo if hasattr(data, 'tipo_cuerpo') else None,
                nivel_actividad=data.nivel_actividad,  # ✅ Campo obligatorio del onboarding
                idioma="es",
                puntos_fuertes=None,
                puntos_debiles=None,
                entrenar_fuerte=None,
                lesiones=data.lesiones if hasattr(data, 'lesiones') else None,
                alergias=data.alergias if hasattr(data, 'alergias') else None,
                restricciones_dieta=data.restricciones_dieta if hasattr(data, 'restricciones_dieta') else None,
                session_duration=data.session_duration if hasattr(data, 'session_duration') else '45-60',  # Guardar duración de sesión
                rutina=json.dumps(rutina_json, ensure_ascii=False),
                dieta=json.dumps(dieta_json, ensure_ascii=False),
                motivacion=plan_data.get("motivacion", ""),
                fecha_creacion=datetime.utcnow()
            )

            db.add(nuevo_plan)
            db.flush()  # Para obtener el ID del plan
            plan_id = nuevo_plan.id
            
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
        except IntegrityError as integrity_error:
            # Extraer mensaje de error original de PostgreSQL
            error_detail = str(integrity_error.orig) if hasattr(integrity_error, 'orig') else str(integrity_error)
            error_lower = error_detail.lower()
            
            print(f"🚨 IntegrityError capturado para user_id {usuario.id}")
            print(f"   Error completo: {error_detail}")
            
            # CASO 1: FOREIGN KEY VIOLATION (usuario no existe en tabla usuarios)
            if "foreign key" in error_lower or "fkey" in error_lower or "violates foreign key constraint" in error_lower:
                print(f"❌ FOREIGN KEY violation: Usuario {usuario.id} no existe en tabla usuarios")
                print(f"   Esto indica que la sesión del usuario es inválida o el usuario fue borrado")
                
                db.rollback()
                
                raise HTTPException(
                    status_code=401,
                    detail="Sesión inválida. Por favor, cierra sesión y vuelve a iniciar sesión con Google."
                )
            
            # CASO 2: UNIQUE CONSTRAINT VIOLATION (plan duplicado por concurrencia/doble submit)
            elif "unique" in error_lower or "duplicate key" in error_lower:
                print(f"⚠️ UNIQUE constraint violation: Ya existe plan para user_id {usuario.id}")
                print(f"   Probablemente causado por: doble submit, race condition, o retry del navegador")
                print(f"   Estrategia de recuperación: buscar plan existente y actualizar con datos nuevos")
                
                # Rollback para limpiar transacción fallida
                db.rollback()
                
                # Buscar el plan que causó el conflicto
                existing_plan = db.query(Plan).filter(Plan.user_id == usuario.id).first()
                
                if existing_plan:
                    print(f"✅ Plan encontrado (id: {existing_plan.id}), actualizando con datos del formulario...")
                    
                    # Actualizar TODOS los campos del plan existente
                    existing_plan.altura = data.altura
                    existing_plan.peso = str(int(data.peso))
                    existing_plan.edad = data.edad
                    existing_plan.sexo = data.sexo
                    existing_plan.experiencia = data.experiencia
                    existing_plan.objetivo = f"{data.gym_goal} + {data.nutrition_goal}"
                    existing_plan.objetivo_gym = data.gym_goal
                    existing_plan.objetivo_dieta = data.nutrition_goal
                    existing_plan.objetivo_nutricional = data.nutrition_goal
                    existing_plan.materiales = data.materiales
                    existing_plan.tipo_cuerpo = data.tipo_cuerpo if hasattr(data, 'tipo_cuerpo') else None
                    existing_plan.nivel_actividad = data.nivel_actividad
                    existing_plan.idioma = "es"
                    existing_plan.lesiones = data.lesiones if hasattr(data, 'lesiones') else None
                    existing_plan.alergias = data.alergias if hasattr(data, 'alergias') else None
                    existing_plan.restricciones_dieta = data.restricciones_dieta if hasattr(data, 'restricciones_dieta') else None
                    existing_plan.session_duration = data.session_duration if hasattr(data, 'session_duration') else '45-60'
                    existing_plan.rutina = json.dumps(rutina_json, ensure_ascii=False)
                    existing_plan.dieta = json.dumps(dieta_json, ensure_ascii=False)
                    existing_plan.motivacion = plan_data.get("motivacion", "")
                    existing_plan.fecha_creacion = datetime.utcnow()
                    
                    # ✅ SINCRONIZAR current_routine y current_diet con el Plan actualizado
                    # Convertir rutina_json al formato current_routine
                    exercises_update = []
                    if "dias" in rutina_json:
                        for dia in rutina_json.get("dias", []):
                            for ejercicio in dia.get("ejercicios", []):
                                exercises_update.append({
                                    "name": ejercicio.get("nombre", ""),
                                    "sets": ejercicio.get("series", 3),
                                    "reps": ejercicio.get("repeticiones", "10-12"),
                                    "weight": "moderado",
                                    "day": dia.get("dia", "")
                                })
                    
                    current_routine_update = {
                        "exercises": exercises_update,
                        "schedule": {},
                        "created_at": datetime.utcnow().isoformat(),
                        "version": "1.0.0",
                        "metadata": {
                            "gym_goal": data.gym_goal,
                            "training_frequency": data.training_frequency,
                            "training_days": data.training_days
                        }
                    }
                    
                    # Convertir dieta_json al formato current_diet
                    macros_update = dieta_json.get("macros", {})
                    if not macros_update or (isinstance(macros_update, dict) and len(macros_update) == 0):
                        metadata_macros = dieta_json.get("metadata", {}).get("macros_objetivo", {})
                        if metadata_macros:
                            macros_update = {
                                "proteina": metadata_macros.get("proteina", 0),
                                "carbohidratos": metadata_macros.get("carbohidratos", 0),
                                "grasas": metadata_macros.get("grasas", 0)
                            }
                    
                    # Calcular total_kcal
                    total_kcal_update = macros_update.get("calorias") if isinstance(macros_update, dict) else None
                    if not total_kcal_update or total_kcal_update <= 0:
                        total_kcal_update = sum([meal.get("kcal", 0) for meal in dieta_json.get("comidas", [])])
                    
                    current_diet_update = {
                        "meals": dieta_json.get("comidas", []),
                        "total_kcal": int(total_kcal_update) if total_kcal_update else 2200,
                        "macros": macros_update,
                        "objetivo": f"{data.gym_goal} + {data.nutrition_goal}",
                        "created_at": datetime.utcnow().isoformat(),
                        "version": "1.0.0",
                        "metadata": {
                            "nutrition_goal": data.nutrition_goal
                        }
                    }
                    
                    # Re-aplicar actualización de Usuario (onboarding_completed + current_routine/current_diet)
                    db.query(Usuario).filter(Usuario.id == usuario.id).update({
                        "onboarding_completed": True,
                        "current_routine": json.dumps(current_routine_update, ensure_ascii=False),
                        "current_diet": json.dumps(current_diet_update, ensure_ascii=False)
                    })
                    
                    db.commit()
                    db.refresh(existing_plan)
                    
                    plan_id = existing_plan.id
                    
                    print(f"✅ Plan actualizado exitosamente (id: {plan_id})")
                    print(f"   Usuario {usuario.id} puede continuar normalmente")
                    
                    # Return en formato idéntico al camino feliz
                    return {
                        "message": "Plan personalizado creado exitosamente",
                        "plan_id": plan_id,
                        "rutina": rutina_json,
                        "dieta": dieta_json,
                        "motivacion": plan_data.get("motivacion", "¡Vamos a por ello! Con constancia y dedicación alcanzarás tu objetivo.")
                    }
                else:
                    # Edge case ultra-raro: UNIQUE violation pero plan no existe
                    # Esto solo puede pasar si el plan se borra exactamente entre el error y esta búsqueda
                    print(f"❌ ANOMALÍA DETECTADA: UNIQUE violation pero no hay plan para user_id {usuario.id}")
                    print(f"   Esto es extremadamente raro y puede indicar problema de concurrencia complejo")
                    
                    db.rollback()
                    
                    raise HTTPException(
                        status_code=500,
                        detail="Error temporal al crear plan. Por favor, recarga la página e intenta de nuevo en unos segundos."
                    )
            
            # CASO 3: OTRO TIPO DE INTEGRITYERROR (NOT NULL, CHECK, etc)
            else:
                print(f"❌ IntegrityError de tipo desconocido:")
                print(f"   Error: {error_detail}")
                print(f"   Posibles causas: NOT NULL violation, CHECK constraint, o constraint personalizado")
                
                db.rollback()
                
                raise HTTPException(
                    status_code=500,
                    detail="Error al validar datos del plan. Por favor, verifica que todos los campos estén completos e intenta de nuevo."
                )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear el plan: {str(e)}")
