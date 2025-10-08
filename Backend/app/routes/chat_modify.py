#!/usr/bin/env python3
"""
Endpoint para chat con modificaciones dinámicas usando OpenAI Function Calling
Permite que la IA detecte y ejecute cambios en rutinas y dietas
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
    handle_modify_routine_injury,
    handle_modify_routine_focus,
    handle_adjust_routine_difficulty,
    handle_adjust_menstrual_cycle,
    handle_recalculate_macros,
    handle_substitute_food,
    handle_generate_alternatives,
    handle_simplify_diet,
    handle_revert_modification
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Configurar OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

async def get_user_context(user_id: int, db: Session) -> Dict[str, Any]:
    """
    Obtiene el contexto completo del usuario para el chat
    
    Args:
        user_id: ID del usuario
        db: Sesión de base de datos
        
    Returns:
        Diccionario con contexto del usuario
    """
    try:
        logger.info(f"Obteniendo contexto para usuario {user_id}")
        
        # Obtener datos del usuario usando SQLAlchemy
        from app.models import Usuario
        user = db.query(Usuario).filter(Usuario.id == user_id).first()
        
        if not user:
            logger.error(f"Usuario {user_id} no encontrado")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        logger.info(f"Usuario encontrado: {user.email}")
        
        # Deserializar datos JSON
        from app.utils.json_helpers import deserialize_json
        
        context = {
            "user_id": user.id,
            "email": user.email,
            "sexo": "hombre",  # Valor por defecto
            "current_routine": deserialize_json(user.current_routine or "{}", "current_routine"),
            "current_diet": deserialize_json(user.current_diet or "{}", "current_diet"),
            "injuries": deserialize_json(user.injuries or "[]", "injuries"),
            "focus_areas": deserialize_json(user.focus_areas or "[]", "focus_areas"),
            "disliked_foods": deserialize_json(user.disliked_foods or "[]", "disliked_foods"),
            "modification_history": deserialize_json(user.modification_history or "[]", "modification_history")
        }
        
        logger.info(f"Contexto construido exitosamente para usuario {user_id}")
        return context
        
    except HTTPException:
        # Re-lanzar HTTPExceptions
        raise
    except Exception as e:
        logger.error(f"Error obteniendo contexto del usuario {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo datos del usuario: {str(e)}"
        )

def build_system_prompt(user_context: Dict[str, Any]) -> str:
    """
    Construye el prompt del sistema con el contexto completo del usuario
    
    Args:
        user_context: Contexto del usuario
        
    Returns:
        Prompt del sistema
    """
    # Obtener objetivo actual de la dieta
    current_diet = user_context.get('current_diet', {})
    current_goal = current_diet.get('objetivo', 'mantenimiento')
    
    system_prompt = f"""
    Eres un entrenador personal de IA especializado en modificaciones dinámicas de rutinas y dietas.
    
    CONTEXTO DEL USUARIO:
    - Sexo: {user_context.get('sexo', 'No especificado')}
    - Rutina actual: {len(user_context.get('current_routine', {}).get('dias', []))} días de entrenamiento
    - Dieta actual: {len(user_context.get('current_diet', {}).get('comidas', []))} comidas, {user_context.get('current_diet', {}).get('calorias_totales', 0)} kcal
    - Objetivo actual: {current_goal}
    - Lesiones activas: {len(user_context.get('injuries', []))}
    - Áreas de enfoque: {user_context.get('focus_areas', [])}
    - Alimentos no deseados: {user_context.get('disliked_foods', [])}
    - Modificaciones previas: {len(user_context.get('modification_history', []))}
    
    CAPACIDADES:
    Puedes modificar rutinas y dietas dinámicamente usando las siguientes funciones:
    
    RUTINAS:
    - modify_routine_injury: Adaptar rutina por lesiones
    - modify_routine_focus: Enfocar más un área específica
    - adjust_routine_difficulty: Ajustar dificultad general
    - adjust_for_menstrual_cycle: Adaptar al ciclo menstrual (mujeres)
    
    DIETA:
    - recalculate_diet_macros: Recalcular calorías/macros
    - substitute_disliked_food: Sustituir alimentos no deseados
    - generate_meal_alternatives: Generar alternativas de comidas
    - simplify_diet_plan: Simplificar plan nutricional
    
    GENERAL:
    - revert_last_modification: Deshacer última modificación
    
    DETECCIÓN AUTOMÁTICA DE CAMBIOS:
    
    🔥 CAMBIOS DE PESO - SIEMPRE llama a recalculate_diet_macros:
    - "Subí 2kg" → recalculate_diet_macros(weight_change_kg=2.0, goal="{current_goal}")
    - "Bajé 3kg" → recalculate_diet_macros(weight_change_kg=-3.0, goal="{current_goal}")
    - "He ganado 1 kilo" → recalculate_diet_macros(weight_change_kg=1.0, goal="{current_goal}")
    - "Perdí 2 kilos" → recalculate_diet_macros(weight_change_kg=-2.0, goal="{current_goal}")
    - "Mi peso subió a 78kg desde 75kg" → recalculate_diet_macros(weight_change_kg=3.0, goal="{current_goal}")
    - "Engordé 1.5kg" → recalculate_diet_macros(weight_change_kg=1.5, goal="{current_goal}")
    - "Adelgacé 2.5 kilos" → recalculate_diet_macros(weight_change_kg=-2.5, goal="{current_goal}")
    
    🎯 CAMBIOS DE OBJETIVO - SIEMPRE llama a recalculate_diet_macros:
    - "Quiero ganar fuerza" → recalculate_diet_macros(weight_change_kg=0.0, goal="fuerza")
    - "Quiero más hipertrofia" → recalculate_diet_macros(weight_change_kg=0.0, goal="volumen")
    - "Quiero definir" → recalculate_diet_macros(weight_change_kg=0.0, goal="definicion")
    - "Quiero mantener peso" → recalculate_diet_macros(weight_change_kg=0.0, goal="mantenimiento")
    - "Cambié mi objetivo a fuerza" → recalculate_diet_macros(weight_change_kg=0.0, goal="fuerza")
    - "Ahora busco volumen" → recalculate_diet_macros(weight_change_kg=0.0, goal="volumen")
    
    💪 AJUSTES DE RUTINA - SIEMPRE llama a adjust_routine_difficulty:
    - "La rutina es muy fácil" → adjust_routine_difficulty(difficulty_change="increase", reason="muy facil")
    - "Quiero más intensidad" → adjust_routine_difficulty(difficulty_change="increase", reason="mas intensidad")
    - "Es demasiado difícil" → adjust_routine_difficulty(difficulty_change="decrease", reason="muy dificil")
    - "Necesito menos peso" → adjust_routine_difficulty(difficulty_change="decrease", reason="menos peso")
    
    🎯 ENFOQUE EN ÁREAS - SIEMPRE llama a modify_routine_focus:
    - "Quiero enfocar más los brazos" → modify_routine_focus(focus_area="brazos", intensity="medium")
    - "Más trabajo de pecho" → modify_routine_focus(focus_area="pecho", intensity="high")
    - "Enfócate en mis piernas" → modify_routine_focus(focus_area="piernas", intensity="high")
    - "Más glúteos" → modify_routine_focus(focus_area="gluteos", intensity="medium")
    
    INSTRUCCIONES CRÍTICAS:
    1. 🔥 CAMBIOS DE PESO: Si menciona cambio de peso (subí/bajé/gané/perdí X kg), SIEMPRE llama a recalculate_diet_macros
    2. 🎯 CAMBIOS DE OBJETIVO: Si cambia objetivo (fuerza/volumen/definición), SIEMPRE llama a recalculate_diet_macros
    3. 💪 AJUSTES DE RUTINA: Si menciona dificultad (fácil/difícil), llama a adjust_routine_difficulty
    4. 🎯 ENFOQUE EN ÁREAS: Si quiere enfocar más un músculo, llama a modify_routine_focus
    5. 🏥 LESIONES: Si menciona dolor/lesión, llama a modify_routine_injury
    6. 🍎 ALIMENTOS: Si rechaza un alimento, llama a substitute_disliked_food
    7. 📝 EXPLICACIÓN: Explica claramente qué cambios se realizaron y por qué
    8. ❤️ EMPATÍA: Sé empático y profesional en tus respuestas
    
    PALABRAS CLAVE PARA DETECCIÓN:
    🔥 Peso: "subí", "bajé", "gané", "perdí", "engordé", "adelgacé", "kg", "kilo", "kilos", "peso"
    🎯 Objetivo: "fuerza", "hipertrofia", "volumen", "definir", "definición", "mantener", "objetivo"
    💪 Dificultad: "fácil", "difícil", "intensidad", "peso", "demasiado", "necesito", "rutina"
    🎯 Enfoque: "enfocar", "más", "brazos", "pecho", "piernas", "glúteos", "espalda", "hombros"
    🏥 Lesiones: "duele", "dolor", "lesión", "lesionado", "molesta", "hombro", "rodilla", "espalda"
    🍎 Alimentos: "no me gusta", "odio", "no quiero", "sustituir", "cambiar", "comida"
    
    🚨 IMPORTANTE: Usa las funciones automáticamente cuando detectes estas situaciones. 
    Sé proactivo en detectar cambios y aplicar las modificaciones correspondientes.
    """
    
    return system_prompt

async def execute_function_handler(
    function_name: str, 
    arguments: Dict[str, Any], 
    user_id: int,
    db: Session
) -> Dict[str, Any]:
    """
    Ejecuta el handler correspondiente a una función
    
    Args:
        function_name: Nombre de la función
        arguments: Argumentos de la función
        user_id: ID del usuario
        
    Returns:
        Resultado de la ejecución
    """
    try:
        # Validar argumentos
        if not validate_function_arguments(function_name, arguments):
            raise ValueError(f"Argumentos inválidos para función {function_name}")
        
        # Mapear función a handler
        handler_mapping = {
            "modify_routine_injury": handle_modify_routine_injury,
            "modify_routine_focus": handle_modify_routine_focus,
            "adjust_routine_difficulty": handle_adjust_routine_difficulty,
            "adjust_for_menstrual_cycle": handle_adjust_menstrual_cycle,
            "recalculate_diet_macros": handle_recalculate_macros,
            "substitute_disliked_food": handle_substitute_food,
            "generate_meal_alternatives": handle_generate_alternatives,
            "simplify_diet_plan": handle_simplify_diet,
            "revert_last_modification": handle_revert_modification
        }
        
        handler = handler_mapping.get(function_name)
        if not handler:
            raise ValueError(f"Handler no encontrado para función {function_name}")
        
        # Ejecutar handler
        if function_name == "revert_last_modification":
            result = await handler(user_id, db)
        else:
            # Extraer argumentos específicos
            handler_args = [user_id] + [arguments.get(arg) for arg in arguments.keys()] + [db]
            result = await handler(*handler_args)
        
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
    Endpoint principal para chat con modificaciones dinámicas
    """
    try:
        # 1. Obtener contexto del usuario
        user_context = await get_user_context(request.user_id, db)
        
        # 2. Construir mensajes para OpenAI
        messages = [
            {"role": "system", "content": build_system_prompt(user_context)},
            *request.conversation_history,
            {"role": "user", "content": request.message}
        ]
        
        # 3. Llamar a OpenAI con function calling
        logger.info(f"Llamando a OpenAI para usuario {request.user_id}")
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            tools=[{"type": "function", "function": func} for func in OPENAI_FUNCTIONS],
            tool_choice="auto",
            temperature=0.7,
            max_tokens=1000
        )
        
        message = response.choices[0].message
        function_used = None
        changes = []
        modified = False
        
        # 4. Verificar si hay function call
        if message.tool_calls:
            function_call = message.tool_calls[0]
            function_name = function_call.function.name
            function_used = function_name
            
            try:
                # Parsear argumentos
                arguments = json.loads(function_call.function.arguments)
                
                # Ejecutar handler
                handler_result = await execute_function_handler(
                    function_name, 
                    arguments, 
                    request.user_id,
                    db
                )
                
                changes = handler_result.get("changes", [])
                modified = handler_result.get("success", False)
                
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
                    
                    # Llamar a OpenAI nuevamente para respuesta final
                    final_response = client.chat.completions.create(
                        model="gpt-4",
                        messages=final_messages,
                        temperature=0.7,
                        max_tokens=800
                    )
                    
                    final_message = final_response.choices[0].message.content
                    
                    return ChatResponse(
                        response=final_message,
                        modified=modified,
                        changes=changes,
                        function_used=function_used
                    )
                else:
                    # Error en la función
                    return ChatResponse(
                        response=f"Lo siento, hubo un problema al procesar tu solicitud: {handler_result.get('message', 'Error desconocido')}",
                        modified=False,
                        changes=[],
                        function_used=function_used
                    )
                    
            except Exception as e:
                logger.error(f"Error procesando function call {function_name}: {e}")
                return ChatResponse(
                    response=f"Lo siento, hubo un error al procesar tu solicitud: {str(e)}",
                    modified=False,
                    changes=[],
                    function_used=function_used
                )
        
        else:
            # Respuesta normal sin function call
            return ChatResponse(
                response=message.content,
                modified=False,
                changes=[],
                function_used=None
            )
    
    except Exception as e:
        error_str = str(e).lower()
        if "rate_limit" in error_str:
            logger.error("Rate limit de OpenAI excedido")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Límite de requests excedido. Intenta nuevamente en unos minutos."
            )
        elif "timeout" in error_str:
            logger.error("Timeout en OpenAI API")
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="Timeout en el servidor. Intenta nuevamente."
            )
        else:
            logger.error(f"Error en chat_with_modifications: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error interno del servidor: {str(e)}"
            )

@router.get("/api/chat/modify/functions")
async def get_available_functions():
    """
    Endpoint para obtener las funciones disponibles
    """
    try:
        return {
            "functions": OPENAI_FUNCTIONS,
            "total": len(OPENAI_FUNCTIONS),
            "categories": {
                "rutinas": 4,
                "dieta": 4,
                "general": 1
            }
        }
    except Exception as e:
        logger.error(f"Error obteniendo funciones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo funciones disponibles"
        )

@router.get("/api/chat/modify/status/{user_id}")
async def get_user_modification_status(user_id: int, db: Session = Depends(get_db)):
    """
    Endpoint para obtener el estado de modificaciones del usuario
    """
    try:
        user_context = await get_user_context(user_id, db)
        
        return {
            "user_id": user_id,
            "current_routine_version": user_context.get("current_routine", {}).get("version", "1.0.0"),
            "total_modifications": len(user_context.get("modification_history", [])),
            "active_injuries": len(user_context.get("injuries", [])),
            "focus_areas": user_context.get("focus_areas", []),
            "disliked_foods": user_context.get("disliked_foods", []),
            "last_modification": user_context.get("modification_history", [])[-1] if user_context.get("modification_history") else None
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo estado del usuario {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo estado de modificaciones"
        )
