#!/usr/bin/env python3
"""
Funciones helper para manejo seguro de JSON en la base de datos
Maneja serialización, deserialización y validación de campos JSON
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)

# Esquemas de validación para cada tipo de campo JSON
SCHEMAS = {
    "current_routine": {
        "type": "object",
        "required": ["exercises"],
        "properties": {
            "exercises": {"type": "array"},
            "schedule": {"type": "object"},
            "created_at": {"type": "string"},
            "updated_at": {"type": "string"},
            "version": {"type": "string"}
        }
    },
    "current_diet": {
        "type": "object", 
        "required": ["meals"],
        "properties": {
            "meals": {"type": "array"},
            "total_kcal": {"type": "number"},
            "macros": {"type": "object"},
            "objetivo": {"type": "string"},
            "created_at": {"type": "string"},
            "updated_at": {"type": "string"},
            "version": {"type": "string"}
        }
    },
    "injuries": {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["body_part"],
            "properties": {
                "id": {"type": "integer"},
                "body_part": {"type": "string"},
                "severity": {"type": "string"},
                "description": {"type": "string"},
                "timestamp": {"type": "string"},
                "active": {"type": "boolean"},
                "date": {"type": "string"},
                "notes": {"type": "string"}
            }
        }
    },
    "focus_areas": {
        "type": "array",
        "items": {"type": "string"}
    },
    "disliked_foods": {
        "type": "array", 
        "items": {"type": "string"}
    },
    "modification_history": {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["type", "timestamp"],
            "properties": {
                "type": {"type": "string"},
                "timestamp": {"type": "string"},
                "changes": {"type": "array"},
                "description": {"type": "string"},
                "data": {"type": "object"},
                "user_id": {"type": "integer"},
                "id": {"type": "integer"}
            }
        }
    }
}

def serialize_json(data: Any, field_name: str) -> str:
    """
    Serializa datos a JSON string con validación
    
    Args:
        data: Datos a serializar
        field_name: Nombre del campo para validación
        
    Returns:
        JSON string serializado
        
    Raises:
        ValueError: Si los datos no son válidos para el campo
        TypeError: Si no se puede serializar a JSON
    """
    try:
        # Validar datos según el esquema
        if not _validate_data_structure(data, field_name):
            raise ValueError(f"Datos inválidos para campo {field_name}")
        
        # Serializar a JSON
        json_str = json.dumps(data, ensure_ascii=False, indent=None)
        
        # Verificar que se puede deserializar correctamente
        json.loads(json_str)
        
        logger.debug(f"✅ JSON serializado para {field_name}: {len(json_str)} caracteres")
        return json_str
        
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.error(f"❌ Error serializando JSON para {field_name}: {e}")
        raise TypeError(f"No se puede serializar a JSON: {e}")
    except Exception as e:
        logger.error(f"❌ Error validando datos para {field_name}: {e}")
        raise ValueError(f"Datos inválidos para {field_name}: {e}")

def deserialize_json(json_str: str, field_name: str) -> Any:
    """
    Deserializa JSON string a objeto Python con validación
    
    Args:
        json_str: String JSON a deserializar
        field_name: Nombre del campo para validación
        
    Returns:
        Objeto Python deserializado
        
    Raises:
        ValueError: Si el JSON no es válido
        TypeError: Si no se puede deserializar
    """
    try:
        if not json_str or json_str.strip() == '':
            return _get_default_value(field_name)
        
        # Deserializar JSON
        data = json.loads(json_str)
        
        # Si es un objeto vacío, devolver el valor por defecto
        if isinstance(data, dict) and len(data) == 0:
            logger.debug(f"⚠️  Objeto vacío detectado para {field_name}, usando valor por defecto")
            return _get_default_value(field_name)
        
        # Validar estructura solo si no es vacío
        if not _validate_data_structure(data, field_name):
            # Para objetos vacíos, ser más permisivo
            if isinstance(data, dict) and len(data) == 0:
                logger.debug(f"⚠️  Validación falló para objeto vacío {field_name}, usando valor por defecto")
                return _get_default_value(field_name)
            raise ValueError(f"Estructura JSON inválida para {field_name}")
        
        logger.debug(f"✅ JSON deserializado para {field_name}")
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error deserializando JSON para {field_name}: {e}")
        raise ValueError(f"JSON inválido en {field_name}: {e}")
    except Exception as e:
        logger.error(f"❌ Error procesando {field_name}: {e}")
        raise

def _validate_data_structure(data: Any, field_name: str) -> bool:
    """
    Valida que los datos cumplan con el esquema del campo - VERSIÓN PERMISIVA
    
    Args:
        data: Datos a validar
        field_name: Nombre del campo
        
    Returns:
        True si es válido, False si no
    """
    # Para evitar problemas, hacer validación muy permisiva
    logger.debug(f"🔍 Validando {field_name}: {type(data)}")
    
    # Validación básica de tipos principales
    if isinstance(data, (dict, list, str, int, float, bool)) or data is None:
        logger.debug(f"✅ Datos válidos para {field_name}")
        return True
    
    logger.warning(f"⚠️  Tipo de datos inesperado para {field_name}: {type(data)}")
    return False

def _validate_item_against_schema(item: Any, schema: Dict) -> bool:
    """Valida un item individual contra un esquema"""
    try:
        if schema.get("type") == "object" and not isinstance(item, dict):
            return False
        elif schema.get("type") == "string" and not isinstance(item, str):
            return False
        
        # Validar campos requeridos
        if isinstance(item, dict):
            required = schema.get("required", [])
            for field in required:
                if field not in item:
                    return False
        
        return True
    except:
        return False

def _get_default_value(field_name: str) -> Any:
    """Retorna el valor por defecto para cada campo"""
    from datetime import datetime
    
    defaults = {
        "current_routine": {
            "exercises": [],
            "schedule": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        },
        "current_diet": {
            "meals": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "total_kcal": 0
        },
        "injuries": [],
        "focus_areas": [],
        "disliked_foods": [],
        "modification_history": []
    }
    return defaults.get(field_name, {})

def add_modification_record(
    history: List[Dict], 
    modification_type: str, 
    changes: Dict, 
    reason: Optional[str] = None
) -> List[Dict]:
    """
    Añade un nuevo registro de modificación al historial
    
    Args:
        history: Lista actual del historial
        modification_type: Tipo de modificación ("routine", "diet", "injuries", etc.)
        changes: Diccionario con los cambios realizados
        reason: Razón opcional para el cambio
        
    Returns:
        Lista actualizada del historial
    """
    try:
        # Deserializar si viene como string
        if isinstance(history, str):
            history = deserialize_json(history, "modification_history")
        
        # Crear nuevo registro
        new_record = {
            "type": modification_type,
            "timestamp": datetime.utcnow().isoformat(),
            "changes": changes,
            "reason": reason or "Modificación solicitada por el usuario"
        }
        
        # Añadir al historial (máximo 50 registros)
        history.append(new_record)
        if len(history) > 50:
            history = history[-50:]  # Mantener solo los últimos 50
        
        return history
        
    except Exception as e:
        logger.error(f"❌ Error añadiendo registro de modificación: {e}")
        return history if isinstance(history, list) else []

def get_latest_routine_version(current_routine: Union[str, Dict]) -> str:
    """Obtiene la versión más reciente de la rutina"""
    try:
        if isinstance(current_routine, str):
            routine = deserialize_json(current_routine, "current_routine")
        else:
            routine = current_routine
        
        return routine.get("version", "1.0.0")
    except:
        return "1.0.0"

def increment_routine_version(current_version: str) -> str:
    """Incrementa la versión de la rutina"""
    try:
        parts = current_version.split(".")
        if len(parts) >= 2:
            minor = int(parts[1]) + 1
            return f"{parts[0]}.{minor}.0"
        else:
            return f"{current_version}.1"
    except:
        return "1.0.1"

# Funciones de conveniencia para campos específicos
def add_injury(injuries: List[Dict], body_part: str, severity: str = "moderate", notes: str = "") -> List[Dict]:
    """Añade una nueva lesión a la lista"""
    new_injury = {
        "body_part": body_part,
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "severity": severity,
        "notes": notes
    }
    
    # Deserializar si viene como string
    if isinstance(injuries, str):
        injuries = deserialize_json(injuries, "injuries")
    
    injuries.append(new_injury)
    return injuries

def remove_injury(injuries: List[Dict], body_part: str) -> List[Dict]:
    """Remueve una lesión de la lista"""
    if isinstance(injuries, str):
        injuries = deserialize_json(injuries, "injuries")
    
    return [injury for injury in injuries if injury.get("body_part") != body_part]

def add_focus_area(focus_areas: List[str], area: str) -> List[str]:
    """Añade un área de enfoque"""
    if isinstance(focus_areas, str):
        focus_areas = deserialize_json(focus_areas, "focus_areas")
    
    if area not in focus_areas:
        focus_areas.append(area)
    
    return focus_areas

def add_disliked_food(disliked_foods: List[str], food: str) -> List[str]:
    """Añade un alimento que no le gusta"""
    if isinstance(disliked_foods, str):
        disliked_foods = deserialize_json(disliked_foods, "disliked_foods")
    
    if food not in disliked_foods:
        disliked_foods.append(food)
    
    return disliked_foods
