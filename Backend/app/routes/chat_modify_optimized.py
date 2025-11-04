#!/usr/bin/env python3
"""
Endpoint optimizado para chat con modificaciones dinámicas
Versión senior con manejo eficiente de base de datos y mejor rendimiento
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from openai import OpenAI
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils.functions_definitions import (
    OPENAI_FUNCTIONS, 
    FUNCTION_HANDLERS, 
    get_system_prompt_for_function,
    validate_function_arguments
)
from app.utils.function_handlers_optimized import (
    handle_modify_routine_focus,
    handle_adjust_routine_difficulty,
    handle_adjust_menstrual_cycle,
    handle_recalculate_macros,
    handle_substitute_food,
    handle_generate_alternatives,
    handle_simplify_diet,
    handle_substitute_exercise,
    handle_modify_routine_equipment,
    handle_revert_modification
)

# Diccionario para guardar confirmaciones pendientes
# En producción, usar Redis o base de datos
pending_confirmations: Dict[int, Dict[str, Any]] = {}
from app.utils.function_handlers_optimized import handle_modify_routine_injury
from app.utils.database_service import db_service
from app.utils.allergy_detection import process_user_allergies, validate_food_against_allergies, get_allergy_safe_alternatives

logger = logging.getLogger(__name__)
router = APIRouter()

# Configurar OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 💰 MODELO DINÁMICO: Usar modelo barato en desarrollo, caro en producción
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

if ENVIRONMENT == 'production':
    MODEL = "gpt-4-turbo-preview"  # Para usuarios reales (~$0.03/1K tokens)
    logger.info("🚀 Usando GPT-4 Turbo para PRODUCCIÓN")
else:
    MODEL = "gpt-3.5-turbo"  # Para testing (~$0.0015/1K tokens - 20x más barato)
    logger.info("💡 Usando GPT-3.5 Turbo para DESARROLLO (20x más barato)")

class ChatRequest(BaseModel):
    """Modelo para requests de chat con modificaciones"""
    message: str
    user_id: int
    conversation_history: Optional[List[Dict[str, str]]] = []

class ChatResponse(BaseModel):
    """Modelo para respuestas de chat"""
    response: str
    modified: bool
    changes: List[str]
    function_used: Optional[str] = None
    # Campos adicionales para actualización de planes
    success: Optional[bool] = None
    plan_updated: Optional[bool] = None
    summary: Optional[str] = None

async def get_user_context(user_id: int, db: Session) -> Dict[str, Any]:
    """
    Obtiene el contexto completo del usuario para el chat - VERSIÓN OPTIMIZADA
    
    Args:
        user_id: ID del usuario
        db: Sesión de base de datos
        
    Returns:
        Diccionario con contexto del usuario
    """
    try:
        logger.info(f"Obteniendo contexto para usuario {user_id}")
        
        # Usar el servicio optimizado de base de datos
        user_data = await db_service.get_user_complete_data(user_id, db)
        
        logger.info(f"Contexto obtenido para usuario {user_id}")
        return user_data
        
    except ValueError as e:
        logger.error(f"Usuario no encontrado {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario {user_id} no encontrado"
        )
    except Exception as e:
        logger.error(f"Error obteniendo contexto del usuario {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo contexto del usuario: {str(e)}"
        )

def build_system_prompt(user_context: Dict[str, Any]) -> str:
    """
    Construye el prompt del sistema con el contexto completo del usuario - VERSIÓN OPTIMIZADA
    
    Args:
        user_context: Contexto del usuario
        
    Returns:
        Prompt del sistema
    """
    # Obtener objetivo actual de la dieta
    current_diet = user_context.get('current_diet', {})
    current_goal = current_diet.get('objetivo', 'mantenimiento')
    
    system_prompt = f"""Eres un entrenador personal de IA especializado en modificaciones dinámicas de rutinas y dietas.

CONTEXTO DEL USUARIO:
- Sexo: {user_context.get('sexo', 'No especificado')}
- Rutina: {len(user_context.get('current_routine', {}).get('exercises', []))} ejercicios
- Dieta: {len(user_context.get('current_diet', {}).get('meals', []))} comidas, {user_context.get('current_diet', {}).get('total_kcal', 0)} kcal
- Objetivo: {current_goal}
- Lesiones: {len(user_context.get('injuries', []))}
- Alergias: {user_context.get('alergias', 'ninguna')}

