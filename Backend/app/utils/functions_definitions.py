#!/usr/bin/env python3
"""
Definiciones de funciones para OpenAI Function Calling
Permite que la IA detecte y ejecute modificaciones dinámicas de rutinas y dietas
"""

from typing import Dict, List, Any

# Definiciones de funciones para OpenAI API
OPENAI_FUNCTIONS: List[Dict[str, Any]] = [
    # ==================== RUTINAS ====================
    
    {
        "name": "modify_routine_injury",
        "description": "Elimina ejercicios que afecten una lesión específica y los sustituye por alternativas seguras",
        "parameters": {
            "type": "object",
            "properties": {
                "body_part": {
                    "type": "string",
                    "description": "Parte del cuerpo lesionada",
                    "enum": ["hombro", "rodilla", "espalda", "cuello", "muñeca", "tobillo", "codo", "cadera", "cuadriceps", "piernas", "muslos", "gemelos", "pantorrillas", "pies", "pecho", "brazos", "antebrazo", "lumbar", "cervical", "dorsal", "core", "abdomen"]
                },
                "injury_type": {
                    "type": "string", 
                    "description": "Tipo de lesión",
                    "enum": ["tendinitis", "esguince", "contractura", "inflamacion", "dolor_cronico", "post_cirugia", "desgarro", "distension", "luxacion", "fractura", "bursitis", "artritis", "dolor_muscular"]
                },
                "severity": {
                    "type": "string",
                    "description": "Severidad de la lesión",
                    "enum": ["mild", "moderate", "severe"]
                }
            },
            "required": ["body_part", "injury_type", "severity"]
        }
    },
    
    {
        "name": "modify_routine_focus",
        "description": "Aumenta volumen y/o frecuencia de entrenamiento en un área específica del cuerpo",
        "parameters": {
            "type": "object",
            "properties": {
                "focus_area": {
                    "type": "string",
                    "description": "Área del cuerpo a enfocar",
                    "enum": ["brazos", "pecho", "espalda", "piernas", "hombros", "core", "gluteos", "pantorrillas"]
                },
                "increase_frequency": {
                    "type": "boolean",
                    "description": "Si aumentar la frecuencia de entrenamiento de esa área"
                },
                "volume_change": {
                    "type": "string",
                    "description": "Cambio en el volumen de entrenamiento",
                    "enum": ["ligero_aumento", "aumento_moderado", "aumento_significativo", "mantener_volumen"]
                }
            },
            "required": ["focus_area", "increase_frequency", "volume_change"]
        }
    },
    
    {
        "name": "adjust_routine_difficulty",
        "description": "Ajusta la dificultad general de la rutina (aumentar o disminuir)",
        "parameters": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "description": "Dirección del cambio de dificultad",
                    "enum": ["increase", "decrease"]
                },
                "reason": {
                    "type": "string",
                    "description": "Razón del cambio de dificultad",
                    "enum": ["usuario_se_siente_cansado", "usuario_quiere_mas_desafio", "progreso_estancado", "tiempo_disponible_cambiado", "motivacion_baja"]
                }
            },
            "required": ["direction", "reason"]
        }
    },
    
    {
        "name": "adjust_for_menstrual_cycle",
        "description": "Adapta la rutina según la fase del ciclo menstrual (solo para mujeres)",
        "parameters": {
            "type": "object",
            "properties": {
                "phase": {
                    "type": "string",
                    "description": "Fase del ciclo menstrual",
                    "enum": ["folicular", "lutea", "menstruacion", "ovulacion"]
                },
                "day_of_cycle": {
                    "type": "integer",
                    "description": "Día del ciclo (1-28)",
                    "minimum": 1,
                    "maximum": 28
                }
            },
            "required": ["phase", "day_of_cycle"]
        }
    },
    
    # ==================== DIETA ====================
    
    {
        "name": "recalculate_diet_macros",
        "description": "Recalcula calorías y macronutrientes del plan dietético basado en cambio de peso o objetivos",
        "parameters": {
            "type": "object",
            "properties": {
                "weight_change_kg": {
                    "type": "number",
                    "description": "Cambio de peso en kilogramos (positivo = ganancia, negativo = pérdida)",
                    "minimum": -10.0,
                    "maximum": 10.0
                },
                "goal": {
                    "type": "string",
                    "description": "Objetivo del usuario",
                    "enum": ["volumen", "definicion", "mantenimiento", "fuerza", "resistencia"]
                }
            },
            "required": ["weight_change_kg", "goal"]
        }
    },
    
    {
        "name": "substitute_disliked_food",
        "description": "Sustituye un alimento que no le gusta al usuario por una alternativa con macros similares",
        "parameters": {
            "type": "object",
            "properties": {
                "disliked_food": {
                    "type": "string",
                    "description": "Alimento que no le gusta al usuario"
                },
                "meal_type": {
                    "type": "string",
                    "description": "Tipo de comida donde aparece el alimento",
                    "enum": ["desayuno", "almuerzo", "cena", "snack", "todos"]
                }
            },
            "required": ["disliked_food", "meal_type"]
        }
    },
    
    {
        "name": "generate_meal_alternatives",
        "description": "Genera opciones alternativas para un tipo de comida específico",
        "parameters": {
            "type": "object",
            "properties": {
                "meal_type": {
                    "type": "string",
                    "description": "Tipo de comida para generar alternativas",
                    "enum": ["desayuno", "almuerzo", "cena", "snack"]
                },
                "num_alternatives": {
                    "type": "integer",
                    "description": "Número de alternativas a generar",
                    "minimum": 2,
                    "maximum": 5
                }
            },
            "required": ["meal_type", "num_alternatives"]
        }
    },
    
    {
        "name": "simplify_diet_plan",
        "description": "Simplifica el plan nutricional reduciendo su complejidad",
        "parameters": {
            "type": "object",
            "properties": {
                "complexity_level": {
                    "type": "string",
                    "description": "Nivel de simplicidad deseado",
                    "enum": ["muy_simple", "simple"]
                }
            },
            "required": ["complexity_level"]
        }
    },
    
    {
        "name": "substitute_exercise",
        "description": "Sustituye un ejercicio específico por otro alternativo cuando al usuario no le gusta o no tiene la máquina",
        "parameters": {
            "type": "object",
            "properties": {
                "exercise_to_replace": {
                    "type": "string",
                    "description": "Nombre del ejercicio que se va a sustituir"
                },
                "replacement_reason": {
                    "type": "string",
                    "description": "Razón por la cual se sustituye el ejercicio",
                    "enum": ["no_gusta", "no_tiene_maquina", "muy_dificil", "muy_facil", "incomodo", "no_disponible", "otro"]
                },
                "target_muscles": {
                    "type": "string",
                    "description": "Grupos musculares que debe trabajar el ejercicio alternativo",
                    "enum": ["pecho", "espalda", "hombros", "brazos", "piernas", "gluteos", "core", "pantorrillas", "todo_cuerpo"]
                },
                "equipment_available": {
                    "type": "string",
                    "description": "Tipo de equipamiento disponible para el ejercicio alternativo",
                    "enum": ["peso_libre", "maquinas", "cuerpo_libre", "bandas", "kettlebell", "cualquiera"]
                }
            },
            "required": ["exercise_to_replace", "replacement_reason", "target_muscles"]
        }
    },
    
    {
        "name": "modify_routine_equipment",
        "description": "Adapta la rutina cuando el usuario no tiene acceso a ciertas máquinas o equipamiento",
        "parameters": {
            "type": "object",
            "properties": {
                "missing_equipment": {
                    "type": "string",
                    "description": "Equipamiento que no está disponible",
                    "enum": ["press_banca", "sentadilla_rack", "pesas_libres", "maquinas", "cables", "poleas", "smith_machine", "rack_multiuso", "barras", "discos", "mancuernas", "kettlebells", "bandas_elasticas", "step", "banco", "colchoneta"]
                },
                "available_equipment": {
                    "type": "string",
                    "description": "Equipamiento disponible para sustituir",
                    "enum": ["peso_libre", "cuerpo_libre", "bandas", "kettlebell", "maquinas_basicas", "cables", "step", "banco", "colchoneta", "cualquiera"]
                },
                "affected_exercises": {
                    "type": "string",
                    "description": "Ejercicios específicos que se ven afectados por la falta de equipamiento"
                }
            },
            "required": ["missing_equipment", "available_equipment"]
        }
    },
    
    # ==================== GENERAL ====================
    
    {
        "name": "revert_last_modification",
        "description": "Deshace la última modificación realizada a la rutina o dieta",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

# Mapeo de nombres de funciones a handlers
FUNCTION_HANDLERS: Dict[str, str] = {
    "modify_routine_injury": "handle_modify_routine_injury",
    "modify_routine_focus": "handle_modify_routine_focus", 
    "adjust_routine_difficulty": "handle_adjust_routine_difficulty",
    "adjust_for_menstrual_cycle": "handle_adjust_menstrual_cycle",
    "recalculate_diet_macros": "handle_recalculate_macros",
    "substitute_disliked_food": "handle_substitute_food",
    "generate_meal_alternatives": "handle_generate_alternatives",
    "simplify_diet_plan": "handle_simplify_diet",
    "substitute_exercise": "handle_substitute_exercise",
    "modify_routine_equipment": "handle_modify_routine_equipment",
    "revert_last_modification": "handle_revert_modification"
}

# Prompts del sistema para cada tipo de función
SYSTEM_PROMPTS = {
    "modify_routine_injury": """
    Eres un experto en rehabilitación deportiva. Cuando el usuario mencione una lesión:
    1. Identifica la parte del cuerpo afectada
    2. Determina el tipo de lesión (tendinitis, esguince, etc.)
    3. Evalúa la severidad basándote en las descripciones del usuario
    4. Sugiere ejercicios alternativos que no comprometan la lesión
    """,
    
    "modify_routine_focus": """
    Eres un entrenador personal especializado en periodización. Cuando el usuario quiera enfocar más un área:
    1. Identifica qué área específica quiere desarrollar
    2. Determina si necesita más frecuencia o más volumen
    3. Mantén el equilibrio con el resto del cuerpo
    4. Explica los cambios y el razonamiento
    """,
    
    "adjust_routine_difficulty": """
    Eres un coach experto en progresión de entrenamientos. Cuando el usuario mencione cansancio o facilidad:
    1. Identifica si necesita más o menos dificultad
    2. Determina la razón del cambio (cansancio, estancamiento, etc.)
    3. Ajusta volumen, intensidad o frecuencia apropiadamente
    4. Mantén la progresión sostenible
    """,
    
    "adjust_for_menstrual_cycle": """
    Eres un especialista en entrenamiento femenino. Cuando una mujer mencione su ciclo:
    1. Identifica la fase del ciclo menstrual
    2. Adapta la intensidad según la fase (menstruación = menor intensidad)
    3. Sugiere ejercicios apropiados para cada fase
    4. Considera los cambios hormonales y energéticos
    """,
    
    "recalculate_diet_macros": """
    Eres un nutricionista deportivo. Cuando el usuario mencione cambios de peso u objetivos:
    1. Identifica el cambio de peso o nuevo objetivo
    2. Recalcula las calorías necesarias
    3. Ajusta macronutrientes (proteínas, carbohidratos, grasas)
    4. Mantén el equilibrio nutricional
    """,
    
    "substitute_disliked_food": """
    Eres un chef nutricionista. Cuando el usuario no quiera un alimento:
    1. Identifica el alimento específico que rechaza
    2. Busca alternativas con macros similares
    3. Considera preferencias de sabor y textura
    4. Mantén el valor nutricional
    """,
    
    "generate_meal_alternatives": """
    Eres un meal planner experto. Cuando el usuario pida alternativas:
    1. Identifica el tipo de comida
    2. Genera opciones variadas y atractivas
    3. Mantén las calorías y macros similares
    4. Considera tiempo de preparación y disponibilidad
    """,
    
    "simplify_diet_plan": """
    Eres un coach de hábitos nutricionales. Cuando el usuario pida simplificar:
    1. Reduce la complejidad de las recetas
    2. Disminuye el número de ingredientes
    3. Facilita la preparación
    4. Mantén el valor nutricional
    """,
    
    "substitute_exercise": """
    Eres un entrenador personal experto en variaciones de ejercicios. Cuando el usuario no le guste un ejercicio o no tenga la máquina:
    1. Identifica el ejercicio específico que quiere cambiar
    2. Determina la razón (no le gusta, no tiene máquina, muy difícil, etc.)
    3. Busca un ejercicio alternativo que trabaje los mismos grupos musculares
    4. Considera el equipamiento disponible
    5. Explica por qué el nuevo ejercicio es una buena alternativa
    """,
    
    "modify_routine_equipment": """
    Eres un especialista en adaptación de rutinas. Cuando el usuario no tenga acceso a ciertas máquinas:
    1. Identifica qué equipamiento específico no está disponible
    2. Determina qué ejercicios se ven afectados
    3. Busca alternativas usando el equipamiento disponible
    4. Mantén la intensidad y grupos musculares trabajados
    5. Proporciona opciones claras y viables
    """,
    
    "revert_last_modification": """
    Eres un asistente de gestión de cambios. Cuando el usuario quiera deshacer:
    1. Identifica la última modificación realizada
    2. Restaura la versión anterior
    3. Explica qué se ha revertido
    4. Ofrece alternativas si es necesario
    """
}

def get_function_by_name(function_name: str) -> Dict[str, Any]:
    """
    Obtiene la definición de una función por su nombre
    
    Args:
        function_name: Nombre de la función
        
    Returns:
        Diccionario con la definición de la función
        
    Raises:
        ValueError: Si la función no existe
    """
    for func in OPENAI_FUNCTIONS:
        if func["name"] == function_name:
            return func
    
    raise ValueError(f"Función '{function_name}' no encontrada")

def get_system_prompt_for_function(function_name: str) -> str:
    """
    Obtiene el prompt del sistema para una función específica
    
    Args:
        function_name: Nombre de la función
        
    Returns:
        Prompt del sistema correspondiente
    """
    return SYSTEM_PROMPTS.get(function_name, "Eres un asistente experto en fitness y nutrición.")

def validate_function_arguments(function_name: str, arguments: Dict[str, Any]) -> bool:
    """
    Valida que los argumentos de una función sean correctos
    
    Args:
        function_name: Nombre de la función
        arguments: Diccionario con los argumentos
        
    Returns:
        True si los argumentos son válidos, False si no
    """
    try:
        function_def = get_function_by_name(function_name)
        required_params = function_def["parameters"].get("required", [])
        properties = function_def["parameters"].get("properties", {})
        
        # Verificar parámetros requeridos
        for param in required_params:
            if param not in arguments:
                return False
        
        # Verificar tipos y valores válidos
        for param_name, param_value in arguments.items():
            if param_name not in properties:
                continue
                
            param_def = properties[param_name]
            param_type = param_def.get("type")
            
            # Verificar tipo
            if param_type == "string" and not isinstance(param_value, str):
                return False
            elif param_type == "integer" and not isinstance(param_value, int):
                return False
            elif param_type == "number" and not isinstance(param_value, (int, float)):
                return False
            elif param_type == "boolean" and not isinstance(param_value, bool):
                return False
            
            # Verificar valores enum
            if "enum" in param_def and param_value not in param_def["enum"]:
                return False
            
            # Verificar rangos
            if "minimum" in param_def and param_value < param_def["minimum"]:
                return False
            if "maximum" in param_def and param_value > param_def["maximum"]:
                return False
        
        return True
        
    except Exception:
        return False
