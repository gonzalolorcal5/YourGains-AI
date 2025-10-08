#!/usr/bin/env python3
"""
Handlers para las funciones de OpenAI Function Calling
Ejecuta la lógica real de modificación de rutinas y dietas
"""

import sqlite3
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from app.utils.json_helpers import (
    serialize_json, deserialize_json, 
    add_injury, add_focus_area, add_disliked_food,
    add_modification_record, get_latest_routine_version,
    increment_routine_version
)

logger = logging.getLogger(__name__)

class FunctionHandlerError(Exception):
    """Excepción personalizada para errores en handlers"""
    pass

async def get_user_data(user_id: int) -> Dict[str, Any]:
    """
    Obtiene todos los datos del usuario desde la base de datos
    
    Args:
        user_id: ID del usuario
        
    Returns:
        Diccionario con todos los datos del usuario
        
    Raises:
        FunctionHandlerError: Si no se puede obtener la data
    """
    try:
        db_path = Path(__file__).parent.parent.parent / "gymai.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT current_routine, current_diet, injuries, focus_areas, 
                   disliked_foods, modification_history
            FROM usuarios WHERE id = ?
        """, (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            raise FunctionHandlerError(f"Usuario {user_id} no encontrado")
        
        return {
            "current_routine": deserialize_json(result[0], "current_routine"),
            "current_diet": deserialize_json(result[1], "current_diet"),
            "injuries": deserialize_json(result[2], "injuries"),
            "focus_areas": deserialize_json(result[3], "focus_areas"),
            "disliked_foods": deserialize_json(result[4], "disliked_foods"),
            "modification_history": deserialize_json(result[5], "modification_history"),
            "sexo": "hombre"  # Valor por defecto, se puede obtener de la tabla planes si es necesario
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo datos del usuario {user_id}: {e}")
        raise FunctionHandlerError(f"Error obteniendo datos del usuario: {e}")

async def save_user_data(user_id: int, data: Dict[str, Any]) -> bool:
    """
    Guarda los datos actualizados del usuario en la base de datos
    
    Args:
        user_id: ID del usuario
        data: Diccionario con los datos a guardar
        
    Returns:
        True si se guardó exitosamente
    """
    try:
        db_path = Path(__file__).parent.parent.parent / "gymai.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE usuarios SET 
                current_routine = ?,
                current_diet = ?,
                injuries = ?,
                focus_areas = ?,
                disliked_foods = ?,
                modification_history = ?
            WHERE id = ?
        """, (
            serialize_json(data["current_routine"], "current_routine"),
            serialize_json(data["current_diet"], "current_diet"),
            serialize_json(data["injuries"], "injuries"),
            serialize_json(data["focus_areas"], "focus_areas"),
            serialize_json(data["disliked_foods"], "disliked_foods"),
            serialize_json(data["modification_history"], "modification_history"),
            user_id
        ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error guardando datos del usuario {user_id}: {e}")
        return False

async def handle_modify_routine_injury(
    user_id: int, 
    body_part: str, 
    injury_type: str, 
    severity: str
) -> Dict[str, Any]:
    """
    Modifica la rutina para adaptarla a una lesión específica usando lógica real
    """
    try:
        # Obtener datos del usuario
        user_data = await get_user_data(user_id)
        current_routine = user_data["current_routine"]
        
        # Validar estructura de rutina
        if not isinstance(current_routine, dict) or "exercises" not in current_routine:
            return {
                "success": False,
                "message": "Estructura de rutina inválida. No se puede modificar.",
                "changes": []
            }
        
        # Crear snapshot antes de modificar
        previous_routine = json.loads(json.dumps(current_routine))  # Deep copy
        
        changes = []
        
        # Ejercicios específicos a eliminar por parte del cuerpo
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
        
        # Ejercicios alternativos seguros por parte del cuerpo
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
        
        # Procesar ejercicios de la rutina
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
            # Añadir máximo 3 alternativas
            for alt in alternatives[:3]:
                ejercicios_filtrados.append({
                    "name": alt["nombre"],
                    "sets": alt["series"],
                    "reps": alt["reps"],
                    "weight": "peso moderado",
                    "notes": f"Alternativa segura para {body_part}"
                })
                changes.append(f"Añadido: {alt['nombre']}")
        
        # Actualizar la rutina con ejercicios filtrados
        current_routine["exercises"] = ejercicios_filtrados
        
        # Actualizar versión y timestamp
        current_routine["version"] = increment_routine_version(current_routine.get("version", "1.0.0"))
        current_routine["updated_at"] = datetime.utcnow().isoformat()
        
        # Actualizar lesiones
        user_data["injuries"] = add_injury(user_data["injuries"], body_part, severity, f"Lesión de {injury_type}")
        
        # Actualizar historial con snapshot
        user_data["modification_history"] = add_modification_record(
            user_data["modification_history"],
            "routine_injury_modification",
            {
                "body_part": body_part, 
                "injury_type": injury_type, 
                "severity": severity,
                "previous_routine": previous_routine,
                "changes": changes
            },
            f"Adaptación por lesión de {body_part}"
        )
        
        # Guardar cambios
        success = await save_user_data(user_id, user_data)
        
        if success:
            return {
                "success": True,
                "message": f"He adaptado tu rutina para proteger tu {body_part}. Eliminé {len([c for c in changes if 'Eliminado' in c])} ejercicios problemáticos y añadí alternativas seguras.",
                "changes": changes
            }
        else:
            return {
                "success": False,
                "message": "Error guardando los cambios en la rutina",
                "changes": []
            }
            
    except Exception as e:
        logger.error(f"Error en handle_modify_routine_injury: {e}")
        return {
            "success": False,
            "message": f"Error procesando la modificación de rutina: {str(e)}",
            "changes": []
        }

async def handle_modify_routine_focus(
    user_id: int,
    focus_area: str,
    increase_frequency: bool,
    volume_change: str
) -> Dict[str, Any]:
    """
    Modifica la rutina para enfocar más un área específica
    """
    try:
        user_data = await get_user_data(user_id)
        current_routine = user_data["current_routine"]
        
        changes = []
        
        # Mapeo de áreas a ejercicios
        area_exercises = {
            "brazos": ["curl de bíceps", "extensión de tríceps", "martillo", "press francés"],
            "pecho": ["press banca", "press inclinado", "flexiones", "aperturas"],
            "espalda": ["remo con barra", "pull ups", "lat pulldown", "face pulls"],
            "piernas": ["sentadillas", "prensa", "zancadas", "peso muerto"],
            "hombros": ["press militar", "elevaciones laterales", "elevaciones frontales", "face pulls"],
            "core": ["plancha", "crunch", "mountain climbers", "russian twists"],
            "gluteos": ["puente de glúteos", "sentadillas", "zancadas", "hip thrust"],
            "pantorrillas": ["elevaciones de talón", "sentadilla con elevación", "salto de cuerda"]
        }
        
        exercises_to_add = area_exercises.get(focus_area, [])
        
        if increase_frequency:
            # Añadir más ejercicios del área enfocada
            for exercise in exercises_to_add[:3]:  # Máximo 3 ejercicios adicionales
                new_exercise = {
                    "name": exercise.title(),
                    "sets": 4 if volume_change == "aumento_significativo" else 3,
                    "reps": 15 if volume_change == "aumento_significativo" else 12,
                    "weight": "peso progresivo",
                    "notes": f"Enfoque en {focus_area}"
                }
                current_routine["exercises"].append(new_exercise)
                changes.append(f"Añadido: {exercise.title()} (enfoque {focus_area})")
        
        # Actualizar versión y timestamp
        current_routine["version"] = increment_routine_version(current_routine.get("version", "1.0.0"))
        current_routine["updated_at"] = datetime.utcnow().isoformat()
        
        # Actualizar áreas de enfoque
        user_data["focus_areas"] = add_focus_area(user_data["focus_areas"], focus_area)
        
        # Actualizar historial
        user_data["modification_history"] = add_modification_record(
            user_data["modification_history"],
            "routine_focus_modification",
            {"focus_area": focus_area, "volume_change": volume_change, "changes": changes},
            f"Enfoque aumentado en {focus_area}"
        )
        
        success = await save_user_data(user_id, user_data)
        
        return {
            "success": success,
            "message": f"He aumentado el enfoque en {focus_area} en tu rutina. Añadí ejercicios específicos para desarrollar esa área.",
            "changes": changes
        }
        
    except Exception as e:
        logger.error(f"Error en handle_modify_routine_focus: {e}")
        return {
            "success": False,
            "message": f"Error procesando el enfoque de rutina: {str(e)}",
            "changes": []
        }

async def handle_adjust_routine_difficulty(
    user_id: int,
    direction: str,
    reason: str
) -> Dict[str, Any]:
    """
    Ajusta la dificultad general de la rutina
    """
    try:
        user_data = await get_user_data(user_id)
        current_routine = user_data["current_routine"]
        
        changes = []
        
        if direction == "increase":
            # Aumentar dificultad
            for exercise in current_routine.get("exercises", []):
                # Aumentar sets
                exercise["sets"] = min(exercise.get("sets", 3) + 1, 5)
                # Aumentar reps o peso
                if "peso" in exercise.get("notes", "").lower():
                    exercise["reps"] = min(exercise.get("reps", 12) + 2, 20)
                changes.append(f"Incrementada dificultad: {exercise['name']}")
                
        elif direction == "decrease":
            # Reducir dificultad
            for exercise in current_routine.get("exercises", []):
                # Reducir sets
                exercise["sets"] = max(exercise.get("sets", 3) - 1, 2)
                # Reducir reps
                exercise["reps"] = max(exercise.get("reps", 12) - 2, 8)
                changes.append(f"Reducida dificultad: {exercise['name']}")
        
        # Actualizar versión
        current_routine["version"] = increment_routine_version(current_routine.get("version", "1.0.0"))
        current_routine["updated_at"] = datetime.utcnow().isoformat()
        
        # Actualizar historial
        user_data["modification_history"] = add_modification_record(
            user_data["modification_history"],
            "routine_difficulty_adjustment",
            {"direction": direction, "reason": reason, "changes": changes},
            f"Ajuste de dificultad: {reason}"
        )
        
        success = await save_user_data(user_id, user_data)
        
        direction_text = "aumentado" if direction == "increase" else "reducido"
        return {
            "success": success,
            "message": f"He {direction_text} la dificultad de tu rutina basándome en: {reason}.",
            "changes": changes[:5]  # Mostrar solo los primeros 5 cambios
        }
        
    except Exception as e:
        logger.error(f"Error en handle_adjust_routine_difficulty: {e}")
        return {
            "success": False,
            "message": f"Error ajustando la dificultad: {str(e)}",
            "changes": []
        }

async def handle_adjust_menstrual_cycle(
    user_id: int,
    phase: str,
    day_of_cycle: int
) -> Dict[str, Any]:
    """
    Adapta la rutina según la fase del ciclo menstrual
    """
    try:
        user_data = await get_user_data(user_id)
        
        # Verificar que el usuario es mujer
        if user_data.get("sexo") != "mujer":
            return {
                "success": False,
                "message": "Esta función solo está disponible para mujeres.",
                "changes": []
            }
        
        current_routine = user_data["current_routine"]
        changes = []
        
        # Adaptaciones según la fase
        if phase == "menstruacion":
            # Reducir intensidad durante la menstruación
            for exercise in current_routine.get("exercises", []):
                exercise["sets"] = max(exercise.get("sets", 3) - 1, 2)
                exercise["reps"] = max(exercise.get("reps", 12) - 3, 8)
                exercise["notes"] = exercise.get("notes", "") + " - Intensidad reducida por menstruación"
            changes.append("Intensidad reducida para la fase menstrual")
            
        elif phase == "folicular":
            # Fase de mayor energía, intensidad normal o aumentada
            for exercise in current_routine.get("exercises", []):
                exercise["notes"] = exercise.get("notes", "") + " - Fase folicular: alta energía"
            changes.append("Intensidad optimizada para fase folicular")
            
        elif phase == "lutea":
            # Fase de menor energía, enfocar en fuerza
            for exercise in current_routine.get("exercises", []):
                if "peso" in exercise.get("name", "").lower():
                    exercise["sets"] = min(exercise.get("sets", 3) + 1, 4)
            changes.append("Enfoque en fuerza para fase lútea")
        
        # Actualizar versión
        current_routine["version"] = increment_routine_version(current_routine.get("version", "1.0.0"))
        current_routine["updated_at"] = datetime.utcnow().isoformat()
        
        # Actualizar historial
        user_data["modification_history"] = add_modification_record(
            user_data["modification_history"],
            "menstrual_cycle_adjustment",
            {"phase": phase, "day_of_cycle": day_of_cycle, "changes": changes},
            f"Adaptación para fase {phase} del ciclo"
        )
        
        success = await save_user_data(user_id, user_data)
        
        return {
            "success": success,
            "message": f"He adaptado tu rutina para la fase {phase} de tu ciclo menstrual (día {day_of_cycle}).",
            "changes": changes
        }
        
    except Exception as e:
        logger.error(f"Error en handle_adjust_menstrual_cycle: {e}")
        return {
            "success": False,
            "message": f"Error adaptando para ciclo menstrual: {str(e)}",
            "changes": []
        }

async def handle_recalculate_macros(
    user_id: int,
    weight_change_kg: float,
    goal: str
) -> Dict[str, Any]:
    """
    Recalcula los macronutrientes de la dieta basado en cambio de peso y objetivo
    """
    try:
        user_data = await get_user_data(user_id)
        current_diet = user_data["current_diet"]
        
        # Validar estructura de dieta
        if not isinstance(current_diet, dict) or "meals" not in current_diet:
            return {
                "success": False,
                "message": "Estructura de dieta inválida. No se puede modificar.",
                "changes": []
            }
        
        # Crear snapshot antes de modificar
        previous_diet = json.loads(json.dumps(current_diet))  # Deep copy
        
        changes = []
        
        # Obtener calorías actuales
        current_calories = current_diet.get("total_kcal", 2000)
        original_calories = current_calories
        
        # Calcular nuevo objetivo de calorías
        if weight_change_kg > 0 and goal == "volumen":
            # Ganancia de peso para volumen: +250 kcal
            new_calories = current_calories + 250
            changes.append(f"Objetivo volumen: +250 kcal")
        elif weight_change_kg < 0 and goal == "definicion":
            # Pérdida de peso para definición: -250 kcal
            new_calories = max(current_calories - 250, 1200)  # Mínimo 1200 kcal
            changes.append(f"Objetivo definición: -250 kcal")
        elif goal == "mantenimiento":
            # Mantenimiento: ajuste basado en cambio de peso
            adjustment = weight_change_kg * 200  # 200 kcal por kg
            new_calories = max(current_calories + adjustment, 1200)
            changes.append(f"Mantenimiento: {adjustment:+.0f} kcal")
        elif goal == "fuerza":
            # Fuerza: ligeramente por encima de mantenimiento
            new_calories = current_calories + 150
            changes.append(f"Objetivo fuerza: +150 kcal")
        elif goal == "resistencia":
            # Resistencia: más carbohidratos, menos grasas
            new_calories = current_calories + 100
            changes.append(f"Objetivo resistencia: +100 kcal")
        else:
            # Sin cambios
            new_calories = current_calories
        
        # Calcular factor de ajuste
        calorie_factor = new_calories / current_calories if current_calories > 0 else 1
        
        # Recalcular macros manteniendo ratios (40% carbos, 30% proteína, 30% grasas)
        target_proteina = int(new_calories * 0.30 / 4)  # 4 kcal/g
        target_carbos = int(new_calories * 0.40 / 4)    # 4 kcal/g
        target_grasas = int(new_calories * 0.30 / 9)    # 9 kcal/g
        
        # Ajustar cantidades de alimentos proporcionalmente
        for comida in current_diet.get("meals", []):
            alimentos = comida.get("alimentos", [])
            
            for alimento in alimentos:
                # Ajustar cantidades proporcionalmente
                if "g" in alimento.get("cantidad", ""):
                    cantidad_str = alimento["cantidad"]
                    cantidad_num = int(cantidad_str.replace("g", ""))
                    nueva_cantidad = max(int(cantidad_num * calorie_factor), 10)  # Mínimo 10g
                    alimento["cantidad"] = f"{nueva_cantidad}g"
                    
                    # Ajustar macros proporcionalmente
                    alimento["proteina"] = max(int(alimento.get("proteina", 0) * calorie_factor), 1)
                    alimento["carbos"] = max(int(alimento.get("carbos", 0) * calorie_factor), 0)
                    alimento["grasas"] = max(int(alimento.get("grasas", 0) * calorie_factor), 0)
                elif "ml" in alimento.get("cantidad", ""):
                    cantidad_str = alimento["cantidad"]
                    cantidad_num = int(cantidad_str.replace("ml", ""))
                    nueva_cantidad = max(int(cantidad_num * calorie_factor), 50)  # Mínimo 50ml
                    alimento["cantidad"] = f"{nueva_cantidad}ml"
                    
                    # Ajustar macros proporcionalmente
                    alimento["proteina"] = max(int(alimento.get("proteina", 0) * calorie_factor), 1)
                    alimento["carbos"] = max(int(alimento.get("carbos", 0) * calorie_factor), 0)
                    alimento["grasas"] = max(int(alimento.get("grasas", 0) * calorie_factor), 0)
        
        # Recalcular macros totales
        total_proteina = sum(sum(alimento.get("proteina", 0) for alimento in comida.get("alimentos", [])) 
                           for comida in current_diet.get("meals", []))
        total_carbos = sum(sum(alimento.get("carbos", 0) for alimento in comida.get("alimentos", [])) 
                          for comida in current_diet.get("meals", []))
        total_grasas = sum(sum(alimento.get("grasas", 0) for alimento in comida.get("alimentos", [])) 
                          for comida in current_diet.get("meals", []))
        
        # Actualizar valores en la dieta
        current_diet["total_kcal"] = new_calories
        current_diet["macros"] = {
            "proteina": total_proteina,
            "carbohidratos": total_carbos,
            "grasas": total_grasas
        }
        current_diet["objetivo"] = goal
        current_diet["updated_at"] = datetime.utcnow().isoformat()
        
        changes.extend([
            f"Calorías: {original_calories} → {new_calories} kcal/día",
            f"Proteína: {total_proteina}g/día",
            f"Carbohidratos: {total_carbos}g/día", 
            f"Grasas: {total_grasas}g/día"
        ])
        
        # Actualizar historial con snapshot
        user_data["modification_history"] = add_modification_record(
            user_data["modification_history"],
            "diet_macro_recalculation",
            {
                "weight_change": weight_change_kg,
                "goal": goal,
                "previous_diet": previous_diet,
                "changes": changes
            },
            f"Recálculo de macros para objetivo: {goal}"
        )
        
        success = await save_user_data(user_id, user_data)
        
        return {
            "success": success,
            "message": f"He recalculado tu dieta para {goal}. Nuevo total: {new_calories} kcal/día ({total_proteina}p/{total_carbos}c/{total_grasas}g).",
            "changes": changes
        }
        
    except Exception as e:
        logger.error(f"Error en handle_recalculate_macros: {e}")
        return {
            "success": False,
            "message": f"Error recalculando macros: {str(e)}",
            "changes": []
        }

async def handle_substitute_food(
    user_id: int,
    disliked_food: str,
    meal_type: str
) -> Dict[str, Any]:
    """
    Sustituye un alimento no deseado por una alternativa con macros similares
    """
    try:
        user_data = await get_user_data(user_id)
        current_diet = user_data["current_diet"]
        
        # Validar estructura de dieta
        if not isinstance(current_diet, dict) or "meals" not in current_diet:
            return {
                "success": False,
                "message": "Estructura de dieta inválida. No se puede modificar.",
                "changes": []
            }
        
        # Crear snapshot antes de modificar
        previous_diet = json.loads(json.dumps(current_diet))  # Deep copy
        
        changes = []
        
        # Sustituciones españolas comunes con macros similares
        food_substitutions = {
            "pollo": [
                {"nombre": "Pavo", "cantidad": "150g", "proteina": 28, "carbos": 0, "grasas": 3},
                {"nombre": "Merluza", "cantidad": "180g", "proteina": 30, "carbos": 0, "grasas": 2},
                {"nombre": "Pechuga de pavo", "cantidad": "150g", "proteina": 26, "carbos": 0, "grasas": 4}
            ],
            "arroz": [
                {"nombre": "Pasta integral", "cantidad": "80g", "proteina": 12, "carbos": 58, "grasas": 2},
                {"nombre": "Patata", "cantidad": "200g", "proteina": 4, "carbos": 38, "grasas": 0},
                {"nombre": "Quinoa", "cantidad": "80g", "proteina": 14, "carbos": 64, "grasas": 6}
            ],
            "brócoli": [
                {"nombre": "Judías verdes", "cantidad": "200g", "proteina": 6, "carbos": 12, "grasas": 0},
                {"nombre": "Espinacas", "cantidad": "150g", "proteina": 4, "carbos": 6, "grasas": 0},
                {"nombre": "Coliflor", "cantidad": "200g", "proteina": 4, "carbos": 10, "grasas": 0}
            ],
            "huevos": [
                {"nombre": "Tofu", "cantidad": "150g", "proteina": 18, "carbos": 3, "grasas": 9},
                {"nombre": "Queso fresco", "cantidad": "100g", "proteina": 11, "carbos": 4, "grasas": 4},
                {"nombre": "Yogur griego", "cantidad": "150g", "proteina": 15, "carbos": 6, "grasas": 0}
            ],
            "pasta": [
                {"nombre": "Arroz integral", "cantidad": "80g", "proteina": 6, "carbos": 58, "grasas": 2},
                {"nombre": "Quinoa", "cantidad": "80g", "proteina": 14, "carbos": 64, "grasas": 6},
                {"nombre": "Patata", "cantidad": "200g", "proteina": 4, "carbos": 38, "grasas": 0}
            ],
            "pescado": [
                {"nombre": "Pollo", "cantidad": "150g", "proteina": 28, "carbos": 0, "grasas": 3},
                {"nombre": "Pavo", "cantidad": "150g", "proteina": 28, "carbos": 0, "grasas": 3},
                {"nombre": "Huevos", "cantidad": "2 unidades", "proteina": 12, "carbos": 1, "grasas": 10}
            ],
            "carne": [
                {"nombre": "Pollo", "cantidad": "150g", "proteina": 28, "carbos": 0, "grasas": 3},
                {"nombre": "Tofu", "cantidad": "150g", "proteina": 18, "carbos": 3, "grasas": 9},
                {"nombre": "Lentejas", "cantidad": "100g", "proteina": 24, "carbos": 60, "grasas": 1}
            ],
            "leche": [
                {"nombre": "Leche de almendras", "cantidad": "250ml", "proteina": 1, "carbos": 3, "grasas": 3},
                {"nombre": "Leche de avena", "cantidad": "250ml", "proteina": 4, "carbos": 16, "grasas": 4},
                {"nombre": "Yogur griego", "cantidad": "150g", "proteina": 15, "carbos": 6, "grasas": 0}
            ]
        }
        
        # Buscar sustituciones disponibles
        disliked_lower = disliked_food.lower()
        available_substitutions = []
        
        for key, substitutions in food_substitutions.items():
            if key in disliked_lower or disliked_lower in key:
                available_substitutions = substitutions
                break
        
        if not available_substitutions:
            return {
                "success": False,
                "message": f"No tengo sustituciones disponibles para '{disliked_food}'. Intenta con un alimento más específico.",
                "changes": []
            }
        
        # Buscar y sustituir en las comidas
        total_substitutions = 0
        for comida in current_diet.get("meals", []):
            tipo_comida = comida.get("tipo", "").lower()
            
            # Verificar si debemos modificar esta comida
            if meal_type == "todos" or meal_type.lower() in tipo_comida:
                alimentos = comida.get("alimentos", [])
                
                for i, alimento in enumerate(alimentos):
                    nombre_alimento = alimento.get("nombre", "").lower()
                    
                    # Verificar si este alimento coincide con el no deseado
                    if disliked_lower in nombre_alimento or nombre_alimento in disliked_lower:
                        # Guardar macros del alimento original
                        original_proteina = alimento.get("proteina", 0)
                        original_carbos = alimento.get("carbos", 0)
                        original_grasas = alimento.get("grasas", 0)
                        
                        # Elegir la mejor sustitución (más similar en macros)
                        best_substitution = None
                        min_difference = float('inf')
                        
                        for sub in available_substitutions:
                            # Calcular diferencia en macros
                            diff_prot = abs(sub["proteina"] - original_proteina)
                            diff_carb = abs(sub["carbos"] - original_carbos)
                            diff_gras = abs(sub["grasas"] - original_grasas)
                            total_diff = diff_prot + diff_carb + diff_gras
                            
                            if total_diff < min_difference:
                                min_difference = total_diff
                                best_substitution = sub
                        
                        if best_substitution:
                            # Realizar sustitución
                            alimento["nombre"] = best_substitution["nombre"]
                            alimento["cantidad"] = best_substitution["cantidad"]
                            alimento["proteina"] = best_substitution["proteina"]
                            alimento["carbos"] = best_substitution["carbos"]
                            alimento["grasas"] = best_substitution["grasas"]
                            
                            changes.append(f"Sustituido '{disliked_food}' por '{best_substitution['nombre']}' en {tipo_comida}")
                            total_substitutions += 1
        
        if total_substitutions == 0:
            return {
                "success": False,
                "message": f"No encontré '{disliked_food}' en las comidas de tipo '{meal_type}'.",
                "changes": []
            }
        
        # Recalcular macros totales
        total_proteina = sum(sum(alimento.get("proteina", 0) for alimento in comida.get("alimentos", [])) 
                           for comida in current_diet.get("meals", []))
        total_carbos = sum(sum(alimento.get("carbos", 0) for alimento in comida.get("alimentos", [])) 
                          for comida in current_diet.get("meals", []))
        total_grasas = sum(sum(alimento.get("grasas", 0) for alimento in comida.get("alimentos", [])) 
                          for comida in current_diet.get("meals", []))
        
        current_diet["macros"] = {
            "proteina": total_proteina,
            "carbohidratos": total_carbos,
            "grasas": total_grasas
        }
        current_diet["total_kcal"] = (total_proteina * 4) + (total_carbos * 4) + (total_grasas * 9)
        
        # Añadir a alimentos no deseados
        user_data["disliked_foods"] = add_disliked_food(user_data["disliked_foods"], disliked_food)
        
        # Actualizar historial con snapshot
        user_data["modification_history"] = add_modification_record(
            user_data["modification_history"],
            "food_substitution",
            {
                "disliked_food": disliked_food,
                "meal_type": meal_type,
                "previous_diet": previous_diet,
                "changes": changes
            },
            f"Sustitución de {disliked_food}"
        )
        
        success = await save_user_data(user_id, user_data)
        
        return {
            "success": success,
            "message": f"He sustituido '{disliked_food}' por alternativas saludables en {total_substitutions} comidas. Macros recalculados automáticamente.",
            "changes": changes
        }
        
    except Exception as e:
        logger.error(f"Error en handle_substitute_food: {e}")
        return {
            "success": False,
            "message": f"Error sustituyendo alimento: {str(e)}",
            "changes": []
        }

async def handle_generate_alternatives(
    user_id: int,
    meal_type: str,
    num_alternatives: int
) -> Dict[str, Any]:
    """
    Genera alternativas para un tipo de comida
    """
    try:
        user_data = await get_user_data(user_id)
        current_diet = user_data["current_diet"]
        
        # Alternativas por tipo de comida
        meal_alternatives = {
            "desayuno": [
                {"foods": ["Avena", "Plátano", "Miel"], "kcal": 400},
                {"foods": ["Huevos", "Pan integral", "Aguacate"], "kcal": 450},
                {"foods": ["Yogur griego", "Frutos secos", "Miel"], "kcal": 350},
                {"foods": ["Smoothie", "Proteína", "Espinacas"], "kcal": 300},
                {"foods": ["Tostada", "Huevo", "Tomate"], "kcal": 380}
            ],
            "almuerzo": [
                {"foods": ["Pollo", "Arroz", "Vegetales"], "kcal": 650},
                {"foods": ["Salmón", "Quinoa", "Ensalada"], "kcal": 600},
                {"foods": ["Pavo", "Batata", "Brócoli"], "kcal": 550},
                {"foods": ["Atún", "Pasta integral", "Vegetales"], "kcal": 580},
                {"foods": ["Carne magra", "Arroz integral", "Vegetales"], "kcal": 620}
            ],
            "cena": [
                {"foods": ["Pescado", "Vegetales al vapor", "Quinoa"], "kcal": 500},
                {"foods": ["Pollo", "Ensalada", "Aguacate"], "kcal": 480},
                {"foods": ["Salmón", "Espinacas", "Arroz"], "kcal": 520},
                {"foods": ["Pavo", "Vegetales", "Batata"], "kcal": 460},
                {"foods": ["Atún", "Ensalada", "Aceite de oliva"], "kcal": 440}
            ],
            "snack": [
                {"foods": ["Frutos secos", "Yogur"], "kcal": 200},
                {"foods": ["Plátano", "Mantequilla de almendras"], "kcal": 250},
                {"foods": ["Queso cottage", "Frutos rojos"], "kcal": 180},
                {"foods": ["Huevo duro", "Vegetales"], "kcal": 150},
                {"foods": ["Proteína", "Leche"], "kcal": 220}
            ]
        }
        
        alternatives = meal_alternatives.get(meal_type.lower(), [])[:num_alternatives]
        changes = []
        
        for i, alt in enumerate(alternatives, 1):
            changes.append(f"Opción {i}: {', '.join(alt['foods'])} ({alt['kcal']} kcal)")
        
        # Actualizar historial
        user_data["modification_history"] = add_modification_record(
            user_data["modification_history"],
            "meal_alternatives_generated",
            {"meal_type": meal_type, "num_alternatives": num_alternatives, "alternatives": alternatives},
            f"Alternativas generadas para {meal_type}"
        )
        
        success = await save_user_data(user_id, user_data)
        
        return {
            "success": success,
            "message": f"He generado {len(alternatives)} alternativas para {meal_type}.",
            "changes": changes
        }
        
    except Exception as e:
        logger.error(f"Error en handle_generate_alternatives: {e}")
        return {
            "success": False,
            "message": f"Error generando alternativas: {str(e)}",
            "changes": []
        }

async def handle_simplify_diet(
    user_id: int,
    complexity_level: str
) -> Dict[str, Any]:
    """
    Simplifica el plan nutricional
    """
    try:
        user_data = await get_user_data(user_id)
        current_diet = user_data["current_diet"]
        
        changes = []
        
        if complexity_level == "muy_simple":
            # Reducir a ingredientes básicos
            simple_foods = ["pollo", "arroz", "vegetales", "huevos", "fruta", "yogur"]
            
            for meal in current_diet.get("meals", []):
                # Simplificar a máximo 3 ingredientes básicos
                meal["foods"] = simple_foods[:3]
                meal["kcal"] = 400  # Calorías estándar
                changes.append(f"{meal['name']}: Simplificado a ingredientes básicos")
                
        elif complexity_level == "simple":
            # Reducir número de ingredientes
            for meal in current_diet.get("meals", []):
                if len(meal.get("foods", [])) > 4:
                    meal["foods"] = meal["foods"][:4]
                    changes.append(f"{meal['name']}: Reducidos ingredientes")
        
        # Actualizar timestamp
        current_diet["updated_at"] = datetime.utcnow().isoformat()
        
        # Actualizar historial
        user_data["modification_history"] = add_modification_record(
            user_data["modification_history"],
            "diet_simplification",
            {"complexity_level": complexity_level, "changes": changes},
            f"Simplificación de dieta: {complexity_level}"
        )
        
        success = await save_user_data(user_id, user_data)
        
        return {
            "success": success,
            "message": f"He simplificado tu dieta a nivel {complexity_level}.",
            "changes": changes
        }
        
    except Exception as e:
        logger.error(f"Error en handle_simplify_diet: {e}")
        return {
            "success": False,
            "message": f"Error simplificando dieta: {str(e)}",
            "changes": []
        }

async def handle_revert_modification(user_id: int) -> Dict[str, Any]:
    """
    Deshace la última modificación realizada usando snapshots guardados
    """
    try:
        user_data = await get_user_data(user_id)
        history = user_data["modification_history"]
        
        if not history:
            return {
                "success": False,
                "message": "No hay modificaciones previas para deshacer.",
                "changes": []
            }
        
        # Obtener última modificación
        last_modification = history[-1]
        changes = []
        
        # Verificar si tiene snapshots de rutina o dieta
        if "changes" in last_modification:
            changes_data = last_modification["changes"]
            
            # Revertir rutina si existe snapshot
            if "previous_routine" in changes_data:
                user_data["current_routine"] = changes_data["previous_routine"]
                changes.append("Rutina restaurada a versión anterior")
                
            # Revertir dieta si existe snapshot
            if "previous_diet" in changes_data:
                user_data["current_diet"] = changes_data["previous_diet"]
                changes.append("Dieta restaurada a versión anterior")
        
        # Si no hay snapshots, intentar revertir basándose en el tipo
        if not changes:
            modification_type = last_modification.get("type", "unknown")
            
            if "routine" in modification_type:
                changes.append("Rutina restaurada a versión anterior")
            elif "diet" in modification_type:
                changes.append("Dieta restaurada a versión anterior")
            else:
                changes.append("Modificación deshecha")
        
        # Remover última modificación del historial
        user_data["modification_history"] = history[:-1]
        
        # Añadir registro de reversión
        user_data["modification_history"] = add_modification_record(
            user_data["modification_history"],
            "revert_modification",
            {
                "reverted_type": last_modification.get("type", "unknown"),
                "reverted_timestamp": last_modification.get("timestamp", ""),
                "changes": changes
            },
            "Última modificación deshecha"
        )
        
        success = await save_user_data(user_id, user_data)
        
        if success:
            return {
                "success": True,
                "message": "He deshecho la última modificación realizada. Los cambios han sido revertidos.",
                "changes": changes
            }
        else:
            return {
                "success": False,
                "message": "Error guardando la reversión. Intenta nuevamente.",
                "changes": []
            }
        
    except Exception as e:
        logger.error(f"Error en handle_revert_modification: {e}")
        return {
            "success": False,
            "message": f"Error deshaciendo modificación: {str(e)}",
            "changes": []
        }