CAPACIDADES:
RUTINAS: modify_routine_injury, modify_routine_focus, adjust_routine_difficulty, substitute_exercise, modify_routine_equipment
DIETA: recalculate_diet_macros, substitute_disliked_food, generate_meal_alternatives, simplify_diet_plan
GENERAL: revert_last_modification

🔄 DETECCIÓN DE REVERTIR CAMBIOS - Ejemplos:
- "Deshaz el último cambio" → revert_last_modification()
- "Revertir cambios" → revert_last_modification()
- "Vuelve atrás" → revert_last_modification()
- "Deshacer modificación" → revert_last_modification()
- "Deshaz la última modificación" → revert_last_modification()
- "Quiero volver atrás" → revert_last_modification()
- "Cancela el último cambio" → revert_last_modification()
- "Deshacer el último cambio" → revert_last_modification()

VARIACIONES DE DETECCIÓN:
- "deshaz", "deshacer", "revertir", "volver atrás", "cancelar", "deshacer cambios" → revert_last_modification

DETECCIÓN AUTOMÁTICA:
🔥 CAMBIOS DE PESO → recalculate_diet_macros(weight_change_kg=X, goal="{current_goal}")
🎯 CAMBIOS DE OBJETIVO → recalculate_diet_macros(weight_change_kg=0.0, goal="nuevo_objetivo")
🍽️ ALIMENTOS NO DESEADOS → substitute_disliked_food(disliked_food="X", meal_type="desayuno/almuerzo/cena/snack/todos")
💪 EJERCICIOS NO DESEADOS → substitute_exercise(exercise_to_replace="X", replacement_reason="no_gusta", target_muscles="Y")
🏋️ FALTA DE EQUIPAMIENTO → modify_routine_equipment(missing_equipment="X", available_equipment="Y")
💪 AJUSTES DE RUTINA → adjust_routine_difficulty(difficulty_change="increase/decrease", reason="X")
🎯 ENFOQUE EN ÁREAS → modify_routine_focus(focus_area="X", intensity="medium/high")
🏥 LESIONES → modify_routine_injury(body_part="X", injury_type="Y", severity="mild/moderate/severe")

🍽️ DETECCIÓN DE ALIMENTOS NO DESEADOS - Ejemplos:
- "No me gusta la leche" → substitute_disliked_food(disliked_food="leche", meal_type="todos")
- "No quiero avena" → substitute_disliked_food(disliked_food="avena", meal_type="todos")
- "Odio el pollo" → substitute_disliked_food(disliked_food="pollo", meal_type="todos")
- "No me gusta el desayuno" → generate_meal_alternatives(meal_type="desayuno", num_alternatives=3)
- "Quiero cambiar el desayuno" → generate_meal_alternatives(meal_type="desayuno", num_alternatives=3)
- "No me gusta mi cena" → generate_meal_alternatives(meal_type="cena", num_alternatives=3)
- "Sustituye el pollo por pavo" → substitute_disliked_food(disliked_food="pollo", meal_type="todos")
- "Cambia la leche" → substitute_disliked_food(disliked_food="leche", meal_type="todos")
- "No como avena" → substitute_disliked_food(disliked_food="avena", meal_type="todos")
- "Prefiero no comer pollo" → substitute_disliked_food(disliked_food="pollo", meal_type="todos")

VARIACIONES DE DETECCIÓN DE ALIMENTOS:
- "no me gusta", "no quiero", "odio", "no como", "no puedo comer", "prefiero no" → Alimento no deseado
- Si menciona comida completa ("no me gusta mi desayuno") → generate_meal_alternatives
- Si menciona alimento específico ("no me gusta la leche") → substitute_disliked_food

⚠️ IMPORTANTE - DIFICULTAD DE RUTINA:
Cuando el usuario diga que la rutina es "muy fácil", "muy difícil", "muy facil", "muy dificil", "demasiado fácil", etc.:
- NO uses adjust_routine_difficulty automáticamente
- Responde con un mensaje educativo explicando que no hay rutinas más fáciles o difíciles por sí mismas
- La dificultad depende de la INTENSIDAD que le ponga el usuario
- Explica que debe:
  1. Aumentar el peso en los ejercicios
  2. Buscar llegar más cerca del fallo muscular
  3. Cuando llegas cercano al fallo muscular en un entorno de 8-12 reps, da igual la rutina que uses, te va a costar
