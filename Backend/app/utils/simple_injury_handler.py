#!/usr/bin/env python3
"""
Handler simplificado para lesiones - versión rápida y directa
"""

import json
import logging
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.utils.database_service import db_service

logger = logging.getLogger(__name__)

async def handle_modify_routine_injury_simple(
    user_id: int, 
    body_part: str, 
    injury_type: str, 
    severity: str,
    db: Session
) -> Dict[str, Any]:
    """
    Handler simplificado para lesiones - VERSIÓN RÁPIDA
    """
    try:
        logger.info(f"Procesando lesión de {body_part} para usuario {user_id}")
        
        # Obtener datos del usuario
        user_data = await db_service.get_user_complete_data(user_id, db)
        current_routine = user_data["current_routine"]
        
        # Validar estructura básica
        if not isinstance(current_routine, dict):
            return {
                "success": False,
                "message": "Estructura de rutina inválida.",
                "changes": []
            }
        
        # Asegurar que existe el campo exercises
        if "exercises" not in current_routine:
            current_routine["exercises"] = []
        
        changes = []
        
        # Ejercicios problemáticos por parte del cuerpo (simplificado)
        problem_exercises = {
            "cuadriceps": ["sentadillas", "zancadas", "prensa", "salto"],
            "hombro": ["press banca", "press militar", "fondos"],
            "rodilla": ["sentadillas", "zancadas", "prensa"],
            "espalda": ["peso muerto", "remo", "pull ups"]
        }
        
        # Alternativas seguras (simplificado)
        safe_exercises = {
            "cuadriceps": [
                {"name": "Leg press", "sets": 3, "reps": "12-15", "notes": "Alternativa segura"},
                {"name": "Curl femoral", "sets": 3, "reps": "12-15", "notes": "Sin impacto"}
            ],
            "hombro": [
                {"name": "Elevaciones laterales ligeras", "sets": 3, "reps": "12-15", "notes": "Peso ligero"},
                {"name": "Facepulls", "sets": 3, "reps": "15-20", "notes": "Rehabilitación"}
            ],
            "rodilla": [
                {"name": "Leg press", "sets": 3, "reps": "12-15", "notes": "Sin impacto"},
                {"name": "Extensiones", "sets": 3, "reps": "12-15", "notes": "Controlado"}
            ],
            "espalda": [
                {"name": "Remo con mancuernas", "sets": 3, "reps": "10-12", "notes": "Movimiento controlado"},
                {"name": "Lat pulldown", "sets": 3, "reps": "10-12", "notes": "Sin carga axial"}
            ]
        }
        
        # Filtrar ejercicios problemáticos
        exercises_to_remove = problem_exercises.get(body_part, [])
        current_exercises = current_routine.get("exercises", [])
        
        # Filtrar ejercicios (búsqueda simple)
        filtered_exercises = []
        for exercise in current_exercises:
            if isinstance(exercise, dict):
                exercise_name = exercise.get("name", "").lower()
                should_remove = any(problem in exercise_name for problem in exercises_to_remove)
                
                if should_remove:
                    changes.append(f"Eliminado: {exercise.get('name', 'ejercicio')}")
                else:
                    filtered_exercises.append(exercise)
            else:
                # Si no es un dict, mantenerlo
                filtered_exercises.append(exercise)
        
        # Añadir alternativas seguras - EVITAR DUPLICADOS
        new_safe_exercises = safe_exercises.get(body_part, [])
        existing_exercise_names = set()
        
        # Recopilar nombres de ejercicios existentes
        for exercise in filtered_exercises:
            if isinstance(exercise, dict):
                existing_exercise_names.add(exercise.get("name", "").lower())
            else:
                existing_exercise_names.add(str(exercise).lower())
        
        # Añadir solo ejercicios que no existen ya
        for safe_exercise in new_safe_exercises:
            exercise_name = safe_exercise.get("name", "").lower()
            if exercise_name not in existing_exercise_names:
                filtered_exercises.append(safe_exercise)
                changes.append(f"Añadido: {safe_exercise['name']}")
                existing_exercise_names.add(exercise_name)
            else:
                logger.info(f"⚠️ Ejercicio ya existe, omitiendo: {safe_exercise['name']}")
        
        # Actualizar rutina
        current_routine["exercises"] = filtered_exercises
        current_routine["version"] = "1.1.0"
        current_routine["updated_at"] = datetime.utcnow().isoformat()
        
        # Guardar cambios (sin validación compleja)
        await db_service.update_user_data(user_id, {
            "current_routine": current_routine
        }, db)
        
        return {
            "success": True,
            "message": f"Rutina adaptada para lesión de {body_part}. Se eliminaron ejercicios problemáticos y se añadieron alternativas seguras.",
            "changes": changes
        }
        
    except Exception as e:
        logger.error(f"Error en handler simplificado de lesión: {e}")
        return {
            "success": False,
            "message": f"Error adaptando rutina: {str(e)}",
            "changes": []
        }
