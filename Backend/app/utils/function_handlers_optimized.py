#!/usr/bin/env python3
"""
Handlers optimizados para funciones de OpenAI
Versión senior con manejo eficiente de base de datos y mejor rendimiento
"""

import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.utils.database_service import db_service
from app.utils.json_helpers import serialize_json

logger = logging.getLogger(__name__)

class FunctionHandlerError(Exception):
    """Excepción personalizada para errores en handlers"""
    pass

# ==================== FUNCIONES AUXILIARES OPTIMIZADAS ====================

def increment_routine_version(current_version: str) -> str:
    """Incrementa la versión de la rutina de manera inteligente"""
    try:
        if not current_version or current_version == "1.0.0":
            return "1.1.0"
        
        parts = current_version.split(".")
        if len(parts) >= 2:
            minor = int(parts[1]) + 1
            return f"{parts[0]}.{minor}.0"
        return "1.1.0"
    except:
        return "1.1.0"

def increment_diet_version(current_version: str) -> str:
    """Incrementa la versión de la dieta de manera inteligente"""
    return increment_routine_version(current_version)

def add_injury(injuries: List[Dict], body_part: str, severity: str, description: str) -> List[Dict]:
    """Añade una lesión al historial de manera eficiente"""
    new_injury = {
        "id": len(injuries) + 1,
        "body_part": body_part,
        "severity": severity,
        "description": description,
        "timestamp": datetime.utcnow().isoformat(),
        "active": True
    }
    
    # Mantener solo lesiones activas recientes
    active_injuries = [inj for inj in injuries if inj.get("active", False)]
    active_injuries.append(new_injury)
    
    # Máximo 10 lesiones activas
    return active_injuries[-10:]

# ==================== HANDLERS OPTIMIZADOS ====================