- Sé educativo y motivador, no técnico

Ejemplo de respuesta correcta:
"Entiendo tu preocupación. Me gustaría aclarar algo importante: no hay rutinas más fáciles o más difíciles por sí mismas. Todo depende de la intensidad que le pongas tú. Si te resulta muy fácil, aumenta el peso en los ejercicios y busca llegar más cerca del fallo muscular. Cuando llegas cercano al fallo muscular en un entorno de 8-12 reps, da igual la rutina que uses, te va a costar. La clave está en la intensidad con la que ejecutas cada serie, no en cambiar la estructura de la rutina."

DETECCIÓN DE LESIONES - Ejemplos:
- "Me duele el hombro" → modify_routine_injury(body_part="hombro", injury_type="dolor_muscular", severity="mild")
- "Tengo molestias en la rodilla" → modify_routine_injury(body_part="rodilla", injury_type="dolor_muscular", severity="mild")
- "Me he lesionado el hombro" → modify_routine_injury(body_part="hombro", injury_type="lesion", severity="moderate")
- "Me lesioné la espalda" → modify_routine_injury(body_part="espalda", injury_type="lesion", severity="moderate")
- "Me duele mucho la rodilla" → modify_routine_injury(body_part="rodilla", injury_type="dolor_muscular", severity="moderate")
- "Tengo una tendinitis en el hombro" → modify_routine_injury(body_part="hombro", injury_type="tendinitis", severity="moderate")
- "No puedo entrenar el hombro porque me duele" → modify_routine_injury(body_part="hombro", injury_type="dolor_muscular", severity="mild")

VARIACIONES DE DETECCIÓN:
- "me duele", "duele", "dolor en", "tengo dolor" → Dolor/malestar
- "tengo molestias", "molestias en", "molesta" → Molestias (severidad: mild)
- "me lesioné", "me he lesionado", "tengo una lesión", "estoy lesionado" → Lesión (severidad: moderate)
- "mucho dolor", "duele mucho", "muy doloroso" → Dolor intenso (severidad: moderate/severe)

🎯 DETECCIÓN DE AJUSTES CALÓRICOS:
Cuando el usuario mencione cambios en déficit/superávit calórico, debes identificar:

1. **La cantidad del ajuste** (ej: 500 kcal, 300 kcal)
2. **Si es déficit (-) o superávit (+)**
3. **Si es ABSOLUTO, INCREMENTAL o AMBIGUO**

### 🔍 REGLAS DE DETECCIÓN:

**ABSOLUTO (reemplazar déficit/superávit total):**
Palabras clave: "de", "total de", "cambiar a", "quiero un déficit de"
- "Quiero un déficit de 500 kcal" → calorie_adjustment=-500, is_incremental=false
- "Cambiar a superávit de 300 kcal" → calorie_adjustment=300, is_incremental=false
- "Definición de 400 kcal" → calorie_adjustment=-400, is_incremental=false
- "Superávit de 250" → calorie_adjustment=250, is_incremental=false

**INCREMENTAL (añadir al déficit/superávit actual):**
Palabras clave: "más", "adicional", "extra", "añade", "incrementa", "aumenta en", "reduce en"
- "Añade 100 kcal más al déficit" → calorie_adjustment=-100, is_incremental=true
- "Incrementa el superávit 50 kcal" → calorie_adjustment=50, is_incremental=true
- "Reduce 200 kcal adicionales" → calorie_adjustment=-200, is_incremental=true
- "100 kcal más de déficit" → calorie_adjustment=-100, is_incremental=true

**AMBIGUO (pedir confirmación):**
Palabras clave: "aumenta a", "sube a", "baja a" (la preposición "a" es ambigua)
- "Aumenta el déficit a 500 kcal" → calorie_adjustment=-500, is_incremental=null
- "Sube el superávit a 400" → calorie_adjustment=400, is_incremental=null
- "Cambia el déficit a 600" → calorie_adjustment=-600, is_incremental=null

