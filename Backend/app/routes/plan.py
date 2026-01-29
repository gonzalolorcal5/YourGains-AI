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
async def generar_rutina(
    datos: PlanRequest = Body(...),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    """
    Genera un plan de rutina y dieta personalizado.
    Implementa programación defensiva para manejar estructuras inconsistentes de GPT
    y problemas de sesión SQLAlchemy tras operaciones asíncronas largas.
    """
    try:
        print(f"🔄 Iniciando generación de plan para usuario {usuario.id}")
        es_premium = bool(usuario.is_premium) or (usuario.plan_type == "PREMIUM")
        print(f"💎 Usuario premium: {es_premium}")

        # Convertir PlanRequest (Pydantic) a diccionario y mapear campos
        datos_dict = datos.model_dump() if hasattr(datos, 'model_dump') else datos.dict()
        
        # Mapear 'objetivo' a 'gym_goal' para generar_plan_personalizado
        if 'objetivo' in datos_dict and 'gym_goal' not in datos_dict:
            datos_dict['gym_goal'] = datos_dict['objetivo']
        
        # Mapear 'dias_entrenamiento' a 'training_frequency' si no existe
        if 'dias_entrenamiento' in datos_dict and 'training_frequency' not in datos_dict:
            datos_dict['training_frequency'] = datos_dict['dias_entrenamiento']
        
        # Agregar 'training_days' si está disponible
        if hasattr(datos, 'training_days') and datos.training_days:
            datos_dict['training_days'] = datos.training_days
        
        # Agregar 'session_duration' si está disponible
        if hasattr(datos, 'session_duration'):
            datos_dict['session_duration'] = datos.session_duration or '45-60'
        
        # Agregar 'nutrition_goal' por defecto si no existe
        if 'nutrition_goal' not in datos_dict:
            if hasattr(datos, 'objetivo_nutricional') and datos.objetivo_nutricional:
                datos_dict['nutrition_goal'] = datos.objetivo_nutricional
            else:
                objetivo = datos_dict.get('objetivo', 'mantener_forma')
                if objetivo in ['perder_grasa', 'mantener_forma']:
                    datos_dict['nutrition_goal'] = 'definicion' if objetivo == 'perder_grasa' else 'mantenimiento'
                else:
                    datos_dict['nutrition_goal'] = 'volumen'
        
        # Agregar 'nivel_actividad' si no existe
        if 'nivel_actividad' not in datos_dict:
            datos_dict['nivel_actividad'] = 'moderado'

        # ==========================================
        # LOGGING DE DÍAS SOLICITADOS
        # ==========================================
        print(f"🗓️ Días solicitados: {datos_dict.get('training_days')}")
        print(f"📅 Frecuencia de entrenamiento: {datos_dict.get('training_frequency')} días/semana")

        # ==========================================
        # GENERAR PLAN (Operación asíncrona larga)
        # ==========================================
        print(f"🤖 Generando plan con {'GPT' if es_premium else 'template local'}...")

        # ═══ LOGGING DETALLADO DE DATOS ENVIADOS A GPT ═══
        if es_premium:
            print(f"📤 [GPT INPUT] Datos enviados a generar_plan_personalizado:")
            print(f"   - Usuario ID: {usuario.id}")
            print(f"   - Objetivo: {datos_dict.get('objetivo')} / {datos_dict.get('gym_goal')}")
            print(f"   - Training frequency: {datos_dict.get('training_frequency')} días/semana")
            print(f"   - Training days: {datos_dict.get('training_days')}")
            print(f"   - Session duration: {datos_dict.get('session_duration')}")
            print(f"   - Experiencia: {datos_dict.get('experiencia')}")
            print(f"   - Lesiones: {datos_dict.get('lesiones', 'Ninguna')}")
            print(f"   - Alergias: {datos_dict.get('alergias', 'Ninguna')}")
            print(f"   - Restricciones dieta: {datos_dict.get('restricciones_dieta', 'Ninguna')}")
            print(f"   - Nivel actividad: {datos_dict.get('nivel_actividad')}")

        if es_premium:
            plan_generado = await generar_plan_personalizado(datos_dict)
        else:
            plan_generado = _generar_plan_basico_local(datos)
        
        # ═══ LOGGING DETALLADO DE RESPUESTA GPT ═══
        print(f"")
        print(f"{'='*70}")
        print(f"📥 [GPT OUTPUT] Análisis de respuesta de GPT:")
        print(f"{'='*70}")
        print(f"Tipo de plan_generado: {type(plan_generado)}")

        if isinstance(plan_generado, dict):
            print(f"Keys disponibles: {list(plan_generado.keys())}")

            # ═══ ANALIZAR RUTINA ═══
            if 'rutina' in plan_generado:
                rutina_raw = plan_generado['rutina']
                print(f"")
                print(f"🏋️ RUTINA:")
                print(f"  - Tipo: {type(rutina_raw)}")

                if isinstance(rutina_raw, dict):
                    if 'dias' in rutina_raw:
                        dias = rutina_raw['dias']
                        print(f"  - Estructura: dict con 'dias'")
                        print(f"  - Número de días: {len(dias) if isinstance(dias, list) else 'ERROR: dias no es lista'}")

                        if isinstance(dias, list) and len(dias) > 0:
                            print(f"  - Primer día: {dias[0].get('dia', 'N/A')}")
                            ejercicios = dias[0].get('ejercicios', [])
                            print(f"  - Ejercicios primer día: {len(ejercicios)}")

                            if ejercicios:
                                print(f"  - Primer ejercicio: {ejercicios[0].get('nombre', 'N/A')}")
                            else:
                                print(f"  ⚠️ PROBLEMA: Primer día SIN ejercicios")
                        else:
                            print(f"  ❌ PROBLEMA: Lista de días VACÍA")
                    else:
                        print(f"  ⚠️ PROBLEMA: rutina es dict pero NO tiene 'dias'")
                        print(f"  - Keys de rutina: {list(rutina_raw.keys())}")
                elif isinstance(rutina_raw, list):
                    print(f"  - Estructura: lista directa")
                    print(f"  - Número de elementos: {len(rutina_raw)}")
                else:
                    print(f"  ❌ PROBLEMA: rutina no es dict ni list, es {type(rutina_raw)}")
            else:
                print(f"  ❌ PROBLEMA CRÍTICO: 'rutina' NO está en plan_generado")

            # ═══ ANALIZAR DIETA ═══
            if 'dieta' in plan_generado:
                dieta_raw = plan_generado['dieta']
                print(f"")
                print(f"🍽️ DIETA:")
                print(f"  - Tipo: {type(dieta_raw)}")

                if isinstance(dieta_raw, dict):
                    has_comidas = 'comidas' in dieta_raw
                    has_meals = 'meals' in dieta_raw
                    print(f"  - Tiene 'comidas': {has_comidas}")
                    print(f"  - Tiene 'meals': {has_meals}")

                    comidas_key = 'comidas' if has_comidas else 'meals'
                    if has_comidas or has_meals:
                        comidas = dieta_raw.get(comidas_key, [])
                        print(f"  - Número de comidas: {len(comidas) if isinstance(comidas, list) else 'ERROR: no es lista'}")

                        if isinstance(comidas, list) and len(comidas) > 0:
                            print(f"  - Primera comida: {comidas[0].get('nombre', 'N/A')}")
                        else:
                            print(f"  ⚠️ PROBLEMA: Lista de comidas VACÍA")
                    else:
                        print(f"  ⚠️ PROBLEMA: dieta NO tiene 'comidas' ni 'meals'")
                        print(f"  - Keys de dieta: {list(dieta_raw.keys())}")

                    # Macros
                    if 'macros' in dieta_raw:
                        macros = dieta_raw['macros']
                        print(f"  - Macros: {macros}")
                    else:
                        print(f"  ⚠️ ADVERTENCIA: dieta sin 'macros'")
                else:
                    print(f"  ❌ PROBLEMA: dieta no es dict, es {type(dieta_raw)}")
            else:
                print(f"  ❌ PROBLEMA CRÍTICO: 'dieta' NO está en plan_generado")

        else:
            print(f"❌ PROBLEMA CRÍTICO: plan_generado NO es dict, es {type(plan_generado)}")
            print(f"Contenido: {str(plan_generado)[:200]}...")

        print(f"{'='*70}")
        print(f"")

        # ==========================================
        # PARSING INTELIGENTE CON FALLBACKS
        # ==========================================
        
        # 1. Extraer RUTINA con fallbacks y NORMALIZACIÓN (CRÍTICO)
        rutina_data = None
        if isinstance(plan_generado, dict):
            if "rutina" in plan_generado:
                temp = plan_generado["rutina"]
                print(f"📋 Rutina encontrada en clave 'rutina'")
                
                # NORMALIZACIÓN: Si es una lista, envolverla en {"dias": [...]}
                if isinstance(temp, list):
                    print(f"🔄 Normalizando: rutina es lista, envolviendo en estructura estándar")
                    rutina_data = {"dias": temp}
                elif isinstance(temp, dict):
                    # Si ya es dict, verificar que tenga "dias"
                    if "dias" in temp:
                        rutina_data = temp
                        print(f"✅ Rutina ya tiene estructura correcta con 'dias'")
                    else:
                        # Dict sin "dias", crear estructura estándar
                        print(f"🔄 Normalizando: rutina es dict sin 'dias', creando estructura estándar")
                        rutina_data = {"dias": [temp] if temp else []}
                else:
                    # Tipo inesperado, usar fallback
                    print(f"⚠️ Tipo inesperado de rutina: {type(temp)}, usando fallback")
                    rutina_data = {"dias": []}
            elif "dias" in plan_generado:
                # GPT devolvió directamente la lista de días en el nivel raíz
                temp = plan_generado["dias"]
                print(f"📋 Rutina encontrada en clave 'dias' (estructura plana)")
                
                # NORMALIZACIÓN: Asegurar que siempre sea {"dias": [...]}
                if isinstance(temp, list):
                    rutina_data = {"dias": temp}
                else:
                    print(f"⚠️ 'dias' no es lista, envolviendo en estructura estándar")
                    rutina_data = {"dias": [temp] if temp else []}
            else:
                # Fallback: crear estructura mínima
                print(f"⚠️ No se encontró rutina en estructura esperada, usando fallback")
                rutina_data = {"dias": [], "titulo": "Rutina personalizada", "version": "1.0.0"}
        else:
            print(f"⚠️ plan_generado no es dict, es {type(plan_generado)}, usando fallback")
            rutina_data = {"dias": [], "titulo": "Rutina personalizada", "version": "1.0.0"}
        
        # VERIFICACIÓN FINAL: Asegurar que rutina_data SIEMPRE tiene estructura {"dias": [...]}
        if not isinstance(rutina_data, dict) or "dias" not in rutina_data:
            print(f"🔄 Normalización final: asegurando que rutina tiene estructura estándar")
            if isinstance(rutina_data, list):
                rutina_data = {"dias": rutina_data}
            else:
                rutina_data = {"dias": []}
        
        # Logging de verificación de estructura normalizada
        if isinstance(rutina_data, dict) and "dias" in rutina_data:
            dias_count = len(rutina_data["dias"]) if isinstance(rutina_data["dias"], list) else 0
            print(f"🔍 Verificación estructura rutina: tiene 'dias'=True, cantidad de días={dias_count}")
            if dias_count > 0:
                # Contar ejercicios totales
                ejercicios_count = 0
                for dia in rutina_data["dias"]:
                    if isinstance(dia, dict) and "ejercicios" in dia:
                        ejercicios_count += len(dia["ejercicios"]) if isinstance(dia["ejercicios"], list) else 0
                print(f"   ✅ Estructura correcta: {dias_count} días, {ejercicios_count} ejercicios encontrados")

        # 2. Extraer DIETA con fallbacks y NORMALIZACIÓN (comidas -> meals)
        dieta_data = None
        if isinstance(plan_generado, dict):
            if "dieta" in plan_generado:
                raw_dieta = plan_generado["dieta"]
                print(f"🍽️ Dieta encontrada en clave 'dieta'")
                
                # NORMALIZACIÓN: Si tiene "comidas" pero no "meals", crear "meals"
                if isinstance(raw_dieta, dict):
                    if "comidas" in raw_dieta and "meals" not in raw_dieta:
                        print(f"🔄 Normalizando: 'comidas' -> 'meals' para compatibilidad frontend")
                        dieta_data = raw_dieta.copy()
                        dieta_data["meals"] = dieta_data.pop("comidas")  # Renombrar comidas a meals
                    elif "meals" in raw_dieta:
                        dieta_data = raw_dieta
                        print(f"✅ Dieta ya tiene 'meals' (formato correcto)")
                    else:
                        dieta_data = raw_dieta
                else:
                    dieta_data = raw_dieta
                    
            elif "comidas" in plan_generado:
                # GPT devolvió directamente las comidas en el nivel raíz
                print(f"🍽️ Dieta encontrada en clave 'comidas' (estructura plana)")
                dieta_data = {"meals": plan_generado["comidas"], "macros": {}, "version": "1.0.0"}
            else:
                print(f"⚠️ No se encontró dieta en estructura esperada, usando fallback")
                dieta_data = {"meals": [], "macros": {}, "version": "1.0.0"}
        else:
            print(f"⚠️ plan_generado no es dict para dieta, usando fallback")
            dieta_data = {"meals": [], "macros": {}, "version": "1.0.0"}
        
        # Asegurar que dieta_data SIEMPRE tiene "meals" (no "comidas")
        if isinstance(dieta_data, dict) and "comidas" in dieta_data and "meals" not in dieta_data:
            print(f"🔄 Normalización final: asegurando que dieta tiene 'meals'")
            dieta_data["meals"] = dieta_data.pop("comidas")
        
        # Logging de verificación de estructura normalizada
        if isinstance(dieta_data, dict):
            has_meals = "meals" in dieta_data
            has_comidas = "comidas" in dieta_data
            print(f"🔍 Verificación estructura dieta: tiene 'meals'={has_meals}, tiene 'comidas'={has_comidas}")
            if has_meals:
                print(f"   ✅ Estructura correcta: {len(dieta_data.get('meals', []))} meals encontrados")

        # ==========================================
        # NORMALIZACIÓN DE MACROS (Compatibilidad Frontend)
        # ==========================================
        if isinstance(dieta_data, dict) and "macros" in dieta_data:
            macros = dieta_data["macros"]
            if isinstance(macros, dict):
                # 1. Proteínas: GPT usa "proteina", Frontend espera "proteinas"
                if "proteina" in macros and "proteinas" not in macros:
                    macros["proteinas"] = macros["proteina"]
                    print(f"🔄 Normalizando macros: 'proteina' -> 'proteinas'")
                elif "proteinas" in macros and "proteina" not in macros:
                    # Compatibilidad bidireccional (por seguridad)
                    macros["proteina"] = macros["proteinas"]
                
                # 2. Carbohidratos / Hidratos: GPT usa "carbohidratos", Frontend espera "hidratos"
                if "carbohidratos" in macros and "hidratos" not in macros:
                    macros["hidratos"] = macros["carbohidratos"]
                    print(f"🔄 Normalizando macros: 'carbohidratos' -> 'hidratos'")
                elif "hidratos" in macros and "carbohidratos" not in macros:
                    # Compatibilidad bidireccional (por seguridad)
                    macros["carbohidratos"] = macros["hidratos"]
                
                # 3. Grasas: GPT a veces usa "fats", Frontend espera "grasas"
                if "fats" in macros and "grasas" not in macros:
                    macros["grasas"] = macros["fats"]
                    print(f"🔄 Normalizando macros: 'fats' -> 'grasas'")
                elif "grasas" in macros and "fats" not in macros:
                    # Compatibilidad bidireccional (por seguridad)
                    macros["fats"] = macros["grasas"]
                
                # 4. Calorías: Normalizar variantes comunes
                if "calorias" in macros and "total_kcal" not in macros:
                    macros["total_kcal"] = macros["calorias"]
                elif "total_kcal" in macros and "calorias" not in macros:
                    macros["calorias"] = macros["total_kcal"]
                
                print(f"✅ Macros normalizados: {list(macros.keys())}")
            else:
                print(f"⚠️ 'macros' no es un diccionario, tipo: {type(macros)}")
        else:
            # Si no hay macros, crear estructura vacía para evitar errores en frontend
            if isinstance(dieta_data, dict):
                if "macros" not in dieta_data:
                    dieta_data["macros"] = {}
                    print(f"⚠️ No se encontraron macros, creando estructura vacía")

        # ==========================================
        # AÑADIR total_kcal EN NIVEL RAIZ (Compatibilidad Logs y Frontend)
        # ==========================================
        if isinstance(dieta_data, dict) and "macros" in dieta_data:
            macros = dieta_data["macros"]
            if isinstance(macros, dict):
                # Extraer total_kcal desde macros si no existe en nivel raíz
                if "total_kcal" not in dieta_data:
                    total_kcal_value = macros.get("total_kcal") or macros.get("calorias") or 0
                    if total_kcal_value:
                        dieta_data["total_kcal"] = int(total_kcal_value)
                        print(f"✅ total_kcal añadido en nivel raíz: {dieta_data['total_kcal']} kcal")
                else:
                    # Si ya existe, verificar que sea consistente con macros
                    existing_total_kcal = dieta_data.get("total_kcal", 0)
                    macros_total_kcal = macros.get("total_kcal") or macros.get("calorias") or 0
                    if macros_total_kcal and existing_total_kcal != macros_total_kcal:
                        # Actualizar para mantener consistencia
                        dieta_data["total_kcal"] = int(macros_total_kcal)
                        print(f"🔄 total_kcal actualizado en nivel raíz para consistencia: {dieta_data['total_kcal']} kcal")

        # 3. Extraer MOTIVACIÓN con fallbacks
        motivacion_data = None
        if isinstance(plan_generado, dict):
            if "motivacion" in plan_generado:
                motivacion_data = plan_generado["motivacion"]
            elif "mensaje" in plan_generado:
                motivacion_data = plan_generado["mensaje"]
            else:
                motivacion_data = "¡Sigue adelante con tu plan personalizado!"
        else:
            motivacion_data = "¡Sigue adelante con tu plan personalizado!"

        # ==========================================
        # SERIALIZACIÓN EXPLÍCITA A JSON
        # ==========================================
        print(f"🔄 Serializando datos a JSON...")
        try:
            rutina_str = json.dumps(rutina_data, ensure_ascii=False) if isinstance(rutina_data, (dict, list)) else str(rutina_data)
            print(f"✅ Rutina serializada: {len(rutina_str)} caracteres")
        except Exception as e:
            print(f"❌ Error serializando rutina: {e}")
            rutina_str = json.dumps({"error": "Error serializando rutina", "dias": []}, ensure_ascii=False)

        try:
            dieta_str = json.dumps(dieta_data, ensure_ascii=False) if isinstance(dieta_data, (dict, list)) else str(dieta_data)
            print(f"✅ Dieta serializada: {len(dieta_str)} caracteres")
        except Exception as e:
            print(f"❌ Error serializando dieta: {e}")
            dieta_str = json.dumps({"error": "Error serializando dieta", "meals": []}, ensure_ascii=False)

        try:
            motivacion_str = json.dumps(motivacion_data, ensure_ascii=False) if isinstance(motivacion_data, (dict, list)) else str(motivacion_data)
        except Exception as e:
            print(f"❌ Error serializando motivación: {e}")
            motivacion_str = "¡Sigue adelante con tu plan personalizado!"

        # ==========================================
        # GESTIÓN DE SESIÓN ROBUSTA (Instancia Fresca)
        # ==========================================
        # CRÍTICO: Después de await largo, el objeto usuario puede estar "detached"
        # O puede estar asociado a otra sesión. Obtener instancia fresca para evitar conflictos
        print(f"🔗 Obteniendo instancia fresca de usuario desde BD...")
        user_fresh = db.query(Usuario).get(usuario.id)
        if not user_fresh:
            raise HTTPException(status_code=404, detail="Usuario no encontrado después de generación")
        print(f"✅ Instancia fresca obtenida: ID={user_fresh.id}")

        # ==========================================
        # CREAR REGISTRO EN TABLA PLAN
        # ==========================================
        print(f"💾 Creando registro en tabla Plan...")
        nuevo_plan = Plan(
            user_id=user_fresh.id,
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
            session_duration=getattr(datos, 'session_duration', '45-60'),  # Guardar duración de sesión
            rutina=rutina_str,
            dieta=dieta_str,
            motivacion=motivacion_str,
            fecha_creacion=datetime.utcnow()
        )
        db.add(nuevo_plan)
        print(f"✅ Plan añadido a sesión")

        # ==========================================
        # ACTUALIZAR ESTADO ACTUAL DEL USUARIO
        # ==========================================
        # Usar user_fresh (instancia fresca) en lugar de usuario (puede estar detached)
        print(f"🔄 Actualizando current_routine y current_diet del usuario...")
        user_fresh.current_routine = rutina_str
        user_fresh.current_diet = dieta_str
        print(f"✅ Campos actualizados en objeto usuario (instancia fresca)")

        # ==========================================
        # COMMIT TRANSACCIÓN
        # ==========================================
        print(f"💾 Haciendo commit de transacción...")
        db.commit()
        print(f"✅ Commit exitoso")
        
        db.refresh(nuevo_plan)
        print(f"✅ Plan refrescado desde BD")

        # ==========================================
        # PREPARAR RESPUESTA
        # ==========================================
        # Usar los datos originales (no serializados) para la respuesta
        # Normalizar motivación a string
        if isinstance(motivacion_data, str):
            motivacion_final = motivacion_data
        elif isinstance(motivacion_data, (dict, list)):
            motivacion_final = json.dumps(motivacion_data, ensure_ascii=False)
        else:
            motivacion_final = str(motivacion_data) if motivacion_data else "¡Sigue adelante con tu plan personalizado!"
        
        print(f"✅ Respuesta preparada exitosamente")
        return PlanResponse(
            rutina=rutina_data,
            dieta=dieta_data,
            motivacion=motivacion_final
        )

    except HTTPException:
        # Re-raise HTTPExceptions sin modificar
        raise
    except Exception as e:
        print(f"❌ ERROR CRÍTICO en generar_rutina: {e}")
        import traceback
        print(f"📋 Traceback completo:")
        traceback.print_exc()
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
    Incluye fallback para usuarios antiguos que tienen Plan pero no current_routine/current_diet
    """
    try:
        # 1. Intentar cargar desde Usuario.current_routine y current_diet
        current_routine = deserialize_json(usuario.current_routine or "{}", "current_routine")
        current_diet = deserialize_json(usuario.current_diet or "{}", "current_diet")
        
        # 2. Verificar si están vacíos
        routine_is_empty = (
            not current_routine or
            current_routine == {} or
            not current_routine.get("exercises") or
            len(current_routine.get("exercises", [])) == 0
        )
        
        diet_is_empty = (
            not current_diet or
            current_diet == {} or
            not current_diet.get("meals") or
            len(current_diet.get("meals", [])) == 0
        )
        
        # 3. Si AMBOS están vacíos, hacer fallback desde Plan
        if routine_is_empty and diet_is_empty:
            print(f"⚠️ current_routine y current_diet vacíos para usuario {usuario.id}, intentando fallback desde Plan...")
            plan = db.query(Plan).filter(Plan.user_id == usuario.id).order_by(Plan.id.desc()).first()
            
            if plan:
                print(f"✅ Plan encontrado (ID: {plan.id}), cargando datos...")
                try:
                    # Cargar rutina y dieta desde Plan
                    routine_from_plan = json.loads(plan.rutina or '{}')
                    diet_from_plan = json.loads(plan.dieta or '{}')
                    
                    # Convertir routine_from_plan["dias"] al formato exercises (si existe)
                    if isinstance(routine_from_plan, dict) and "dias" in routine_from_plan:
                        exercises = []
                        for dia in routine_from_plan.get("dias", []):
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
                        
                        # Si hay metadata en la rutina original, preservarla
                        if "metadata" in routine_from_plan:
                            current_routine["metadata"] = routine_from_plan["metadata"]
                    else:
                        # Si ya está en formato exercises, usar directamente
                        current_routine = routine_from_plan
                    
                    # Usar diet_from_plan directamente (ya está en formato correcto)
                    # Pero asegurar que tenga estructura current_diet si viene en formato GPT
                    if isinstance(diet_from_plan, dict):
                        # Si tiene "comidas" pero no "meals", convertir
                        if "comidas" in diet_from_plan and "meals" not in diet_from_plan:
                            diet_from_plan["meals"] = diet_from_plan.pop("comidas")
                        
                        # Asegurar que tenga total_kcal
                        if "total_kcal" not in diet_from_plan:
                            macros = diet_from_plan.get("macros", {})
                            if isinstance(macros, dict):
                                total_kcal = macros.get("calorias") or macros.get("total_kcal") or 0
                                if total_kcal:
                                    diet_from_plan["total_kcal"] = int(total_kcal)
                                else:
                                    # Calcular desde comidas
                                    meals = diet_from_plan.get("meals", [])
                                    diet_from_plan["total_kcal"] = sum([meal.get("kcal", 0) for meal in meals])
                        
                        current_diet = diet_from_plan
                    else:
                        current_diet = diet_from_plan
                    
                    print(f"✅ Fallback exitoso: {len(current_routine.get('exercises', []))} ejercicios, {len(current_diet.get('meals', []))} comidas")
                    
                    # 4. OPCIONALMENTE sincronizar de vuelta a Usuario para que la próxima vez no necesite fallback
                    try:
                        usuario.current_routine = json.dumps(current_routine, ensure_ascii=False)
                        usuario.current_diet = json.dumps(current_diet, ensure_ascii=False)
                        db.commit()
                        print(f"✅ Datos sincronizados de vuelta a Usuario.current_routine/current_diet")
                    except Exception as sync_err:
                        print(f"⚠️ Error sincronizando a Usuario (no crítico): {sync_err}")
                        db.rollback()
                        # Continuar aunque falle la sincronización
                    
                except Exception as fallback_err:
                    print(f"❌ Error en fallback desde Plan: {fallback_err}")
                    import traceback
                    traceback.print_exc()
                    # Continuar con datos vacíos si falla el fallback
            else:
                print(f"⚠️ No se encontró Plan para usuario {usuario.id}, usando datos vacíos")
        
        # Devolver como si fuera un plan (manteniendo compatibilidad)
        return [
            PlanResponse(
                rutina=current_routine,
                dieta=current_diet,
                motivacion="Rutina y dieta actualizadas dinámicamente"
            )
        ]
    except Exception as e:
        print(f"❌ Error obteniendo datos actuales: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error obteniendo datos actuales: {str(e)}")


@router.get("/plan/datos-actuales", dependencies=[Depends(security)])
def obtener_datos_actuales(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    """
    Obtiene los datos del último Plan del usuario para pre-llenar formulario de nueva rutina.
    Incluye training_frequency y training_days desde current_routine o metadata del Plan.
    Solo lectura, no modifica nada.
    """
    try:
        import json
        
        # Intentar obtener training_days y training_frequency desde current_routine (más actualizado)
        training_frequency = None
        training_days = None
        
        if usuario.current_routine:
            try:
                current_routine_data = json.loads(usuario.current_routine)
                if isinstance(current_routine_data, dict) and 'metadata' in current_routine_data:
                    metadata = current_routine_data['metadata']
                    training_frequency = metadata.get('training_frequency')
                    training_days = metadata.get('training_days')
            except (json.JSONDecodeError, AttributeError, KeyError):
                pass
        
        # Obtener último Plan del usuario
        plan = db.query(Plan).filter(Plan.user_id == usuario.id).order_by(Plan.fecha_creacion.desc()).first()
        
        if not plan:
            # Si no hay plan, retornar valores por defecto
            return {
                "altura": 175,
                "peso": 75.0,
                "edad": 25,
                "sexo": "hombre",
                "experiencia": "principiante",
                "objetivo_gym": "ganar_musculo",
                "objetivo_nutricional": "volumen",
                "materiales": "",
                "tipo_cuerpo": None,
                "nivel_actividad": "moderado",
                "puntos_fuertes": None,
                "puntos_debiles": None,
                "entrenar_fuerte": None,
                "lesiones": None,
                "alergias": None,
                "restricciones_dieta": None,
                "dias_entrenamiento": training_frequency or 4,
                "training_frequency": training_frequency or 4,
                "training_days": training_days or ["lunes", "martes", "jueves", "viernes"]
            }
        
        # Si no se encontraron en current_routine, intentar desde metadata del Plan
        if training_frequency is None or training_days is None:
            try:
                rutina_json = json.loads(plan.rutina) if plan.rutina else {}
                if isinstance(rutina_json, dict) and 'metadata' in rutina_json:
                    metadata = rutina_json['metadata']
                    if training_frequency is None:
                        training_frequency = metadata.get('training_frequency')
                    if training_days is None:
                        training_days = metadata.get('training_days')
            except (json.JSONDecodeError, AttributeError, KeyError):
                pass
        
        # Retornar datos del plan
        peso_float = float(plan.peso) if plan.peso else 75.0
        
        return {
            "altura": plan.altura,
            "peso": peso_float,
            "edad": plan.edad,
            "sexo": plan.sexo,
            "experiencia": plan.experiencia,
            "objetivo_gym": plan.objetivo_gym or plan.objetivo or "ganar_musculo",
            "objetivo_nutricional": plan.objetivo_nutricional or plan.objetivo_dieta or "volumen",
            "materiales": plan.materiales or "",
            "tipo_cuerpo": plan.tipo_cuerpo,
            "nivel_actividad": plan.nivel_actividad or "moderado",
            "puntos_fuertes": plan.puntos_fuertes,
            "puntos_debiles": plan.puntos_debiles,
            "entrenar_fuerte": plan.entrenar_fuerte,
            "lesiones": plan.lesiones or None,
            "alergias": plan.alergias or None,
            "restricciones_dieta": plan.restricciones_dieta or None,
            "dias_entrenamiento": training_frequency or 4,
            "training_frequency": training_frequency or 4,
            "training_days": training_days or ["lunes", "martes", "jueves", "viernes"],
            "session_duration": plan.session_duration or "45-60"
        }
    except Exception as e:
        # Si hay error, retornar valores por defecto (no fallar)
        import json
        training_frequency = None
        training_days = None
        
        # Intentar obtener desde current_routine incluso en caso de error
        try:
            if usuario.current_routine:
                current_routine_data = json.loads(usuario.current_routine)
                if isinstance(current_routine_data, dict) and 'metadata' in current_routine_data:
                    metadata = current_routine_data['metadata']
                    training_frequency = metadata.get('training_frequency')
                    training_days = metadata.get('training_days')
        except:
            pass
        
        return {
            "altura": 175,
            "peso": 75.0,
            "edad": 25,
            "sexo": "hombre",
            "experiencia": "principiante",
            "objetivo_gym": "ganar_musculo",
            "objetivo_nutricional": "volumen",
            "materiales": "",
            "tipo_cuerpo": None,
            "nivel_actividad": "moderado",
            "puntos_fuertes": None,
            "puntos_debiles": None,
            "entrenar_fuerte": None,
            "lesiones": None,
            "alergias": None,
            "restricciones_dieta": None,
            "dias_entrenamiento": training_frequency or 4,
            "training_frequency": training_frequency or 4,
            "training_days": training_days or ["lunes", "martes", "jueves", "viernes"],
            "session_duration": "45-60"
        }


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
        
        # Obtener metadata de training_frequency y training_days para validación
        training_frequency = None
        training_days = None
        
        if usuario.current_routine:
            try:
                import json
                current_routine_data = json.loads(usuario.current_routine)
                if isinstance(current_routine_data, dict) and 'metadata' in current_routine_data:
                    metadata = current_routine_data['metadata']
                    training_frequency = metadata.get('training_frequency')
                    training_days = metadata.get('training_days')
            except (json.JSONDecodeError, AttributeError, KeyError):
                pass
        
        # Si no se encontraron en current_routine, intentar desde el último Plan
        if training_frequency is None or training_days is None:
            try:
                import json
                plan = db.query(Plan).filter(Plan.user_id == usuario.id).order_by(Plan.fecha_creacion.desc()).first()
                if plan and plan.rutina:
                    rutina_json = json.loads(plan.rutina)
                    if isinstance(rutina_json, dict) and 'metadata' in rutina_json:
                        metadata = rutina_json['metadata']
                        if training_frequency is None:
                            training_frequency = metadata.get('training_frequency')
                        if training_days is None:
                            training_days = metadata.get('training_days')
            except (json.JSONDecodeError, AttributeError, KeyError):
                pass

        # ─── FALLBACK: Si current_routine/current_diet vacíos, cargar desde Plan (usuarios antiguos) ───
        routine = deserialize_json(usuario.current_routine or "{}", "current_routine")
        diet = deserialize_json(usuario.current_diet or "{}", "current_diet")

        routine_is_empty = (
            routine == {} or
            not routine.get("exercises") or
            len(routine.get("exercises", [])) == 0
        )
        diet_is_empty = (
            diet == {} or
            not diet.get("meals") or
            len(diet.get("meals", [])) == 0
        )

        if routine_is_empty and diet_is_empty:
            print(f"⚠️ Usuario {user_id}: current_routine/diet vacíos, buscando en Plan...")
            plan = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.id.desc()).first()

            if plan:
                print(f"✅ Plan encontrado (ID: {plan.id}), cargando datos...")
                try:
                    routine_from_plan = json.loads(plan.rutina or '{}')
                    diet_from_plan = json.loads(plan.dieta or '{}')

                    if isinstance(routine_from_plan, dict) and "dias" in routine_from_plan:
                        exercises = []
                        for dia in routine_from_plan.get("dias", []):
                            for ejercicio in dia.get("ejercicios", []):
                                exercises.append({
                                    "name": ejercicio.get("nombre", ""),
                                    "sets": ejercicio.get("series", 3),
                                    "reps": ejercicio.get("repeticiones", "10-12"),
                                    "weight": "moderado",
                                    "day": dia.get("dia", "")
                                })
                        routine = {
                            "exercises": exercises,
                            "schedule": {},
                            "created_at": datetime.utcnow().isoformat(),
                            "version": "1.0.0"
                        }
                        if "metadata" in routine_from_plan:
                            routine["metadata"] = routine_from_plan["metadata"]
                    else:
                        routine = routine_from_plan

                    if isinstance(diet_from_plan, dict):
                        if "comidas" in diet_from_plan and "meals" not in diet_from_plan:
                            diet_from_plan["meals"] = diet_from_plan.pop("comidas")
                        if "total_kcal" not in diet_from_plan:
                            macros = diet_from_plan.get("macros", {})
                            if isinstance(macros, dict):
                                total_kcal = macros.get("calorias") or macros.get("total_kcal") or 0
                                if total_kcal:
                                    diet_from_plan["total_kcal"] = int(total_kcal)
                                else:
                                    diet_from_plan["total_kcal"] = sum(
                                        [meal.get("kcal", 0) for meal in diet_from_plan.get("meals", [])]
                                    )
                        diet = diet_from_plan
                    else:
                        diet = diet_from_plan

                    print(f"✅ Fallback exitoso: {len(routine.get('exercises', []))} ejercicios, {len(diet.get('meals', []))} comidas")

                    try:
                        usuario.current_routine = json.dumps(routine, ensure_ascii=False)
                        usuario.current_diet = json.dumps(diet, ensure_ascii=False)
                        db.commit()
                        db.refresh(usuario)
                        print(f"✅ Datos sincronizados de vuelta a Usuario.current_routine/current_diet")
                    except Exception as sync_err:
                        print(f"⚠️ Error sincronizando a Usuario (no crítico): {sync_err}")
                        db.rollback()
                except Exception as fallback_err:
                    print(f"❌ Error en fallback desde Plan: {fallback_err}")
                    import traceback
                    traceback.print_exc()

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
        
        # 🔍 Verificar si la rutina premium está lista (no es template free)
        is_premium_routine_ready = False
        if is_premium and current_routine:
            try:
                # Verificar que no sea template genérico
                is_generic = current_routine.get('is_generic', False)
                version = current_routine.get('version', '')
                
                # Verificar que no sea template free
                # Los templates free tienen: is_generic=True o version="generic-1.0.0"
                is_template_free = (
                    is_generic is True or
                    (isinstance(version, str) and 'generic' in version.lower())
                )
                
                # Verificar si tiene marcadores de rutina GPT generada
                # Las rutinas GPT tienen: is_premium_generated=True o versión >= 2.0 o estructura "dias"
                has_premium_markers = False
                
                # Verificar si está en formato JSON string (desde BD)
                routine_to_check = current_routine
                if isinstance(current_routine, str):
                    try:
                        routine_to_check = json.loads(current_routine)
                    except:
                        pass
                
                # Si es dict, verificar marcadores
                if isinstance(routine_to_check, dict):
                    # Marcador 1: is_premium_generated
                    if routine_to_check.get('is_premium_generated') is True:
                        has_premium_markers = True
                    
                    # Marcador 2: versión >= 2.0 (y no es generic)
                    version_str = str(routine_to_check.get('version', '0'))
                    if version_str and 'generic' not in version_str.lower():
                        try:
                            # Extraer número de versión (ej: "2.0.0" -> 2.0)
                            version_num = float(version_str.split('.')[0] + '.' + version_str.split('.')[1] if '.' in version_str else version_str)
                            if version_num >= 2.0:
                                has_premium_markers = True
                        except:
                            pass
                    
                    # Marcador 3: estructura "dias" (formato GPT)
                    if 'dias' in routine_to_check and isinstance(routine_to_check['dias'], list):
                        has_premium_markers = True
                
                # Verificar también en current_routine de la BD (formato JSON string)
                if usuario.current_routine:
                    routine_str = usuario.current_routine.lower()
                    # Verificar que no contenga texto del template free
                    template_markers = ['plan gratuito', 'template', 'generic', 'genérico']
                    has_template_text = any(marker in routine_str for marker in template_markers)
                    
                    if has_template_text:
                        is_template_free = True
                
                # Resultado final: es premium ready si es premium, tiene rutina, NO es template free, y tiene marcadores premium
                is_premium_routine_ready = (
                    is_premium and
                    current_routine is not None and
                    not is_template_free and
                    has_premium_markers
                )
                
                print(f"🔍 Verificación is_premium_routine_ready:")
                print(f"   is_premium: {is_premium}")
                print(f"   current_routine existe: {current_routine is not None}")
                print(f"   is_template_free: {is_template_free}")
                print(f"   has_premium_markers: {has_premium_markers}")
                print(f"   ✅ is_premium_routine_ready: {is_premium_routine_ready}")
            except Exception as e:
                print(f"⚠️ Error verificando is_premium_routine_ready: {e}")
                is_premium_routine_ready = False
        
        return {
            "success": True,
            "current_routine": current_routine,
            "current_diet": current_diet,
            "metadata": {
                "training_frequency": training_frequency,
                "training_days": training_days
            },
            "user_id": usuario.id,
            "is_premium": is_premium,
            "is_premium_routine_ready": is_premium_routine_ready
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