async def handle_modify_routine_injury(
    user_id: int, 
    body_part: str, 
    injury_type: str, 
    severity: str,
    db: Session
) -> Dict[str, Any]:
    """
    Modifica la rutina para adaptarla a una lesión específica - VERSIÓN OPTIMIZADA
    """
    try:
        # Obtener datos del usuario en UNA sola consulta
        user_data = await db_service.get_user_complete_data(user_id, db)
        current_routine = user_data["current_routine"]
        
        # Validar estructura de rutina
        if not isinstance(current_routine, dict) or "exercises" not in current_routine:
            return {
                "success": False,
                "message": "Estructura de rutina inválida. No se puede modificar.",
                "changes": []
            }
        
        # Crear snapshot antes de modificar
        previous_routine = json.loads(json.dumps(current_routine))
        
        changes = []
        
        # Diccionarios optimizados de ejercicios
        exercises_to_remove = {
            "hombro": ["Press banca", "Press militar", "Remo al cuello", "Elevaciones laterales", "Fondos"],
            "rodilla": ["Sentadilla profunda", "Zancadas", "Sentadillas", "Prensa", "Salto"],
            "espalda": ["Peso muerto", "Remo con barra", "Pull ups", "Extensión lumbar"],
            "cuello": ["Press militar", "Elevaciones frontales", "Encogimientos"],
            "muñeca": ["Flexiones", "Press banca", "Curl de bíceps", "Fondos"],
            "tobillo": ["Sentadillas", "Zancadas", "Prensa", "Salto"],
            "codo": ["Curl de bíceps", "Press francés", "Fondos", "Flexiones"],
            "cadera": ["Sentadillas", "Prensa", "Peso muerto", "Zancadas"],
            "cuadriceps": ["Sentadillas", "Zancadas", "Prensa", "Sentadilla profunda", "Salto", "Extensiones de cuádriceps", "Hack squat", "Sissy squat"],
            "piernas": ["Sentadillas", "Zancadas", "Prensa", "Sentadilla profunda", "Salto", "Extensiones de cuádriceps", "Hack squat", "Sissy squat", "Peso muerto"],
            "muslos": ["Sentadillas", "Zancadas", "Prensa", "Sentadilla profunda", "Salto", "Extensiones de cuádriceps", "Hack squat", "Sissy squat"]
        }
        
        safe_alternatives = {
            "hombro": [
                {"nombre": "Press banca agarre cerrado", "series": 4, "reps": "8-10", "descanso": 90},
                {"nombre": "Elevaciones laterales ligeras", "series": 3, "reps": "12-15", "descanso": 60},
                {"nombre": "Facepulls", "series": 3, "reps": "15-20", "descanso": 60}
            ],
            "rodilla": [
                {"nombre": "Leg press", "series": 4, "reps": "12-15", "descanso": 90},
                {"nombre": "Extensiones de cuádriceps", "series": 3, "reps": "12-15", "descanso": 60},
                {"nombre": "Curl femoral", "series": 3, "reps": "12-15", "descanso": 60}
            ],
            "espalda": [
                {"nombre": "Remo con mancuernas", "series": 4, "reps": "8-10", "descanso": 90},
                {"nombre": "Lat pulldown", "series": 3, "reps": "10-12", "descanso": 90},
                {"nombre": "Facepulls", "series": 3, "reps": "15-20", "descanso": 60}
            ],
            "cuello": [
                {"nombre": "Movimientos de cuello", "series": 3, "reps": "10", "descanso": 30},
                {"nombre": "Estiramientos cervicales", "series": 2, "reps": "30s", "descanso": 60}
            ],
            "muñeca": [
                {"nombre": "Curl con barra EZ", "series": 3, "reps": "12-15", "descanso": 60},
                {"nombre": "Press con mancuernas", "series": 3, "reps": "10-12", "descanso": 90}
            ],
            "tobillo": [
                {"nombre": "Elevaciones de talón", "series": 3, "reps": "15-20", "descanso": 60},
                {"nombre": "Flexiones de tobillo", "series": 3, "reps": "15", "descanso": 45}
            ],
            "codo": [
                {"nombre": "Curl martillo", "series": 3, "reps": "12-15", "descanso": 60},
                {"nombre": "Press con mancuernas", "series": 3, "reps": "10-12", "descanso": 90}
            ],
            "cadera": [
                {"nombre": "Puente de glúteos", "series": 3, "reps": "15-20", "descanso": 60},
                {"nombre": "Clamshells", "series": 3, "reps": "15", "descanso": 45}
            ],
            "cuadriceps": [
                {"nombre": "Leg press", "series": 4, "reps": "12-15", "descanso": 90},
                {"nombre": "Curl femoral", "series": 3, "reps": "12-15", "descanso": 60},
                {"nombre": "Puente de glúteos", "series": 3, "reps": "15-20", "descanso": 60},
                {"nombre": "Estocadas estáticas", "series": 3, "reps": "10-12", "descanso": 60}
            ],
            "piernas": [
                {"nombre": "Leg press", "series": 4, "reps": "12-15", "descanso": 90},
                {"nombre": "Curl femoral", "series": 3, "reps": "12-15", "descanso": 60},
                {"nombre": "Puente de glúteos", "series": 3, "reps": "15-20", "descanso": 60},
                {"nombre": "Elevaciones de talón", "series": 3, "reps": "15-20", "descanso": 60}
            ],
            "muslos": [
                {"nombre": "Leg press", "series": 4, "reps": "12-15", "descanso": 90},
                {"nombre": "Curl femoral", "series": 3, "reps": "12-15", "descanso": 60},
                {"nombre": "Puente de glúteos", "series": 3, "reps": "15-20", "descanso": 60}
            ]
        }
        
        exercises_to_remove_list = exercises_to_remove.get(body_part, [])
        alternatives = safe_alternatives.get(body_part, [])
        
        # Procesar ejercicios de manera eficiente
        ejercicios_actuales = current_routine.get("exercises", [])
        ejercicios_filtrados = []
        ejercicios_eliminados = []
        
        # Filtrar ejercicios problemáticos
        for ejercicio in ejercicios_actuales:
            nombre_ejercicio = ejercicio.get("name", "") if isinstance(ejercicio, dict) else str(ejercicio)
            should_remove = any(avoid.lower() in nombre_ejercicio.lower() for avoid in exercises_to_remove_list)
            
            if should_remove:
                ejercicios_eliminados.append(nombre_ejercicio)
                changes.append(f"Eliminado: {nombre_ejercicio}")
            else:
                ejercicios_filtrados.append(ejercicio)
        
        # Añadir alternativas si se eliminaron ejercicios
        if ejercicios_eliminados and alternatives:
            for alt in alternatives[:3]:
                ejercicios_filtrados.append({
                    "name": alt["nombre"],
                    "sets": alt["series"],
                    "reps": alt["reps"],
                    "weight": "peso moderado",
                    "notes": f"Alternativa segura para {body_part}"
                })
                changes.append(f"Añadido: {alt['nombre']}")
        
        # Actualizar la rutina
        current_routine["exercises"] = ejercicios_filtrados
        current_routine["version"] = increment_routine_version(current_routine.get("version", "1.0.0"))
        current_routine["updated_at"] = datetime.utcnow().isoformat()
        
        # Actualizar lesiones
        updated_injuries = add_injury(user_data["injuries"], body_part, severity, f"Lesión de {injury_type}")
        
        # Guardar cambios en UNA sola transacción
        await db_service.update_user_data(user_id, {
            "current_routine": current_routine,
            "injuries": updated_injuries
        }, db)
        
        # Añadir registro de modificación
        await db_service.add_modification_record(
            user_id,
            "routine_injury_modification",
            {
                "body_part": body_part,
                "injury_type": injury_type,
                "severity": severity,
                "previous_routine": previous_routine,
                "changes": changes
            },
            f"Adaptación por lesión de {body_part}",
            db
        )
        
        return {
            "success": True,
            "message": f"Rutina adaptada para lesión de {body_part} ({injury_type}, {severity})",
            "changes": changes
        }
        
    except Exception as e:
        logger.error(f"Error en handle_modify_routine_injury: {e}")
        return {
            "success": False,
            "message": f"Error adaptando rutina para lesión: {str(e)}",
            "changes": []
        }