PALABRAS CLAVE:
🔥 Peso: "subí", "bajé", "gané", "perdí", "kg", "kilo", "peso"
🎯 Objetivo: "fuerza", "hipertrofia", "volumen", "definir", "mantener"
💪 Dificultad: "fácil", "difícil", "intensidad", "rutina"
🎯 Enfoque: "enfocar", "más", "pecho", "piernas", "brazos", "espalda", "hombros"
🏥 Lesiones: "duele", "dolor", "lesión", "molestias", "molesta", "me lesioné", "me he lesionado", "tengo molestias", "hombro", "rodilla", "espalda", "cuádriceps"
💪 Ejercicios: "no me gusta", "odio", "no tengo", "no puedo hacer"
🏋️ Equipamiento: "no tengo", "no hay", "máquina", "barra", "mancuernas"

SINÓNIMOS:
- "pectoral/pectorales" = "pecho"
- "cuádriceps/cuadriceps" = "piernas"
- "deltoides" = "hombros"
- "dorsales" = "espalda"
- "bíceps/tríceps" = "brazos"

INSTRUCCIONES:
1. Usa funciones automáticamente cuando detectes cambios
2. Sé proactivo en detectar y aplicar modificaciones
3. Explica claramente qué cambios se realizaron
4. Sé empático y profesional
5. Prioriza la seguridad alimentaria
6. ⚠️ IMPORTANTE: Cuando el usuario diga que la rutina es muy fácil/difícil, NO ajustes la rutina automáticamente. Responde educativamente explicando que la dificultad depende de la intensidad (peso y cercanía al fallo muscular)"""
    
    return system_prompt

async def execute_function_handler(
    function_name: str, 
    arguments: Dict[str, Any], 
    user_id: int,
    db: Session
) -> Dict[str, Any]:
    """
    Ejecuta el handler correspondiente a una función - VERSIÓN OPTIMIZADA
    
    Args:
        function_name: Nombre de la función
        arguments: Argumentos de la función
        user_id: ID del usuario
        db: Sesión de base de datos
        
    Returns:
        Resultado de la ejecución
    """
    try:
        # Logging detallado de argumentos
        logger.info(f"🔍 Función: {function_name}")
        logger.info(f"📝 Argumentos recibidos: {arguments}")
        logger.info(f"📊 Tipo de argumentos: {type(arguments)}")
        
        # Log detallado de cada argumento individual
        for key, value in arguments.items():
            value_str = str(value)[:100] if value else "None"  # Limitar a 100 chars
            logger.info(f"  ➤ {key}: {value_str} (type: {type(value).__name__})")
        
        # Normalizar argumentos: filtrar None para funciones que aceptan parámetros opcionales
        if function_name == "recalculate_diet_macros":
            # 🔧 FIX: Soportar peso absoluto ("ahora peso 87kg") y mapear a weight_change_kg
            try:
                # Obtener peso actual desde el plan más reciente
                from app.models import Plan
                plan_actual = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.id.desc()).first()
                peso_actual_float = None
                if plan_actual and plan_actual.peso is not None:
                    try:
                        peso_actual_float = float(str(plan_actual.peso).replace("kg", "").strip())
                    except Exception:
                        peso_actual_float = None

                # Detectar posibles claves de peso absoluto
                new_weight_candidates = []
                for k in ["new_weight_kg", "peso", "weight", "weight_kg"]:
                    if k in arguments and arguments[k] is not None:
                        try:
                            new_weight_candidates.append(float(str(arguments[k]).replace("kg", "").strip()))
                        except Exception:
                            pass

                new_weight_val = new_weight_candidates[0] if new_weight_candidates else None

                # Caso 1: Viene explícitamente new_weight_* → calcular delta
                if new_weight_val is not None and peso_actual_float is not None:
                    arguments["weight_change_kg"] = round(new_weight_val - peso_actual_float, 2)
                    # Eliminar claves auxiliares para no romper validación
                    for k in ["new_weight_kg", "peso", "weight", "weight_kg"]:
                        arguments.pop(k, None)

                # Caso 2: Viene weight_change_kg pero parece ser peso absoluto (valor grande)
                elif "weight_change_kg" in arguments and arguments["weight_change_kg"] is not None and peso_actual_float is not None:
                    try:
                        wc = float(arguments["weight_change_kg"])
                        # Heurística: si está en rango de peso humano (30-300), trátalo como peso absoluto
                        if 30 <= wc <= 300:
                            arguments["weight_change_kg"] = round(wc - peso_actual_float, 2)
                    except Exception:
                        pass
            except Exception:
                # No bloquear si falla la normalización; continuar con los argumentos originales
                pass

            clean_arguments = {
                k: v for k, v in arguments.items()
                if v is not None and k in [
                    "weight_change_kg",
                    "goal",
                    "target_calories",
                    "calorie_adjustment",
                    "is_incremental",
                    "adjustment_type"
                ]
            }
            logger.info(f"✅ Argumentos válidos para {function_name}")
            logger.info(f"   Originales: {arguments}")
            logger.info(f"   Limpios: {clean_arguments}")
            if not clean_arguments:
                logger.error("❌ No hay argumentos válidos después de filtrar")
                return {
                    "success": False,
                    "message": "No se detectó ningún cambio válido en tu mensaje",
                    "changes": []
                }
            arguments = clean_arguments

        # Validar argumentos (después de limpieza)
        if not validate_function_arguments(function_name, arguments):
            logger.error(f"❌ Argumentos inválidos para {function_name}: {arguments}")
            raise ValueError(f"Argumentos inválidos para función {function_name}")
        
        logger.info(f"✅ Argumentos válidos para {function_name}")
        
        # Mapeo de funciones a handlers
        handler_mapping = {
            "modify_routine_injury": handle_modify_routine_injury,
            "modify_routine_focus": handle_modify_routine_focus,
            "adjust_routine_difficulty": handle_adjust_routine_difficulty,
            "adjust_for_menstrual_cycle": handle_adjust_menstrual_cycle,
            "recalculate_diet_macros": handle_recalculate_macros,
            "substitute_disliked_food": handle_substitute_food,
            "generate_meal_alternatives": handle_generate_alternatives,
            "simplify_diet_plan": handle_simplify_diet,
            "substitute_exercise": handle_substitute_exercise,
            "modify_routine_equipment": handle_modify_routine_equipment,
            "revert_last_modification": handle_revert_modification
        }
        
        handler = handler_mapping.get(function_name)
        if not handler:
            raise ValueError(f"Handler no encontrado para función {function_name}")
        
        # Ejecutar handler con sesión de base de datos
        if function_name == "revert_last_modification":
            result = await handler(user_id, db)
        else:
            # Pasar TODOS los argumentos como keyword arguments para evitar mapeo incorrecto
            # Esto es crítico cuando las funciones tienen parámetros con valores por defecto
            # Añadir db a los argumentos antes de pasarlos
            arguments_with_db = {**arguments, 'db': db}
            result = await handler(user_id=user_id, **arguments_with_db)
        
        return result
        
    except Exception as e:
        logger.error(f"Error ejecutando handler {function_name}: {e}")
        return {
            "success": False,
            "message": f"Error ejecutando {function_name}: {str(e)}",
            "changes": []
        }

@router.post("/api/chat/modify", response_model=ChatResponse)
async def chat_with_modifications(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Endpoint principal para chat con modificaciones dinámicas - VERSIÓN OPTIMIZADA
    """
    try:
        logger.info(f"Procesando chat para usuario {request.user_id}: {request.message[:50]}...")
        
        # ════════════════════════════════════════════════════════════
        # VERIFICAR SI HAY CONFIRMACIÓN PENDIENTE
        # ════════════════════════════════════════════════════════════
        
        if request.user_id in pending_confirmations:
            logger.info(f"🔍 Confirmación pendiente detectada para usuario {request.user_id}")
            pending = pending_confirmations[request.user_id]
            
            # Detectar si eligió opción A o B
            message_lower = request.message.lower()
            
            chosen_option = None
            if any(word in message_lower for word in ["opción a", "opcion a", "a)", "total", "primera", "absoluto"]):
                chosen_option = "A"
            elif any(word in message_lower for word in ["opción b", "opcion b", "b)", "añadir", "anadir", "mas", "más", "incremental", "adicional"]):
                chosen_option = "B"
            
            if chosen_option:
                logger.info(f"✅ Usuario eligió opción {chosen_option}")
                
                # Aplicar la opción elegida
                params = pending["params"].copy()
                option_data = pending["options"][chosen_option]
                
                params["is_incremental"] = option_data["is_incremental"]
                params["calorie_adjustment"] = option_data["calorie_adjustment"]
                
                # Ejecutar el recálculo
                result = await handle_recalculate_macros(request.user_id, **params, db=db)
                
                # Limpiar confirmación pendiente
                del pending_confirmations[request.user_id]
                
                if result.get("success"):
                    return ChatResponse(
                        response=f"✅ Plan actualizado correctamente.\n\n{result.get('summary', '')}",
                        modified=True,
                        changes=result.get("changes", []),
                        function_used="recalculate_diet_macros",
                        success=result.get("success"),
                        plan_updated=result.get("plan_updated"),
                        summary=result.get("summary")
                    )
                else:
                    return ChatResponse(
                        response=f"❌ Error al actualizar: {result.get('message', 'Error desconocido')}",
                        modified=False,
                        changes=[],
                        function_used="recalculate_diet_macros"
                    )
            else:
                # No entendió la respuesta, volver a preguntar
                return ChatResponse(
                    response="No entendí tu respuesta. Por favor responde:\n• 'Opción A' para déficit total\n• 'Opción B' para añadir al déficit actual",
                    modified=False,
                    changes=[],
                    function_used="recalculate_diet_macros"
                )
        
        # 1. Obtener contexto del usuario (optimizado)
        user_context = await get_user_context(request.user_id, db)
        
        # 2. Construir mensajes para OpenAI - LIMITAR HISTORIAL PARA REDUCIR TOKENS
        # Solo enviar últimos 10 mensajes para evitar consumo excesivo de tokens
        limited_history = request.conversation_history[-10:] if request.conversation_history else []
        
        messages = [
            {"role": "system", "content": build_system_prompt(user_context)},
            *limited_history,
            {"role": "user", "content": request.message}
        ]
        
        # Logging de tokens para monitoreo
        estimated_tokens = len(str(messages)) // 4  # Estimación aproximada
        logger.info(f"📊 Mensajes enviados: {len(messages)}, Estimación tokens: ~{estimated_tokens}")
        if estimated_tokens > 5000:
            logger.warning(f"⚠️ ALERTA: Request muy grande! ~{estimated_tokens} tokens estimados")
        
        # 3. Llamar a OpenAI con function calling (optimizado) - CON RETRY LIMITS
        logger.info(f"Llamando a OpenAI para usuario {request.user_id}")
        
        MAX_RETRIES = 1  # No más de 1 retry para evitar loops
        retry_count = 0
        
        while retry_count <= MAX_RETRIES:
            try:
                response = client.chat.completions.create(
                    model=MODEL,  # ✅ Usa modelo dinámico según ambiente
                    messages=messages,
                    tools=[{"type": "function", "function": func} for func in OPENAI_FUNCTIONS],
                    tool_choice="auto",
                    temperature=0.7,
                    max_tokens=1000,
                    timeout=30  # Timeout para evitar cuelgues
                )
                
                # Logging adicional del modelo usado
                logger.info(f"🤖 Modelo usado: {MODEL} (Ambiente: {ENVIRONMENT})")
                
                # Logging de tokens reales usados
                if hasattr(response, 'usage') and response.usage:
                    tokens_used = response.usage.total_tokens
                    logger.info(f"📊 Tokens usados: {tokens_used}")
                    if tokens_used > 5000:
                        logger.warning(f"❌ ALERTA: Request muy grande! {tokens_used} tokens usados")
                    elif tokens_used > 2000:
                        logger.warning(f"⚠️ Request grande: {tokens_used} tokens usados")
                
                break  # Salir del loop si la llamada fue exitosa
                
            except Exception as e:
                retry_count += 1
                if retry_count > MAX_RETRIES:
                    logger.error(f"❌ Error en OpenAI después de {MAX_RETRIES} reintentos: {e}")
                    raise HTTPException(status_code=500, detail=f"Error en OpenAI: {str(e)}")
                else:
                    logger.warning(f"⚠️ Reintentando llamada a OpenAI (intento {retry_count}/{MAX_RETRIES}): {e}")
                    continue
        
        message = response.choices[0].message
        function_used = None
        changes = []
        modified = False
        
        # Log de la respuesta del LLM
        logger.info(f"📝 Contenido de la respuesta: {message.content[:200] if message.content else 'None'}")
        logger.info(f"🔧 Tool calls: {len(message.tool_calls) if message.tool_calls else 0}")
        if message.tool_calls:
            logger.info(f"🔧 Función detectada: {message.tool_calls[0].function.name if message.tool_calls else 'None'}")
        
        # 4. Verificar si hay function call
        if message.tool_calls:
            function_call = message.tool_calls[0]
            function_name = function_call.function.name
            function_used = function_name
            
            try:
                # Parsear argumentos
                arguments = json.loads(function_call.function.arguments)
                
                # Ejecutar handler (optimizado)
                handler_result = await execute_function_handler(
                    function_name, 
                    arguments, 
                    request.user_id,
                    db
                )
                
                changes = handler_result.get("changes", [])
                modified = handler_result.get("success", False)
                
                # Verificar si necesita confirmación
                if handler_result.get("needs_clarification"):
                    logger.info(f"🤔 Handler necesita confirmación para usuario {request.user_id}")
                    
                    # Guardar confirmación pendiente
                    pending_confirmations[request.user_id] = {
                        "params": handler_result.get("pending_params", {}),
                        "options": handler_result.get("options", {})
                    }
                    
                    return ChatResponse(
                        response=handler_result.get("message", "Necesito aclarar tu solicitud."),
                        modified=False,
                        changes=[],
                        function_used=function_name
                    )
                
                # Construir respuesta final
                if handler_result.get("success"):
                    final_messages = messages + [
                        {"role": "assistant", "content": message.content or "", "tool_calls": message.tool_calls},
                        {
                            "role": "tool", 
                            "tool_call_id": function_call.id,
                            "content": json.dumps(handler_result)
                        }
                    ]
                    
                    # Llamar a OpenAI nuevamente para respuesta final (con timeout)
                    final_response = client.chat.completions.create(
                        model=MODEL,  # ✅ Usa modelo dinámico según ambiente
                        messages=final_messages,
                        temperature=0.7,
                        max_tokens=800,
                        timeout=30
                    )
                    
                    # Logging de tokens de la respuesta final
                    if hasattr(final_response, 'usage') and final_response.usage:
                        tokens_used = final_response.usage.total_tokens
                        logger.info(f"📊 Tokens usados (respuesta final): {tokens_used}")
                    
                    final_message = final_response.choices[0].message.content
                    
                    logger.info(f"Modificación exitosa para usuario {request.user_id}: {function_name}")
                    
                    return ChatResponse(
                        response=final_message,
                        modified=modified,
                        changes=changes,
                        function_used=function_used,
                        # Pasar campos adicionales del handler_result
                        success=handler_result.get("success"),
                        plan_updated=handler_result.get("plan_updated"),
                        summary=handler_result.get("summary")
                    )
                else:
                    # Error en la modificación
                    logger.warning(f"Error en modificación para usuario {request.user_id}: {handler_result.get('message', 'Error desconocido')}")
                    
                    return ChatResponse(
                        response=handler_result.get("message", "Lo siento, hubo un problema al procesar tu solicitud."),
                        modified=False,
                        changes=[],
                        function_used=function_used
                    )
                    
            except json.JSONDecodeError as e:
                logger.error(f"Error parseando argumentos JSON: {e}")
                return ChatResponse(
                    response="Lo siento, hubo un problema al procesar tu solicitud.",
                    modified=False,
                    changes=[],
                    function_used=function_used
                )
            except Exception as e:
                logger.error(f"Error ejecutando función {function_name}: {e}")
                return ChatResponse(
                    response=f"Lo siento, hubo un problema al procesar tu solicitud: {str(e)}",
                    modified=False,
                    changes=[],
                    function_used=function_used
                )
        else:
            # No hay function call, respuesta normal
            logger.info(f"Respuesta normal para usuario {request.user_id}")
            
            return ChatResponse(
                response=message.content or "Lo siento, no pude procesar tu solicitud.",
                modified=False,
                changes=[],
                function_used=None
            )
        
    except Exception as e:
        logger.error(f"Error en chat_with_modifications para usuario {request.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )
