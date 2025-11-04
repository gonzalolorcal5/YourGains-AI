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
        
        # Validar user_id
        if not user_id or user_id <= 0:
            print(f"❌ user_id inválido: {user_id}")
            raise HTTPException(status_code=400, detail="ID de usuario inválido")
        
        # Validar sesión de BD
        if db is None:
            print(f"❌ Sesión de BD es None")
            raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")
        
        # IMPORTANTE: Invalidar cache de SQLAlchemy y hacer query fresca
        db.expire_all()
        
        usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not usuario:
            print(f"❌ Usuario {user_id} no encontrado")
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # 🔍 LOGGING CRÍTICO: Verificar estado del usuario
        # Forzar refresh del objeto desde BD para obtener datos frescos
        try:
            db.refresh(usuario)
        except Exception:
            # Si refresh falla, hacer query nueva
            db.expire_all()
            usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
            if not usuario:
                raise HTTPException(status_code=404, detail="Usuario no encontrado después de refresh")
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
            
            # 🔍 DEBUG: Verificar contenido de current_diet después de deserializar
            print(f"🔍 DEBUG current_diet después de deserializar:")
            print(f"   Tipo: {type(current_diet)}")
            print(f"   Tiene 'macros': {'macros' in current_diet if isinstance(current_diet, dict) else 'N/A'}")
            if isinstance(current_diet, dict) and 'macros' in current_diet:
                macros = current_diet['macros']
                print(f"   macros['proteina']: {macros.get('proteina', 'NO ENCONTRADO')}")
                print(f"   macros['carbohidratos']: {macros.get('carbohidratos', 'NO ENCONTRADO')}")
                print(f"   macros['grasas']: {macros.get('grasas', 'NO ENCONTRADO')}")
                print(f"   total_kcal: {current_diet.get('total_kcal', 'NO ENCONTRADO')}")
            else:
                print(f"   ❌ current_diet no tiene macros o no es dict")
            
            # Si current_diet está vacío o no tiene macros, intentar leer desde Plan.dieta como respaldo
            if (not current_diet or 
                not isinstance(current_diet, dict) or 
                not current_diet.get('macros') or 
                not any(current_diet.get('macros', {}).values())):
                print(f"⚠️ current_diet vacío o sin macros, intentando leer desde Plan.dieta...")
                plan_data = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.id.desc()).first()
                if plan_data and plan_data.dieta:
                    try:
                        dieta_plan = json.loads(plan_data.dieta)
                        print(f"✅ Leyendo desde Plan.dieta (Plan ID: {plan_data.id})")
                        # Actualizar current_diet con los datos del Plan
                        if isinstance(dieta_plan, dict):
                            # 🔧 FIX CRÍTICO: Convertir dieta_plan al formato current_diet correctamente
                            # dieta_plan tiene estructura GPT (comidas), current_diet necesita (meals, total_kcal)
                            
                            # Obtener macros de dieta_plan
                            macros_dieta = dieta_plan.get("macros", {})
                            
                            # 🔧 FIX: Leer total_kcal correctamente desde dieta_plan
                            total_kcal = None
                            if macros_dieta and "calorias" in macros_dieta:
                                total_kcal = macros_dieta["calorias"]
                            elif dieta_plan.get("metadata", {}).get("calorias_objetivo"):
                                total_kcal = dieta_plan["metadata"]["calorias_objetivo"]
                            elif dieta_plan.get("macros", {}).get("calorias"):
                                total_kcal = dieta_plan["macros"]["calorias"]
                            else:
                                # Calcular desde objetivo nutricional
                                objetivo_nutricional = plan_data.objetivo_nutricional or plan_data.objetivo_dieta or "mantenimiento"
                                if " + " in objetivo_nutricional:
                                    objetivo_nutricional = objetivo_nutricional.split(" + ")[-1]
                                
                                from app.utils.nutrition_calculator import get_complete_nutrition_plan
                                user_data_nutrition = {
                                    'peso': float(plan_data.peso) if plan_data.peso else 75.0,
                                    'altura': int(plan_data.altura) if plan_data.altura else 175,
                                    'edad': int(plan_data.edad) if plan_data.edad else 25,
                                    'sexo': plan_data.sexo or 'masculino',
                                    'nivel_actividad': plan_data.nivel_actividad or 'moderado'
                                }
                                try:
                                    nutrition_plan = get_complete_nutrition_plan(user_data_nutrition, objetivo_nutricional)
                                    total_kcal = nutrition_plan.get("calorias_objetivo")
                                    print(f"✅ total_kcal calculado desde objetivo nutricional: {total_kcal} kcal")
                                except Exception as e:
                                    print(f"⚠️ Error calculando total_kcal: {e}")
                                    total_kcal = sum([comida.get("kcal", 0) for comida in dieta_plan.get("comidas", [])])
                            
                            if not total_kcal or total_kcal <= 0:
                                total_kcal = sum([comida.get("kcal", 0) for comida in dieta_plan.get("comidas", [])])
                            
                            # Convertir a formato current_diet
                            current_diet = {
                                "meals": dieta_plan.get("comidas", []),
                                "total_kcal": int(total_kcal),
                                "macros": macros_dieta,
                                "objetivo": plan_data.objetivo_nutricional or plan_data.objetivo or "mantenimiento",
                                "created_at": datetime.utcnow().isoformat(),
                                "version": "1.0.0"
                            }
                            
                            print(f"✅ current_diet actualizado desde Plan.dieta")
                            print(f"   macros: {current_diet.get('macros', {})}")
                            print(f"   total_kcal: {current_diet.get('total_kcal', 'N/A')}")
                    except Exception as e:
                        print(f"❌ Error leyendo Plan.dieta: {e}")
        elif is_premium and not usuario.current_routine:
            # Usuario premium pero sin current_routine → intentar generar o usar plan de tabla
            print(f"⚠️ Usuario premium sin current_routine, intentando usar plan de tabla planes...")
            plan_data = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.id.desc()).first()
            if plan_data and plan_data.rutina and plan_data.dieta:
                try:
                    # Usar el plan guardado en tabla planes
                    print(f"✅ Usando plan de tabla planes (ID: {plan_data.id})")
                    rutina_plan = json.loads(plan_data.rutina)
                    dieta_plan = json.loads(plan_data.dieta)
                    
                    # Convertir a formato current_routine/current_diet
                    exercises = []
                    if "dias" in rutina_plan:
                        for dia in rutina_plan["dias"]:
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
                        "created_at": "2024-01-01T00:00:00",
                        "version": "1.0.0",
                        "is_generic": False
                    }
                    
                    # Obtener macros de dieta_plan (ya calculados)
                    macros_dieta = dieta_plan.get("macros", {})
                    # Si no existen, calcular desde comidas
                    if not macros_dieta or all(v == 0 for v in macros_dieta.values()):
                        proteina_total = sum(int(comida.get("macros", {}).get("proteinas", 0) or 0) for comida in dieta_plan.get("comidas", []))
                        carbohidratos_total = sum(int(comida.get("macros", {}).get("hidratos", 0) or 0) for comida in dieta_plan.get("comidas", []))
                        grasas_total = sum(int(comida.get("macros", {}).get("grasas", 0) or 0) for comida in dieta_plan.get("comidas", []))
                        macros_dieta = {
                            "proteina": round(proteina_total, 1),
                            "carbohidratos": round(carbohidratos_total, 1),
                            "grasas": round(grasas_total, 1)
                        }
                    
                    # 🔧 FIX CRÍTICO: Leer total_kcal correctamente desde dieta_plan
                    # El bug era que buscaba "total_calorias" que no existe en el JSON de GPT
                    # GPT guarda las calorías en: macros.calorias o metadata.calorias_objetivo
                    total_kcal = None
                    if macros_dieta and "calorias" in macros_dieta:
                        total_kcal = macros_dieta["calorias"]
                    elif dieta_plan.get("metadata", {}).get("calorias_objetivo"):
                        total_kcal = dieta_plan["metadata"]["calorias_objetivo"]
                    elif dieta_plan.get("macros", {}).get("calorias"):
                        total_kcal = dieta_plan["macros"]["calorias"]
                    else:
                        # Si no hay calorías en macros, calcular desde objetivo nutricional
                        objetivo_nutricional = plan_data.objetivo_nutricional or plan_data.objetivo_dieta or "mantenimiento"
                        # Extraer solo la parte nutricional del objetivo si está combinado
                        if " + " in objetivo_nutricional:
                            objetivo_nutricional = objetivo_nutricional.split(" + ")[-1]
                        
                        from app.utils.nutrition_calculator import get_complete_nutrition_plan
                        user_data_nutrition = {
                            'peso': float(plan_data.peso) if plan_data.peso else 75.0,
                            'altura': int(plan_data.altura) if plan_data.altura else 175,
                            'edad': int(plan_data.edad) if plan_data.edad else 25,
                            'sexo': plan_data.sexo or 'masculino',
                            'nivel_actividad': plan_data.nivel_actividad or 'moderado'
                        }
                        try:
                            nutrition_plan = get_complete_nutrition_plan(user_data_nutrition, objetivo_nutricional)
                            total_kcal = nutrition_plan.get("calorias_objetivo")
                            print(f"✅ total_kcal calculado desde objetivo nutricional: {total_kcal} kcal (objetivo: {objetivo_nutricional})")
                        except Exception as e:
                            print(f"⚠️ Error calculando total_kcal desde objetivo: {e}")
                            # Fallback: sumar comidas
                            total_kcal = sum([comida.get("kcal", 0) for comida in dieta_plan.get("comidas", [])])
                            print(f"⚠️ Usando suma de comidas como fallback: {total_kcal} kcal")
                    
                    # Si aún no hay valor, usar suma como último recurso
                    if not total_kcal or total_kcal <= 0:
                        total_kcal = sum([comida.get("kcal", 0) for comida in dieta_plan.get("comidas", [])])
                        print(f"⚠️ Usando suma de comidas como último recurso: {total_kcal} kcal")
                    
                    current_diet = {
                        "meals": dieta_plan.get("comidas", []),
                        "total_kcal": int(total_kcal),  # 🔧 FIX: Usar total_kcal calculado correctamente
                        "macros": macros_dieta,
                        "objetivo": plan_data.objetivo_nutricional or plan_data.objetivo or "mantenimiento",
                        "created_at": "2024-01-01T00:00:00",
                        "version": "1.0.0",
                        "is_generic": False
                    }
                    
                    print(f"✅ Plan convertido: {len(exercises)} ejercicios, {len(current_diet.get('meals', []))} comidas")
                except Exception as e:
                    print(f"❌ Error usando plan de tabla: {e}, cayendo a template genérico")
                    plan_data = None  # Forzar usar template genérico
            
            if not plan_data or not plan_data.rutina:
                # Fallback: template genérico (pero aún es premium, solo muestra template)
                print(f"📤 Usando template genérico para usuario premium (sin plan disponible)")
                plan_data = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.id.desc()).first()
                # Continuar al bloque de template genérico abajo (línea ~302)
        else:
            # Si es free, usar template genérico
            print(f"📤 Usando template genérico para usuario free")
            
            # Obtener datos del usuario desde el Plan más reciente para personalizar el template
            plan_data = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.id.desc()).first()
            if plan_data:
                # Obtener datos físicos del plan más reciente
                peso = float(plan_data.peso) if plan_data.peso else 75.0
                altura_cm = float(plan_data.altura) if plan_data.altura else 175.0
                altura_m = altura_cm / 100  # Convertir cm a metros
                edad = int(plan_data.edad) if plan_data.edad else 25
                sexo = plan_data.sexo or 'masculino'
                objetivo = plan_data.objetivo or 'ganar músculo'
                
                user_data = {
                    "sexo": sexo,
                    "altura": altura_cm,  # Pasar altura en cm directamente
                    "peso": peso,
                    "edad": edad,
                    "objetivo": objetivo,
                    "nivel_actividad": plan_data.nivel_actividad  # Campo obligatorio del onboarding, siempre tiene valor
                }
                
                print(f"📊 Datos usuario para rutina FREE:")
                print(f"   Peso: {peso}kg")
                print(f"   Altura: {altura_cm}cm ({altura_m}m)")
                print(f"   Edad: {edad} años")
                print(f"   Sexo: {sexo}")
                print(f"   Objetivo: {objetivo}")
                print(f"   Nivel actividad: {plan_data.nivel_actividad}")  # Campo obligatorio del onboarding
            else:
                # Datos por defecto si no hay plan
                user_data = {
                    "sexo": 'masculino',
                    "altura": 1.75,
                    "peso": 75.0,
                    "edad": 25,
                    "objetivo": 'ganar músculo',
                    "nivel_actividad": 'ligero'  # ✅ AÑADIDO: nivel_actividad en fallback
                }
                print(f"⚠️ No se encontró plan para usuario {user_id}, usando datos por defecto")
                print(f"   Nivel actividad por defecto: ligero")
            
            # Importar y usar template genérico
            try:
                from app.utils.routine_templates import get_generic_plan
                print(f"📦 Generando plan genérico con datos: {user_data}")
                generic_plan = get_generic_plan(user_data)
                print(f"✅ Plan genérico generado exitosamente")
            except Exception as e:
                print(f"❌ Error generando plan genérico: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error generando rutina genérica: {str(e)}")
            
            # Convertir rutina genérica al formato esperado por el frontend
            try:
                print(f"🔄 Convirtiendo rutina genérica al formato del frontend...")
                exercises = []
                if "dias" in generic_plan["rutina"]:
                    print(f"📋 Procesando {len(generic_plan['rutina']['dias'])} días de rutina")
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
                    # Los alimentos ya vienen como strings en el formato correcto
                    alimentos_lista = comida.get("alimentos", [])
                    kcal_comida = comida.get("kcal", 0)
                    
                    meals.append({
                        "nombre": comida.get("nombre", ""),
                        "kcal": kcal_comida,
                        "alimentos": alimentos_lista,  # Ya están en formato string correcto
                        "total": f"{kcal_comida} kcal"
                    })
                
                # Obtener el resumen de la dieta genérica (ya contiene las calorías correctas)
                resumen_dieta = generic_plan["dieta"].get("resumen", f"Plan nutricional para {user_data['objetivo']}")
                print(f"📊 Resumen de dieta genérica: {resumen_dieta}")
                
                # Obtener macros de generic_plan (ya calculados en get_generic_plan)
                macros_dieta = generic_plan["dieta"].get("macros", {})
                # Si no existen, calcular desde comidas
                if not macros_dieta or all(v == 0 for v in macros_dieta.values()):
                    proteina_total = sum(int(comida.get("macros", {}).get("proteinas", 0) or 0) for comida in generic_plan["dieta"].get("comidas", []))
                    carbohidratos_total = sum(int(comida.get("macros", {}).get("hidratos", 0) or 0) for comida in generic_plan["dieta"].get("comidas", []))
                    grasas_total = sum(int(comida.get("macros", {}).get("grasas", 0) or 0) for comida in generic_plan["dieta"].get("comidas", []))
                    macros_dieta = {
                        "proteina": round(proteina_total, 1),
                        "carbohidratos": round(carbohidratos_total, 1),
                        "grasas": round(grasas_total, 1)
                    }
                
                current_diet = {
                    "meals": meals,
                    "total_kcal": sum([meal["kcal"] for meal in meals]),
                    "macros": macros_dieta,
                    "objetivo": user_data["objetivo"],
                    "created_at": "2024-01-01T00:00:00",
                    "version": "generic-1.0.0",
                    "is_generic": True,  # Marcar como genérico
                    "titulo": resumen_dieta  # Usar resumen como título (ya contiene calorías correctas)
                }
                
                print(f"✅ Conversión completada: {len(exercises)} ejercicios, {len(meals)} comidas")
            except Exception as e:
                print(f"❌ Error convirtiendo plan genérico: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error convirtiendo plan genérico: {str(e)}")
        
        print(f"📊 Rutina preparada: {len(current_routine.get('exercises', []))} ejercicios")
        print(f"📊 Dieta preparada: {len(current_diet.get('meals', []))} comidas")
        
        # 🔍 LOGGING FINAL: Verificar qué se devuelve
        print(f"🚀 Devolviendo respuesta para user_id: {user_id}")
        print(f"🚀 is_premium que se devuelve: {is_premium}")
        print(f"🚀 success: True")
        print(f"🚀 current_routine existe: {bool(current_routine)}")
        print(f"🚀 current_diet existe: {bool(current_diet)}")
        
        # 🔍 LOGGING CRÍTICO: Verificar macros en current_diet antes de devolver
        if isinstance(current_diet, dict):
            print(f"🔍 VERIFICACIÓN FINAL DE MACROS:")
            print(f"   current_diet.tipo: {type(current_diet)}")
            print(f"   current_diet tiene 'macros': {'macros' in current_diet}")
            if 'macros' in current_diet:
                macros = current_diet['macros']
                print(f"   macros.tipo: {type(macros)}")
                print(f"   macros contenido: {macros}")
                if isinstance(macros, dict):
                    print(f"   ✅ Macros válidos encontrados:")
                    print(f"      proteina: {macros.get('proteina', 'NO ENCONTRADO')}")
                    print(f"      carbohidratos: {macros.get('carbohidratos', 'NO ENCONTRADO')}")
                    print(f"      grasas: {macros.get('grasas', 'NO ENCONTRADO')}")
                else:
                    print(f"   ❌ macros no es dict, es: {type(macros)}")
            else:
                print(f"   ❌ current_diet NO tiene 'macros'")
                print(f"   current_diet keys: {list(current_diet.keys())}")
            print(f"   total_kcal: {current_diet.get('total_kcal', 'NO ENCONTRADO')}")
        
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
        # CRÍTICO: Refrescar datos del usuario desde BD para obtener la versión más reciente
        db.refresh(usuario)
        
        current_diet = deserialize_json(usuario.current_diet or "{}", "current_diet")
        
        # Si no hay current_diet, intentar obtener del último plan como fallback
        if not current_diet or not current_diet.get("meals") and not current_diet.get("comidas"):
            planes = db.query(Plan).filter(Plan.user_id == usuario.id).order_by(Plan.fecha_creacion.desc()).limit(1).all()
            if planes:
                plan = planes[0]
                current_diet = json.loads(plan.dieta)
        
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