async def handle_recalculate_macros(
    user_id: int,
    weight_change_kg: float,
    goal: str,
    db: Session
) -> Dict[str, Any]:
    """
    Recalcula los macronutrientes de la dieta - VERSIÓN OPTIMIZADA
    """
    try:
        # Obtener datos del usuario en UNA sola consulta
        user_data = await db_service.get_user_complete_data(user_id, db)
        current_diet = user_data["current_diet"]
        
        # Validar estructura de dieta
        if not isinstance(current_diet, dict) or "meals" not in current_diet:
            return {
                "success": False,
                "message": "Estructura de dieta inválida. No se puede modificar.",
                "changes": []
            }
        
        # Crear snapshot antes de modificar
        previous_diet = json.loads(json.dumps(current_diet))
        
        changes = []
        
        # Obtener calorías actuales
        current_calories = current_diet.get("total_kcal", 2000)
        original_calories = current_calories
        
        # Calcular nuevo objetivo de calorías de manera eficiente
        calorie_adjustments = {
            "volumen": 250 if weight_change_kg > 0 else 0,
            "definicion": -250 if weight_change_kg < 0 else 0,
            "mantenimiento": int(weight_change_kg * 200),
            "fuerza": 150,
            "resistencia": 100
        }
        
        adjustment = calorie_adjustments.get(goal, 0)
        
        if goal == "mantenimiento":
            new_calories = max(current_calories + adjustment, 1200)
            changes.append(f"Mantenimiento: {adjustment:+.0f} kcal")
        else:
            new_calories = max(current_calories + adjustment, 1200)
            changes.append(f"Objetivo {goal}: {adjustment:+d} kcal")
        
        # Calcular factor de ajuste
        calorie_factor = new_calories / original_calories if original_calories > 0 else 1.0
        
        # Ajustar cantidades de alimentos de manera eficiente
        for comida in current_diet.get("meals", []):
            for alimento in comida.get("alimentos", []):
                # Ajustar cantidad
                cantidad_str = alimento.get("cantidad", "100g")
                if "g" in cantidad_str:
                    cantidad_num = int(cantidad_str.replace("g", ""))
                    nueva_cantidad = max(int(cantidad_num * calorie_factor), 10)
                    alimento["cantidad"] = f"{nueva_cantidad}g"
                elif "ml" in cantidad_str:
                    cantidad_num = int(cantidad_str.replace("ml", ""))
                    nueva_cantidad = max(int(cantidad_num * calorie_factor), 50)
                    alimento["cantidad"] = f"{nueva_cantidad}ml"
                
                # Ajustar macros proporcionalmente
                alimento["proteina"] = max(int(alimento.get("proteina", 0) * calorie_factor), 1)
                alimento["carbos"] = max(int(alimento.get("carbos", 0) * calorie_factor), 0)
                alimento["grasas"] = max(int(alimento.get("grasas", 0) * calorie_factor), 0)
        
        # Recalcular macros totales de manera eficiente
        total_proteina = sum(
            sum(alimento.get("proteina", 0) for alimento in comida.get("alimentos", [])) 
            for comida in current_diet.get("meals", [])
        )
        total_carbos = sum(
            sum(alimento.get("carbos", 0) for alimento in comida.get("alimentos", [])) 
            for comida in current_diet.get("meals", [])
        )
        total_grasas = sum(
            sum(alimento.get("grasas", 0) for alimento in comida.get("alimentos", [])) 
            for comida in current_diet.get("meals", [])
        )
        
        # Actualizar valores en la dieta
        current_diet["total_kcal"] = new_calories
        current_diet["macros"] = {
            "proteina": total_proteina,
            "carbohidratos": total_carbos,
            "grasas": total_grasas
        }
        current_diet["objetivo"] = goal
        current_diet["version"] = increment_diet_version(current_diet.get("version", "1.0.0"))
        current_diet["updated_at"] = datetime.utcnow().isoformat()
        
        changes.extend([
            f"Calorías: {original_calories} → {new_calories} kcal/día",
            f"Proteína: {total_proteina}g/día",
            f"Carbohidratos: {total_carbos}g/día", 
            f"Grasas: {total_grasas}g/día"
        ])
        
        # Guardar cambios en UNA sola transacción
        await db_service.update_user_data(user_id, {
            "current_diet": current_diet
        }, db)
        
        # Añadir registro de modificación
        await db_service.add_modification_record(
            user_id,
            "diet_macro_recalculation",
            {
                "weight_change": weight_change_kg,
                "goal": goal,
                "previous_diet": previous_diet,
                "changes": changes
            },
            f"Recálculo de macros para objetivo: {goal}",
            db
        )
        
        return {
            "success": True,
            "message": f"Macros recalculados para objetivo {goal}. Calorías ajustadas a {new_calories} kcal/día",
            "changes": changes
        }
        
    except Exception as e:
        logger.error(f"Error en handle_recalculate_macros: {e}")
        return {
            "success": False,
            "message": f"Error recalculando macros: {str(e)}",
            "changes": []
        }

async def handle_adjust_routine_difficulty(
    user_id: int,
    difficulty_change: str,
    reason: str,
    db: Session
) -> Dict[str, Any]:
    """
    Ajusta la dificultad de la rutina - VERSIÓN OPTIMIZADA
    """
    try:
        # Obtener datos del usuario en UNA sola consulta
        user_data = await db_service.get_user_complete_data(user_id, db)
        current_routine = user_data["current_routine"]
        
        # Validar estructura de rutina
        if not isinstance(current_routine, dict) or "exercises" not in current_routine:
            return {
                "success": False,
                "message": "Estructura de rutina inválida. No se puede modificar.",
                "changes": []
            }
        
        changes = []
        
        # Ajustar dificultad de manera eficiente
        for ejercicio in current_routine.get("exercises", []):
            if isinstance(ejercicio, dict):
                if difficulty_change == "increase":
                    # Aumentar series o peso
                    current_sets = ejercicio.get("sets", 3)
                    new_sets = min(current_sets + 1, 5)  # Máximo 5 series
                    ejercicio["sets"] = new_sets
                    changes.append(f"Aumentadas series: {current_sets} → {new_sets}")
                elif difficulty_change == "decrease":
                    # Disminuir series o peso
                    current_sets = ejercicio.get("sets", 3)
                    new_sets = max(current_sets - 1, 2)  # Mínimo 2 series
                    ejercicio["sets"] = new_sets
                    changes.append(f"Reducidas series: {current_sets} → {new_sets}")
        
        # Actualizar versión y timestamp
        current_routine["version"] = increment_routine_version(current_routine.get("version", "1.0.0"))
        current_routine["updated_at"] = datetime.utcnow().isoformat()
        
        # Guardar cambios
        await db_service.update_user_data(user_id, {
            "current_routine": current_routine
        }, db)
        
        # Añadir registro de modificación
        await db_service.add_modification_record(
            user_id,
            "routine_difficulty_adjustment",
            {
                "difficulty_change": difficulty_change,
                "reason": reason,
                "changes": changes
            },
            f"Ajuste de dificultad: {difficulty_change}",
            db
        )
        
        return {
            "success": True,
            "message": f"Dificultad de rutina ajustada: {difficulty_change}",
            "changes": changes
        }
        
    except Exception as e:
        logger.error(f"Error en handle_adjust_routine_difficulty: {e}")
        return {
            "success": False,
            "message": f"Error ajustando dificultad: {str(e)}",
            "changes": []
        }

async def handle_modify_routine_focus(
    user_id: int,
    focus_area: str,
    increase_frequency: bool,
    volume_change: str,
    db: Session
) -> Dict[str, Any]:
    """
    Modifica la rutina para enfocar más un área específica - VERSIÓN OPTIMIZADA
    """
    try:
        # Obtener datos del usuario en UNA sola consulta
        user_data = await db_service.get_user_complete_data(user_id, db)
        current_routine = user_data["current_routine"]
        
        # Validar estructura de rutina
        if not isinstance(current_routine, dict) or "exercises" not in current_routine:
            return {
                "success": False,
                "message": "Estructura de rutina inválida. No se puede modificar.",
                "changes": []
            }
        
        changes = []
        
        # Ejercicios específicos por área de enfoque
        focus_exercises = {
            "brazos": [
                {"name": "Curl de bíceps", "sets": 4, "reps": "10-12", "weight": "moderado"},
                {"name": "Tríceps press", "sets": 4, "reps": "10-12", "weight": "moderado"},
                {"name": "Martillo", "sets": 3, "reps": "12-15", "weight": "ligero"}
            ],
            "pecho": [
                {"name": "Press banca", "sets": 4, "reps": "8-10", "weight": "moderado"},
                {"name": "Flexiones", "sets": 3, "reps": "12-15", "weight": "cuerpo"},
                {"name": "Aperturas", "sets": 3, "reps": "12-15", "weight": "ligero"}
            ],
            "piernas": [
                {"name": "Sentadillas", "sets": 4, "reps": "12-15", "weight": "moderado"},
                {"name": "Zancadas", "sets": 3, "reps": "10-12", "weight": "moderado"},
                {"name": "Prensa", "sets": 4, "reps": "12-15", "weight": "moderado"}
            ],
            "gluteos": [
                {"name": "Hip thrust", "sets": 4, "reps": "12-15", "weight": "moderado"},
                {"name": "Puente de glúteos", "sets": 3, "reps": "15-20", "weight": "cuerpo"},
                {"name": "Patadas", "sets": 3, "reps": "15", "weight": "cuerpo"}
            ]
        }
        
        # Mapear sinónimos de focus_area
        area_mapping = {
            "pectoral": "pecho",
            "pectorales": "pecho",
            "chest": "pecho",
            "cuadriceps": "piernas",
            "cuádriceps": "piernas",
            "quads": "piernas",
            "muslos": "piernas",
            "deltoides": "hombros",
            "delts": "hombros",
            "shoulders": "hombros",
            "dorsales": "espalda",
            "back": "espalda",
            "biceps": "brazos",
            "bíceps": "brazos",
            "triceps": "brazos",
            "tríceps": "brazos",
            "arms": "brazos",
            "core": "core",
            "abdominales": "core",
            "abs": "core",
            "glutes": "gluteos",
            "glúteos": "gluteos",
            "gemelos": "pantorrillas",
            "calves": "pantorrillas"
        }
        
        # Mapear el área de enfoque
        mapped_focus_area = area_mapping.get(focus_area.lower(), focus_area.lower())
        
        # Añadir ejercicios de enfoque
        if mapped_focus_area in focus_exercises:
            new_exercises = focus_exercises[mapped_focus_area]
            
            # Ajustar volumen según volume_change
            if volume_change == "aumento_significativo":
                for exercise in new_exercises:
                    exercise["sets"] = min(exercise["sets"] + 2, 6)
                    changes.append(f"Aumento significativo de {exercise['name']}: {exercise['sets']} series")
            elif volume_change == "aumento_moderado":
                for exercise in new_exercises:
                    exercise["sets"] = min(exercise["sets"] + 1, 5)
                    changes.append(f"Aumento moderado de {exercise['name']}: {exercise['sets']} series")
            elif volume_change == "ligero_aumento":
                for exercise in new_exercises:
                    exercise["sets"] = min(exercise["sets"] + 1, 4)
                    changes.append(f"Ligero aumento de {exercise['name']}: {exercise['sets']} series")
            
            # Añadir a la rutina
            current_routine["exercises"].extend(new_exercises)
            
            for exercise in new_exercises:
                changes.append(f"Añadido: {exercise['name']} ({exercise['sets']} series)")
        
        # Actualizar versión y timestamp
        current_routine["version"] = increment_routine_version(current_routine.get("version", "1.0.0"))
        current_routine["updated_at"] = datetime.utcnow().isoformat()
        
        # Guardar cambios
        await db_service.update_user_data(user_id, {
            "current_routine": current_routine
        }, db)
        
        # Añadir registro de modificación
        await db_service.add_modification_record(
            user_id,
            "routine_focus_modification",
            {
                "focus_area": focus_area,
                "increase_frequency": increase_frequency,
                "volume_change": volume_change,
                "changes": changes
            },
            f"Enfoque en {focus_area}",
            db
        )
        
        return {
            "success": True,
            "message": f"Rutina enfocada en {focus_area} con {volume_change}",
            "changes": changes
        }
        
    except Exception as e:
        logger.error(f"Error en handle_modify_routine_focus: {e}")
        return {
            "success": False,
            "message": f"Error enfocando rutina: {str(e)}",
            "changes": []
        }

async def handle_revert_modification(user_id: int, db: Session) -> Dict[str, Any]:
    """
    Revierte la última modificación - VERSIÓN OPTIMIZADA
    """
    try:
        # Obtener última modificación
        last_modification = await db_service.get_last_modification(user_id, db)
        
        if not last_modification:
            return {
                "success": False,
                "message": "No hay modificaciones previas para revertir",
                "changes": []
            }
        
        # Obtener datos actuales del usuario
        user_data = await db_service.get_user_complete_data(user_id, db)
        
        changes = []
        reverted_data = {}
        
        # Revertir según el tipo de modificación
        modification_type = last_modification.get("type", "")
        modification_data = last_modification.get("data", {})
        
        if "routine" in modification_type:
            # Revertir rutina
            if "previous_routine" in modification_data:
                reverted_data["current_routine"] = modification_data["previous_routine"]
                changes.append("Rutina revertida a estado anterior")
        
        if "diet" in modification_type:
            # Revertir dieta
            if "previous_diet" in modification_data:
                reverted_data["current_diet"] = modification_data["previous_diet"]
                changes.append("Dieta revertida a estado anterior")
        
        if reverted_data:
            # Guardar datos revertidos
            await db_service.update_user_data(user_id, reverted_data, db)
            
            # Eliminar última modificación del historial
            await db_service.remove_last_modification(user_id, db)
            
            return {
                "success": True,
                "message": f"Modificación revertida: {last_modification.get('description', 'Última modificación')}",
                "changes": changes
            }
        else:
            return {
                "success": False,
                "message": "No se pudo revertir la modificación",
                "changes": []
            }
        
    except Exception as e:
        logger.error(f"Error en handle_revert_modification: {e}")
        return {
            "success": False,
            "message": f"Error revirtiendo modificación: {str(e)}",
            "changes": []
        }

# ==================== HANDLERS STUB PARA FUNCIONES NO IMPLEMENTADAS ====================

async def handle_substitute_food(user_id: int, food_to_replace: str, replacement_food: str, db: Session) -> Dict[str, Any]:
    """Handler para sustitución de alimentos con validación de alergias"""
    try:
        logger.info(f"Sustituyendo alimento: {food_to_replace} → {replacement_food}")
        
        # Obtener datos del usuario
        user_data = await db_service.get_user_complete_data(user_id, db)
        current_diet = user_data["current_diet"]
        user_allergies = user_data.get("alergias", "").split(",") if user_data.get("alergias") else []
        disliked_foods = user_data.get("disliked_foods", [])
        
        # Validar estructura de dieta
        if not isinstance(current_diet, dict) or "meals" not in current_diet:
            return {
                "success": False,
                "message": "Estructura de dieta inválida. No se puede modificar.",
                "changes": []
            }
        
        changes = []
        meals = current_diet.get("meals", [])
        
        # Buscar y sustituir el alimento en todas las comidas
        for meal in meals:
            if isinstance(meal, dict):
                meal_name = meal.get("name", "")
                foods = meal.get("alimentos", [])
                
                # Buscar el alimento a sustituir
                for i, food_item in enumerate(foods):
                    if isinstance(food_item, str) and food_to_replace.lower() in food_item.lower():
                        # Validar que el alimento de reemplazo no tenga alergias
                        from app.utils.allergy_detection import validate_food_against_allergies
                        
                        validation = validate_food_against_allergies(replacement_food, user_allergies)
                        
                        if validation["is_safe"]:
                            # Sustituir el alimento
                            foods[i] = replacement_food
                            changes.append(f"Sustituido en {meal_name}: {food_to_replace} → {replacement_food}")
                        else:
                            # Proporcionar alternativas seguras
                            from app.utils.allergy_detection import get_allergy_safe_alternatives
                            safe_alternatives = get_allergy_safe_alternatives(food_to_replace, user_allergies)
                            
                            if safe_alternatives:
                                # Usar la primera alternativa segura
                                foods[i] = safe_alternatives[0]
                                changes.append(f"Sustituido en {meal_name}: {food_to_replace} → {safe_alternatives[0]} (alternativa segura)")
                            else:
                                changes.append(f"No se pudo sustituir en {meal_name}: {replacement_food} contiene alergias")
        
        # Actualizar versión y timestamp
        current_diet["version"] = increment_routine_version(current_diet.get("version", "1.0.0"))
        current_diet["updated_at"] = datetime.utcnow().isoformat()
        
        # Guardar cambios
        await db_service.update_user_data(user_id, {
            "current_diet": current_diet
        }, db)
        
        # Añadir registro de modificación
        await db_service.add_modification_record(
            user_id,
            "food_substitution",
            {
                "food_to_replace": food_to_replace,
                "replacement_food": replacement_food,
                "changes": changes
            },
            f"Sustitución de alimento: {food_to_replace}",
            db
        )
        
        return {
            "success": True,
            "message": f"Alimento sustituido correctamente: {food_to_replace} → {replacement_food}",
            "changes": changes
        }
        
    except Exception as e:
        logger.error(f"Error en handle_substitute_food: {e}")
        return {
            "success": False,
            "message": f"Error sustituyendo alimento: {str(e)}",
            "changes": []
        }

async def handle_generate_alternatives(user_id: int, meal_type: str, db: Session) -> Dict[str, Any]:
    """Handler stub para generar alternativas de comidas"""
    return {
        "success": False,
        "message": "Función de alternativas de comidas no implementada aún",
        "changes": []
    }

async def handle_simplify_diet(user_id: int, complexity_level: str, db: Session) -> Dict[str, Any]:
    """Handler stub para simplificar dieta"""
    return {
        "success": False,
        "message": "Función de simplificación de dieta no implementada aún",
        "changes": []
    }

async def handle_adjust_menstrual_cycle(user_id: int, cycle_phase: str, db: Session) -> Dict[str, Any]:
    """Handler stub para ajuste del ciclo menstrual"""
    return {
        "success": False,
        "message": "Función de ajuste menstrual no implementada aún",
        "changes": []
    }


async def handle_substitute_exercise(
    user_id: int,
    exercise_to_replace: str,
    replacement_reason: str,
    target_muscles: str,
    equipment_available: str = "cualquiera",
    db: Session = None
) -> Dict[str, Any]:
    """
    Sustituye un ejercicio específico por otro alternativo
    """
    try:
        logger.info(f"Sustituyendo ejercicio: {exercise_to_replace} por razón: {replacement_reason}")
        
        user_data = await db_service.get_user_complete_data(user_id, db)
        current_routine = user_data["current_routine"]
        
        if not isinstance(current_routine, dict) or "exercises" not in current_routine:
            return {
                "success": False,
                "message": "Estructura de rutina inválida. No se puede modificar.",
                "changes": []
            }
        
        changes = []
        exercises = current_routine.get("exercises", [])
        
        # Mapeo de ejercicios alternativos por grupo muscular y equipamiento
        exercise_alternatives = {
            "pecho": {
                "peso_libre": ["Press de pecho con mancuernas", "Aperturas con mancuernas", "Press inclinado con mancuernas"],
                "cuerpo_libre": ["Flexiones", "Flexiones inclinadas", "Flexiones diamante"],
                "maquinas": ["Press de pecho en máquina", "Aperturas en máquina", "Press inclinado en máquina"],
                "bandas": ["Press de pecho con bandas", "Aperturas con bandas", "Cruces con bandas"]
            },
            "espalda": {
                "peso_libre": ["Remo con mancuerna", "Peso muerto rumano", "Dominadas asistidas"],
                "cuerpo_libre": ["Dominadas", "Remo invertido", "Superman"],
                "maquinas": ["Remo en máquina", "Jalón al pecho", "Remo sentado"],
                "bandas": ["Remo con bandas", "Jalón con bandas", "Pulldown con bandas"]
            },
            "hombros": {
                "peso_libre": ["Elevaciones laterales", "Press militar con mancuernas", "Elevaciones frontales"],
                "cuerpo_libre": ["Flexiones pike", "Handstand push-ups", "Flexiones en pared"],
                "maquinas": ["Press de hombros en máquina", "Elevaciones en máquina"],
                "bandas": ["Elevaciones con bandas", "Press de hombros con bandas"]
            },
            "piernas": {
                "peso_libre": ["Sentadillas con mancuernas", "Zancadas", "Peso muerto con mancuernas"],
                "cuerpo_libre": ["Sentadillas", "Zancadas", "Puente de glúteos", "Sentadilla sumo"],
                "maquinas": ["Prensa de piernas", "Extensión de cuádriceps", "Curl femoral"],
                "bandas": ["Sentadillas con bandas", "Zancadas con bandas", "Clamshells"]
            },
            "brazos": {
                "peso_libre": ["Curl de bíceps", "Extensiones de tríceps", "Martillo"],
                "cuerpo_libre": ["Flexiones diamante", "Dips", "Curl de bíceps isométrico"],
                "maquinas": ["Curl en máquina", "Extensiones en máquina"],
                "bandas": ["Curl con bandas", "Extensiones con bandas"]
            }
        }
        
        # Buscar el ejercicio a sustituir
        exercise_found = False
        for i, exercise in enumerate(exercises):
            if isinstance(exercise, dict):
                exercise_name = exercise.get("name", "")
            else:
                exercise_name = str(exercise)
            
            if exercise_to_replace.lower() in exercise_name.lower():
                exercise_found = True
                
                # Obtener alternativas
                alternatives = exercise_alternatives.get(target_muscles, {}).get(equipment_available, [])
                if not alternatives:
                    # Si no hay alternativas específicas, buscar en cualquier equipamiento
                    for eq_alternatives in exercise_alternatives.get(target_muscles, {}).values():
                        alternatives.extend(eq_alternatives)
                
                if alternatives:
                    # Seleccionar una alternativa aleatoria o la primera
                    new_exercise = alternatives[0]
                    
                    if isinstance(exercise, dict):
                        exercises[i] = {
                            "name": new_exercise,
                            "sets": exercise.get("sets", 3),
                            "reps": exercise.get("reps", "10-12"),
                            "weight": exercise.get("weight", "moderado")
                        }
                    else:
                        exercises[i] = new_exercise
                    
                    changes.append(f"Sustituido: {exercise_name} → {new_exercise}")
                    changes.append(f"Razón: {replacement_reason}")
                    changes.append(f"Grupo muscular: {target_muscles}")
                    changes.append(f"Equipamiento: {equipment_available}")
                else:
                    changes.append(f"No se encontraron alternativas para {exercise_name}")
        
        if not exercise_found:
            changes.append(f"No se encontró el ejercicio '{exercise_to_replace}' en la rutina")
        
        # Actualizar versión y timestamp
        current_routine["version"] = increment_routine_version(current_routine.get("version", "1.0.0"))
        current_routine["updated_at"] = datetime.utcnow().isoformat()
        
        # Guardar cambios
        await db_service.update_user_data(user_id, {
            "current_routine": current_routine
        }, db)
        
        await db_service.add_modification_record(
            user_id,
            "exercise_substitution",
            {
                "exercise_to_replace": exercise_to_replace,
                "replacement_reason": replacement_reason,
                "target_muscles": target_muscles,
                "equipment_available": equipment_available,
                "changes": changes
            },
            f"Sustitución de ejercicio: {exercise_to_replace}",
            db
        )
        
        return {
            "success": True,
            "message": f"Ejercicio sustituido: {exercise_to_replace} por {replacement_reason}",
            "changes": changes
        }
        
    except Exception as e:
        logger.error(f"Error en handle_substitute_exercise: {e}")
        return {
            "success": False,
            "message": f"Error sustituyendo ejercicio: {str(e)}",
            "changes": []
        }


async def handle_modify_routine_equipment(
    user_id: int,
    missing_equipment: str,
    available_equipment: str,
    affected_exercises: str = "",
    db: Session = None
) -> Dict[str, Any]:
    """
    Adapta la rutina cuando falta equipamiento específico
    """
    try:
        logger.info(f"Adaptando rutina por falta de equipamiento: {missing_equipment}")
        
        user_data = await db_service.get_user_complete_data(user_id, db)
        current_routine = user_data["current_routine"]
        
        if not isinstance(current_routine, dict) or "exercises" not in current_routine:
            return {
                "success": False,
                "message": "Estructura de rutina inválida. No se puede modificar.",
                "changes": []
            }
        
        changes = []
        exercises = current_routine.get("exercises", [])
        
        # Mapeo de equipamiento faltante a alternativas
        equipment_substitutions = {
            "press_banca": ["Press de pecho con mancuernas", "Flexiones", "Press de pecho en máquina"],
            "sentadilla_rack": ["Sentadillas con mancuernas", "Sentadillas", "Prensa de piernas"],
            "pesas_libres": ["Ejercicios con mancuernas", "Ejercicios con peso corporal", "Ejercicios con bandas"],
            "maquinas": ["Ejercicios con peso libre", "Ejercicios con peso corporal", "Ejercicios con bandas"],
            "smith_machine": ["Ejercicios con barra libre", "Ejercicios con mancuernas", "Ejercicios con peso corporal"],
            "barras": ["Mancuernas", "Peso corporal", "Bandas elásticas"],
            "discos": ["Mancuernas", "Kettlebells", "Bandas elásticas"],
            "mancuernas": ["Peso corporal", "Bandas elásticas", "Kettlebells"],
            "cables": ["Bandas elásticas", "Mancuernas", "Peso corporal"],
            "poleas": ["Bandas elásticas", "Mancuernas", "Peso corporal"]
        }
        
        # Obtener alternativas para el equipamiento faltante
        alternatives = equipment_substitutions.get(missing_equipment, [])
        
        # Buscar ejercicios que usen el equipamiento faltante
        modified_exercises = 0
        for i, exercise in enumerate(exercises):
            if isinstance(exercise, dict):
                exercise_name = exercise.get("name", "")
            else:
                exercise_name = str(exercise)
            
            # Verificar si el ejercicio podría usar el equipamiento faltante
            equipment_keywords = {
                "press_banca": ["press banca", "bench press", "press de banca"],
                "sentadilla_rack": ["sentadilla", "squat", "prensa"],
                "pesas_libres": ["peso libre", "barra", "discos"],
                "maquinas": ["máquina", "machine"],
                "smith_machine": ["smith"],
                "barras": ["barra", "bar"],
                "discos": ["discos", "discs"],
                "mancuernas": ["mancuernas", "dumbbells"],
                "cables": ["cables", "poleas"],
                "poleas": ["poleas", "cables"]
            }
            
            keywords = equipment_keywords.get(missing_equipment, [])
            exercise_needs_substitution = any(keyword in exercise_name.lower() for keyword in keywords)
            
            if exercise_needs_substitution and alternatives:
                # Seleccionar alternativa basada en equipamiento disponible
                if available_equipment == "peso_libre" and "mancuernas" in str(alternatives):
                    new_exercise = "Press de pecho con mancuernas"
                elif available_equipment == "cuerpo_libre":
                    new_exercise = "Flexiones" if "press" in exercise_name.lower() else "Sentadillas"
                elif available_equipment == "bandas":
                    new_exercise = "Press de pecho con bandas"
                else:
                    new_exercise = alternatives[0]
                
                if isinstance(exercise, dict):
                    exercises[i] = {
                        "name": new_exercise,
                        "sets": exercise.get("sets", 3),
                        "reps": exercise.get("reps", "10-12"),
                        "weight": exercise.get("weight", "moderado")
                    }
                else:
                    exercises[i] = new_exercise
                
                changes.append(f"Adaptado: {exercise_name} → {new_exercise}")
                modified_exercises += 1
        
        if modified_exercises == 0:
            changes.append(f"No se encontraron ejercicios que requieran {missing_equipment}")
        else:
            changes.append(f"Adaptados {modified_exercises} ejercicios por falta de {missing_equipment}")
            changes.append(f"Usando equipamiento disponible: {available_equipment}")
        
        # Actualizar versión y timestamp
        current_routine["version"] = increment_routine_version(current_routine.get("version", "1.0.0"))
        current_routine["updated_at"] = datetime.utcnow().isoformat()
        
        # Guardar cambios
        await db_service.update_user_data(user_id, {
            "current_routine": current_routine
        }, db)
        
        await db_service.add_modification_record(
            user_id,
            "equipment_adaptation",
            {
                "missing_equipment": missing_equipment,
                "available_equipment": available_equipment,
                "affected_exercises": affected_exercises,
                "changes": changes
            },
            f"Adaptación por falta de equipamiento: {missing_equipment}",
            db
        )
        
        return {
            "success": True,
            "message": f"Rutina adaptada por falta de {missing_equipment}",
            "changes": changes
        }
        
    except Exception as e:
        logger.error(f"Error en handle_modify_routine_equipment: {e}")
        return {
            "success": False,
            "message": f"Error adaptando rutina por equipamiento: {str(e)}",
            "changes": []
        }
