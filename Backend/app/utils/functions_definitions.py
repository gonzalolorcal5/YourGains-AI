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
        "description": """
        Elimina ejercicios que afecten una lesión específica y los sustituye por alternativas seguras.
        
        DETECCIÓN DE VARIACIONES:
        - "Me duele el hombro" → body_part="hombro", injury_type="dolor_muscular", severity="mild"
        - "Tengo molestias en la rodilla" → body_part="rodilla", injury_type="dolor_muscular", severity="mild"
        - "Me he lesionado el hombro" → body_part="hombro", injury_type="dolor_cronico", severity="moderate"
        - "Me lesioné la espalda" → body_part="espalda", injury_type="dolor_cronico", severity="moderate"
        - "Me duele mucho el hombro" → body_part="hombro", injury_type="dolor_muscular", severity="moderate"
        - "Tengo una tendinitis en el hombro" → body_part="hombro", injury_type="tendinitis", severity="moderate"
        - "No puedo entrenar el hombro porque me duele" → body_part="hombro", injury_type="dolor_muscular", severity="mild"
        
        PALABRAS CLAVE PARA DETECCIÓN:
        - "duele", "dolor", "molestias", "molesta" → Dolor/malestar (severidad: mild)
        - "me lesioné", "me he lesionado", "tengo una lesión", "estoy lesionado" → Lesión (severidad: moderate)
        - "mucho dolor", "duele mucho", "muy doloroso", "dolor intenso" → Dolor intenso (severidad: moderate/severe)
        """,
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
        "description": """
        Recalcula los macros de la dieta cuando:
        - El usuario cambia de peso (subió/bajó kilos)
        - El usuario cambia su objetivo (volumen, definición, mantenimiento)
        - El usuario especifica calorías totales deseadas
        - El usuario especifica ajuste calórico personalizado
        
        🔥 DETECCIÓN DE CAMBIO DE PESO (CRÍTICO):
        - "Subí 2kg" / "He subido 2kg" / "Aumenté 2kg" → weight_change_kg=2
        - "Bajé 3kg" / "He bajado 3kg" / "Adelgacé 3kg" / "He adelgazado 3kg" → weight_change_kg=-3
        - "Perdí 4kg" / "He perdido 4kg" / "Perdí peso" → weight_change_kg=-4
        - "Engordé 2kg" / "He engordado 2kg" → weight_change_kg=2
        - "Gané 5kg" / "He ganado 5kg" → weight_change_kg=5
        
        ⚠️ IMPORTANTE: Cuando el usuario mencione OBJETIVO + CALORÍAS en el mismo mensaje, 
        debes extraer AMBOS parámetros:
        - "Quiero hacer definición de 500 kcal" → goal="definicion", calorie_adjustment=-500, is_incremental=false
        - "Quiero volumen con 3800 kcal" → goal="volumen", target_calories=3800
        - "Cambiar a mantenimiento con 3000 kcal" → goal="mantenimiento", target_calories=3000
        
        🎯 DETECCIÓN DE OBJETIVOS SIMPLES (CRÍTICO):
        - "Quiero hacer mantenimiento" → goal="mantenimiento"
        - "Quiero mantenimiento" → goal="mantenimiento"
        - "Mantenimiento" → goal="mantenimiento"
        - "Quiero hacer definición" → goal="definicion"
        - "Quiero hacer volumen" → goal="volumen"
        
        DETECCIÓN DE AJUSTES CALÓRICOS:
        🔍 ABSOLUTO (establecer déficit/superávit total):
        - "Quiero un déficit de 500 kcal" → calorie_adjustment=-500, is_incremental=false
        - "Cambiar a superávit de 300 kcal" → calorie_adjustment=300, is_incremental=false
        - "Definición de 400 kcal" → goal="definicion", calorie_adjustment=-400, is_incremental=false
        - "Quiero que el volumen sea de 200 kcal" → goal="volumen", calorie_adjustment=200, is_incremental=false
        - "Quiero que la definición sea de 500 kcal" → goal="definicion", calorie_adjustment=-500, is_incremental=false
        - "Quiero que el superávit sea de 200 kcal" → calorie_adjustment=200, is_incremental=false
        - "Quiero que el déficit sea de 400 kcal" → calorie_adjustment=-400, is_incremental=false
        
        🔍 INCREMENTAL (añadir al déficit/superávit actual):
        - "Añade 100 kcal más al déficit" → calorie_adjustment=-100, is_incremental=true
        - "Incrementa el superávit 50 kcal" → calorie_adjustment=50, is_incremental=true
        - "Reduce 200 kcal adicionales" → calorie_adjustment=-200, is_incremental=true
        - "Aumenta el superávit en 200 kcal más" → calorie_adjustment=200, is_incremental=true
        - "Sube el déficit en 100 kcal más" → calorie_adjustment=-100, is_incremental=true
        
        ⚠️ AMBIGUO (pedir confirmación):
        - "Aumenta el déficit a 500 kcal" → calorie_adjustment=-500, is_incremental=null
        - "Aumenta el superávit a 200 kcal" → calorie_adjustment=200, is_incremental=null
        - "Sube el superávit a 400" → calorie_adjustment=400, is_incremental=null
        - "Cambia el déficit a 600" → calorie_adjustment=-600, is_incremental=null
        REGLA CLARA: si la frase usa la preposición "a" ("a X kcal") con verbos
        como aumentar/subir/incrementar, TRÁTALO COMO AMBIGUO (is_incremental=null).
        Solo marca incremental cuando diga explícitamente "en X", "+X", "más X" o
        "añade X". Marca absoluto cuando diga "de X", "sea de X" o "quiero un déficit/superávit de X".
        
        Ejemplos completos:
        - "Subí 2kg" → weight_change_kg=2, goal=null
        - "He adelgazado 3kg" / "Bajé 3kg" / "Perdí 3kg" → weight_change_kg=-3, goal=null
        - "Quiero hacer volumen" → goal="volumen"
        - "Quiero hacer volumen de 500 kcal" → goal="volumen", calorie_adjustment=500, is_incremental=false
        - "Quiero que el volumen sea de 200 kcal" → goal="volumen", calorie_adjustment=200, is_incremental=false
        - "Quiero un déficit de 400 calorías" → calorie_adjustment=-400, is_incremental=false
        - "Añade 100 kcal más al déficit" → calorie_adjustment=-100, is_incremental=true
        - "Aumenta el déficit a 500 kcal" → calorie_adjustment=-500, is_incremental=null
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "weight_change_kg": {
                    "type": ["number", "null"],
                    "description": "Cambio de peso en kg (positivo = subió, negativo = bajó)",
                    "minimum": -10.0,
                    "maximum": 10.0
                },
                "goal": {
                    "type": ["string", "null"],
                    "enum": ["volumen", "definicion", "mantenimiento", "fuerza", "resistencia"],
                    "description": """
                    Nuevo objetivo nutricional del usuario. 
                    
                    DETECCIÓN CRÍTICA:
                    - Si el usuario dice "definición", "definicion", "hacer definición", "hacer definicion", 
                      "quiero definición", "quiero definicion" → devolver "definicion"
                    - Si el usuario dice "volumen", "hacer volumen", "quiero volumen", "bulking" → devolver "volumen"
                    - Si el usuario dice "mantenimiento", "mantener peso" → devolver "mantenimiento"
                    
                    Valores permitidos: "definicion", "volumen", "mantenimiento", "fuerza", "resistencia"
                    """
                },
                "target_calories": {
                    "type": ["integer", "null"],
                    "description": "Calorías totales objetivo especificadas por el usuario (ej: 3500, 2800)"
                },
                "calorie_adjustment": {
                    "type": ["integer", "null"],
                    "description": "Ajuste calórico en kcal (negativo para déficit, positivo para superávit)"
                },
                "is_incremental": {
                    "type": ["boolean", "null"],
                    "description": "true=añadir al ajuste actual, false=reemplazar total, null=ambiguo (pedir confirmación)"
                },
                "adjustment_type": {
                    "type": ["string", "null"],
                    "enum": ["deficit", "surplus"],
                    "description": "Tipo de ajuste calórico"
                }
            },
            "required": []
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
    Eres un nutricionista deportivo experto. Cuando el usuario mencione cambios de peso, objetivos o calorías:
    1. Identifica el cambio de peso, nuevo objetivo, calorías específicas o ajuste personalizado
    2. ⚠️ CRÍTICO: Si el usuario menciona OBJETIVO + CALORÍAS en el mismo mensaje, extrae AMBOS parámetros
    3. ⚠️ CRÍTICO: "Quiero que el volumen sea de X kcal" → goal="volumen", calorie_adjustment=X, is_incremental=false
    4. ⚠️ CRÍTICO: "Quiero que la definición sea de X kcal" → goal="definicion", calorie_adjustment=-X, is_incremental=false
    5. ⚠️ CRÍTICO: "Quiero que el superávit sea de X kcal" → calorie_adjustment=X, is_incremental=false
    6. ⚠️ CRÍTICO: "Quiero que el déficit sea de X kcal" → calorie_adjustment=-X, is_incremental=false
    7. Prioriza: calorías totales > ajuste personalizado > cálculo automático
    8. Recalcula las calorías necesarias según la prioridad
    9. Ajusta macronutrientes (proteínas, carbohidratos, grasas) proporcionalmente
    10. Mantén el equilibrio nutricional y valida rangos saludables (1200-5000 kcal)
    
    🎯 DETECCIÓN DE OBJETIVOS (CRÍTICO):
    - "Quiero hacer mantenimiento" → goal="mantenimiento"
    - "Quiero una dieta de mantenimiento" → goal="mantenimiento"
    - "Cambiar a mantenimiento" → goal="mantenimiento"
    - "Quiero mantenimiento" → goal="mantenimiento"
    - "Mantenimiento" → goal="mantenimiento"
    - "Quiero hacer definición" → goal="definicion"
    - "Quiero hacer volumen" → goal="volumen"
    - "Quiero definición" → goal="definicion"
    - "Quiero volumen" → goal="volumen"
    
    Ejemplos de detección CRÍTICOS:
    - "Quiero hacer definición de 500 kcal" → goal="definicion", calorie_adjustment=-500, is_incremental=false
    - "Quiero hacer volumen de 500 kcal" → goal="volumen", calorie_adjustment=500, is_incremental=false
    - "Quiero que el volumen sea de 200 kcal" → goal="volumen", calorie_adjustment=200, is_incremental=false
    - "Quiero que la definición sea de 400 kcal" → goal="definicion", calorie_adjustment=-400, is_incremental=false
    - "Quiero volumen con 3800 kcal" → goal="volumen", target_calories=3800
    - "Cambiar a mantenimiento con 3000 kcal" → goal="mantenimiento", target_calories=3000
    - "Quiero volumen pero solo +150 kcal" → goal="volumen", calorie_adjustment=150, is_incremental=false
    - "Quiero que el superávit sea de 200 kcal" → calorie_adjustment=200, is_incremental=false
    - "Quiero que el déficit sea de 400 kcal" → calorie_adjustment=-400, is_incremental=false
    
    Ejemplos simples:
    - "Quiero 3500 calorías" → target_calories=3500
    - "Súbeme 200 calorías" → calorie_adjustment=200, is_incremental=true
    - "Subí 2kg" → weight_change_kg=2
    - "Quiero hacer definición" → goal="definicion"
    - "Quiero hacer mantenimiento" → goal="mantenimiento"
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
