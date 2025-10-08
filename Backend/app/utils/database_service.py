#!/usr/bin/env python3
"""
Servicio centralizado de base de datos para optimización de rendimiento
Senior-level database service with proper connection management
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from pathlib import Path

from app.database import get_db
from app.models import Usuario
from app.utils.json_helpers import deserialize_json, serialize_json

logger = logging.getLogger(__name__)

class DatabaseService:
    """
    Servicio centralizado para operaciones de base de datos
    Optimizado para rendimiento y consistencia
    """
    
    async def get_user_complete_data(self, user_id: int, db: Session) -> Dict[str, Any]:
        """
        Obtiene TODOS los datos del usuario en UNA sola consulta optimizada
        
        Args:
            user_id: ID del usuario
            db: Sesión de SQLAlchemy
            
        Returns:
            Diccionario completo con todos los datos del usuario
        """
        try:
            # UNA SOLA consulta optimizada con todos los campos
            result = db.query(Usuario).filter(Usuario.id == user_id).first()
            
            if not result:
                raise ValueError(f"Usuario {user_id} no encontrado")
            
            # Deserializar JSON de manera eficiente
            return {
                "user_id": result.id,
                "email": result.email,
                "sexo": "hombre",  # Default, se puede obtener de planes si necesario
                "current_routine": deserialize_json(result.current_routine, "current_routine"),
                "current_diet": deserialize_json(result.current_diet, "current_diet"),
                "injuries": deserialize_json(result.injuries, "injuries"),
                "focus_areas": deserialize_json(result.focus_areas, "focus_areas"),
                "disliked_foods": deserialize_json(result.disliked_foods, "disliked_foods"),
                "modification_history": deserialize_json(result.modification_history, "modification_history"),
                "created_at": None,  # No disponible en el modelo actual
                "updated_at": None   # No disponible en el modelo actual
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo datos completos del usuario {user_id}: {e}")
            raise ValueError(f"Error obteniendo datos del usuario: {e}")
    
    async def update_user_data(
        self, 
        user_id: int, 
        data: Dict[str, Any], 
        db: Session
    ) -> bool:
        """
        Actualiza los datos del usuario de manera optimizada
        
        Args:
            user_id: ID del usuario
            data: Datos a actualizar
            db: Sesión de SQLAlchemy
            
        Returns:
            True si se actualizó exitosamente
        """
        try:
            # Obtener usuario
            user = db.query(Usuario).filter(Usuario.id == user_id).first()
            
            if not user:
                raise ValueError(f"Usuario {user_id} no encontrado")
            
            # Actualizar campos de manera eficiente
            if "current_routine" in data:
                user.current_routine = serialize_json(data["current_routine"], "current_routine")
                
            if "current_diet" in data:
                user.current_diet = serialize_json(data["current_diet"], "current_diet")
                
            if "injuries" in data:
                user.injuries = serialize_json(data["injuries"], "injuries")
                
            if "focus_areas" in data:
                user.focus_areas = serialize_json(data["focus_areas"], "focus_areas")
                
            if "disliked_foods" in data:
                user.disliked_foods = serialize_json(data["disliked_foods"], "disliked_foods")
                
            if "modification_history" in data:
                user.modification_history = serialize_json(data["modification_history"], "modification_history")
            
            # Actualizar timestamp (no disponible en el modelo actual)
            # user.updated_at = datetime.utcnow()
            
            # Commit en UNA sola transacción
            db.commit()
            
            logger.info(f"Datos actualizados exitosamente para usuario {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error actualizando datos del usuario {user_id}: {e}")
            db.rollback()
            raise ValueError(f"Error actualizando datos: {e}")
    
    async def add_modification_record(
        self,
        user_id: int,
        modification_type: str,
        modification_data: Dict[str, Any],
        description: str,
        db: Session
    ) -> bool:
        """
        Añade un registro al historial de modificaciones de manera eficiente
        
        Args:
            user_id: ID del usuario
            modification_type: Tipo de modificación
            modification_data: Datos de la modificación
            description: Descripción de la modificación
            db: Sesión de SQLAlchemy
            
        Returns:
            True si se añadió exitosamente
        """
        try:
            # Obtener usuario
            user = db.query(Usuario).filter(Usuario.id == user_id).first()
            
            if not user:
                raise ValueError(f"Usuario {user_id} no encontrado")
            
            # Obtener historial actual
            current_history = deserialize_json(user.modification_history, "modification_history")
            
            # Crear nuevo registro
            new_record = {
                "id": len(current_history) + 1,
                "type": modification_type,
                "data": modification_data,
                "description": description,
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id
            }
            
            # Añadir al historial
            current_history.append(new_record)
            
            # Mantener solo los últimos 50 registros para optimizar
            if len(current_history) > 50:
                current_history = current_history[-50:]
            
            # Actualizar en base de datos
            user.modification_history = serialize_json(current_history, "modification_history")
            # user.updated_at = datetime.utcnow()  # No disponible en el modelo actual
            
            db.commit()
            
            logger.info(f"Registro de modificación añadido para usuario {user_id}: {modification_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error añadiendo registro de modificación para usuario {user_id}: {e}")
            db.rollback()
            raise ValueError(f"Error añadiendo registro: {e}")
    
    async def get_last_modification(self, user_id: int, db: Session) -> Optional[Dict[str, Any]]:
        """
        Obtiene la última modificación del usuario
        
        Args:
            user_id: ID del usuario
            db: Sesión de SQLAlchemy
            
        Returns:
            Última modificación o None si no hay
        """
        try:
            user = db.query(Usuario).filter(Usuario.id == user_id).first()
            
            if not user:
                return None
            
            history = deserialize_json(user.modification_history, "modification_history")
            
            if not history:
                return None
            
            return history[-1]  # Último registro
            
        except Exception as e:
            logger.error(f"Error obteniendo última modificación para usuario {user_id}: {e}")
            return None
    
    async def remove_last_modification(self, user_id: int, db: Session) -> bool:
        """
        Elimina la última modificación del historial
        
        Args:
            user_id: ID del usuario
            db: Sesión de SQLAlchemy
            
        Returns:
            True si se eliminó exitosamente
        """
        try:
            user = db.query(Usuario).filter(Usuario.id == user_id).first()
            
            if not user:
                raise ValueError(f"Usuario {user_id} no encontrado")
            
            history = deserialize_json(user.modification_history, "modification_history")
            
            if not history:
                return False
            
            # Eliminar último registro
            history.pop()
            
            # Actualizar en base de datos
            user.modification_history = serialize_json(history, "modification_history")
            # user.updated_at = datetime.utcnow()  # No disponible en el modelo actual
            
            db.commit()
            
            logger.info(f"Última modificación eliminada para usuario {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error eliminando última modificación para usuario {user_id}: {e}")
            db.rollback()
            raise ValueError(f"Error eliminando modificación: {e}")

# Instancia global del servicio
db_service = DatabaseService()
