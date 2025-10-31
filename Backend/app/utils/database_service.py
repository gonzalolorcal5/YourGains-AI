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
            # VALIDACIÓN CRÍTICA: Asegurar que db no sea None
            if db is None:
                logger.error(f"❌ CRÍTICO: Sesión de BD es None para usuario {user_id}")
                raise ValueError("Sesión de base de datos no inicializada. Contacta soporte.")
            
            # UNA SOLA consulta optimizada con todos los campos
            result = db.query(Usuario).filter(Usuario.id == user_id).first()
            
            if not result:
                raise ValueError(f"Usuario {user_id} no encontrado")
            
            # Obtener el plan más reciente del usuario para datos físicos
            from app.models import Plan
            plan_actual = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.id.desc()).first()
            
            # Deserializar JSON de manera eficiente
            user_data = {
                "user_id": result.id,
                "email": result.email,
                "current_routine": deserialize_json(result.current_routine, "current_routine"),
                "current_diet": deserialize_json(result.current_diet, "current_diet"),
                "injuries": deserialize_json(result.injuries, "injuries"),
                "focus_areas": deserialize_json(result.focus_areas, "focus_areas"),
                "disliked_foods": deserialize_json(result.disliked_foods, "disliked_foods"),
                "modification_history": deserialize_json(result.modification_history, "modification_history"),
                "created_at": None,  # No disponible en el modelo actual
                "updated_at": None   # No disponible en el modelo actual
            }
            
            # Añadir datos físicos del plan más reciente (si existe)
            if plan_actual:
                # Limpiar peso (quitar "kg" si existe)
                peso_limpio = plan_actual.peso
                if isinstance(peso_limpio, str) and 'kg' in peso_limpio.lower():
                    peso_limpio = peso_limpio.lower().replace('kg', '').strip()
                
                user_data.update({
                    "peso": peso_limpio,
                    "altura": plan_actual.altura,
                    "edad": plan_actual.edad,
                    "sexo": plan_actual.sexo,
                    "nivel_actividad": plan_actual.nivel_actividad or 'moderado',
                    "objetivo_gym": plan_actual.objetivo_gym or 'ganar_musculo',
                    "objetivo_nutricional": plan_actual.objetivo_nutricional or 'mantenimiento'
                })
                logger.info(f"✅ Datos físicos obtenidos del Plan ID: {plan_actual.id}")
                logger.info(f"   Peso: {peso_limpio}, Altura: {plan_actual.altura}, Edad: {plan_actual.edad}")
                logger.info(f"   Sexo: {plan_actual.sexo}, Nivel: {plan_actual.nivel_actividad}")
                logger.info(f"   Objetivo Gym: {plan_actual.objetivo_gym or 'ganar_musculo'}")
                logger.info(f"   Objetivo Nutricional: {plan_actual.objetivo_nutricional or 'mantenimiento'}")
            else:
                # Si no hay plan, usar valores por defecto
                logger.warning(f"⚠️ No se encontró plan para usuario {user_id}, usando valores por defecto")
                user_data.update({
                    "peso": "75",
                    "altura": 175,
                    "edad": 25,
                    "sexo": "masculino",
                    "nivel_actividad": "moderado",
                    "objetivo_gym": "ganar_musculo",
                    "objetivo_nutricional": "mantenimiento"
                })
            
            return user_data
            
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
            # VALIDACIÓN CRÍTICA: Asegurar que db no sea None
            if db is None:
                logger.error(f"❌ CRÍTICO: Sesión de BD es None al actualizar usuario {user_id}")
                raise ValueError("Sesión de base de datos no inicializada. Contacta soporte.")
            
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
            
            # REFRESH CRÍTICO: Refrescar el objeto desde la BD para asegurar datos actualizados
            db.refresh(user)
            
            # Logging detallado para verificar qué se guardó
            if "current_diet" in data:
                try:
                    diet_data = deserialize_json(user.current_diet, "current_diet")
                    total_kcal = diet_data.get('total_kcal', 'NO EXISTE')
                    macros = diet_data.get('macros', {})
                    logger.info(f"✅ BD actualizada correctamente para usuario {user_id}")
                    logger.info(f"   ✅ current_diet guardado con total_kcal: {total_kcal}")
                    logger.info(f"   ✅ Macros guardados: P={macros.get('proteina', 0)}g, C={macros.get('carbohidratos', 0)}g, G={macros.get('grasas', 0)}g")
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo verificar current_diet después del guardado: {e}")
            else:
                logger.info(f"✅ Datos actualizados exitosamente para usuario {user_id}")
            
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
            # VALIDACIÓN CRÍTICA: Asegurar que db no sea None
            if db is None:
                logger.error(f"❌ CRÍTICO: Sesión de BD es None al añadir modificación para usuario {user_id}")
                raise ValueError("Sesión de base de datos no inicializada. Contacta soporte.")
            
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

    async def update_user_weight(self, user_id: int, new_weight: float, db: Session) -> bool:
        """
        Actualiza el peso del usuario en la base de datos.
        
        Args:
            user_id: ID del usuario
            new_weight: Nuevo peso en kg
            db: Sesión de SQLAlchemy
            
        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            # VALIDACIÓN CRÍTICA: Asegurar que db no sea None
            if db is None:
                logger.error(f"❌ CRÍTICO: Sesión de BD es None para usuario {user_id}")
                raise ValueError("Sesión de base de datos no inicializada. Contacta soporte.")
            
            # Buscar usuario
            user = db.query(Usuario).filter(Usuario.id == user_id).first()
            if not user:
                logger.error(f"❌ Usuario {user_id} no encontrado para actualizar peso")
                return False
            
            # Obtener peso anterior para logging
            old_weight = user.peso
            if old_weight is None:
                old_weight = 70.0  # Valor por defecto si no hay peso
            
            # Actualizar peso
            user.peso = new_weight
            user.updated_at = datetime.utcnow()
            
            # Commit de la transacción
            db.commit()
            db.refresh(user)
            
            logger.info(f"✅ Peso actualizado para usuario {user_id}: {old_weight}kg → {new_weight}kg")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error actualizando peso para usuario {user_id}: {str(e)}")
            db.rollback()
            return False

# Instancia global del servicio
db_service = DatabaseService()
