#!/usr/bin/env python3
"""
Handlers optimizados para funciones de OpenAI
Versión FINAL CORREGIDA - Todas las funciones implementadas
"""

import json
import logging
import re
import asyncio
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.utils.database_service import db_service
from app.utils.gpt import generar_plan_personalizado
from app.utils.routine_templates import get_generic_plan
from app.utils.json_helpers import serialize_json

logger = logging.getLogger(__name__)

# CONFIGURACIÓN
GPT_TIMEOUT_SECONDS = 30.0  # Timeout configurable para GPT (30s es suficiente para respuesta de GPT)

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
    Modifica la rutina para adaptarla a una lesión específica - VERSIÓN CON GPT
    🔧 NUEVO: Ahora GPT genera una rutina completamente nueva evitando la lesión
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
        
        # 🔧 FIX: Guardar versión ANTES de modificar
        previous_routine = json.loads(json.dumps(current_routine))
        old_routine_version = current_routine.get("version", "1.0.0")
        
        logger.info(f"🏥 GENERANDO RUTINA CON GPT PARA LESIÓN:")
        logger.info(f"   Parte del cuerpo: {body_part}")
        logger.info(f"   Tipo de lesión: {injury_type}")
        logger.info(f"   Severidad: {severity}")
        
        # Obtener datos del Plan para pasar a GPT
        from app.models import Plan
        plan_actual = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.id.desc()).first()
        
        if not plan_actual:
            logger.error(f"❌ No se encontró Plan para usuario {user_id}")
            return {
                "success": False,
                "message": "No se encontró plan del usuario. Completa el onboarding primero.",
                "changes": []
            }
        
        # Preparar datos para GPT con información de la lesión
        datos_gpt = {
            'altura': plan_actual.altura or 175,
            'peso': float(plan_actual.peso) if plan_actual.peso else 75.0,
            'edad': plan_actual.edad or 25,
            'sexo': plan_actual.sexo or 'masculino',
            'objetivo': plan_actual.objetivo_gym or (plan_actual.objetivo or 'ganar_musculo'),
            'gym_goal': plan_actual.objetivo_gym or 'ganar_musculo',
            'nutrition_goal': plan_actual.objetivo_nutricional or (plan_actual.objetivo_dieta or 'mantenimiento'),
            'experiencia': plan_actual.experiencia or 'principiante',
            'materiales': plan_actual.materiales or 'gym_completo',
            'tipo_cuerpo': plan_actual.tipo_cuerpo or 'mesomorfo',
            'alergias': plan_actual.alergias or 'Ninguna',
            'restricciones': plan_actual.restricciones_dieta or 'Ninguna',
            # 🔧 NUEVO: Información específica de la lesión
            'lesiones': f"{body_part} ({injury_type}, severidad: {severity}) - EVITAR ejercicios que afecten esta parte",
            'nivel_actividad': plan_actual.nivel_actividad or 'moderado',
            'training_frequency': 4,
            'training_days': ['lunes', 'martes', 'jueves', 'viernes']
        }
        
        # Llamar a GPT para generar rutina nueva con lesión
        from app.utils.gpt import generar_plan_personalizado
        
        exercises_nuevos = None  # Variable para controlar si GPT funcionó
        
        try:
            logger.info(f"🤖 Generando rutina con GPT considerando lesión de {body_part}...")
            plan_generado = await generar_plan_personalizado(datos_gpt)
            
            # Extraer solo la rutina (no necesitamos regenerar dieta)
            rutina_gpt = plan_generado.get("rutina", {})
            dias_rutina = rutina_gpt.get("dias", [])
            
            if not dias_rutina:
                raise ValueError("GPT no generó rutina válida")
            
            # Convertir formato de "dias" a "exercises" (formato que usa current_routine)
            exercises_nuevos = []
            for dia in dias_rutina:
                nombre_dia = dia.get("dia", "")
                grupos_musculares = dia.get("grupos_musculares", "")
                ejercicios_dia = dia.get("ejercicios", [])
                
                for ejercicio in ejercicios_dia:
                    exercises_nuevos.append({
                        "name": ejercicio.get("nombre", ""),
                        "sets": ejercicio.get("series", 3),
                        "reps": ejercicio.get("repeticiones", "10-12"),
                        "weight": "moderado",
                        "day": nombre_dia
                    })
            
            logger.info(f"✅ Rutina generada con GPT: {len(exercises_nuevos)} ejercicios")
            
            # Preparar cambios para el registro
            changes = [
                f"Rutina regenerada con GPT evitando ejercicios para {body_part}",
                f"Total ejercicios: {len(exercises_nuevos)}"
            ]
            
        except Exception as e_gpt:
            logger.error(f"❌ Error generando rutina con GPT: {e_gpt}")
            logger.warning(f"⚠️ Fallando a método de filtrado tradicional...")
            exercises_nuevos = None  # GPT falló, usar fallback
        
        # FALLBACK: Si GPT falló, usar método tradicional de filtrado
        if exercises_nuevos is None:
            # Diccionarios optimizados de ejercicios
            exercises_to_remove = {
                "hombro": [
                "Press banca", "Press inclinado", "Press declinado", "Press militar", "Press con mancuernas",
                "Press inclinado con mancuernas", "Press declinado con mancuernas", "Press banca con mancuernas",
                "Remo al cuello", "Elevaciones laterales", "Elevaciones frontales", "Fondos",
                "Aperturas con mancuernas", "Aperturas en máquina", "Cruce de cables", "Pullover"
            ],
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
                nombre_lower = nombre_ejercicio.lower()
                
                # Detección mejorada: buscar palabras clave y coincidencias exactas
                should_remove = False
                
                # Coincidencia exacta o parcial en la lista
                should_remove = any(avoid.lower() in nombre_lower for avoid in exercises_to_remove_list)
                
                # Detección adicional por palabras clave específicas para hombro
                if body_part == "hombro" and not should_remove:
                    # Palabras clave que indican ejercicios que afectan el hombro
                    keywords_hombro = ["press", "apertura", "fondo", "elevación", "remo al cuello"]
                    if any(keyword in nombre_lower for keyword in keywords_hombro):
                        # Excluir ejercicios seguros para hombro
                        safe_keywords = ["curl", "sentadilla", "prensa", "remo con", "lat pulldown", "jalón", "dominada", "remo invertido"]
                        if not any(safe in nombre_lower for safe in safe_keywords):
                            should_remove = True
                            logger.info(f"⚠️ Ejercicio detectado por palabra clave '{nombre_ejercicio}' para lesión de hombro")
                
                if should_remove:
                    ejercicios_eliminados.append(nombre_ejercicio)
                    changes.append(f"Eliminado: {nombre_ejercicio}")
                else:
                    ejercicios_filtrados.append(ejercicio)
            
            # Añadir alternativas si se eliminaron ejercicios (solo en fallback)
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
        
        # Actualizar rutina con el método que funcionó
        if exercises_nuevos is not None:
            # GPT funcionó: usar rutina generada por GPT
            current_routine["exercises"] = exercises_nuevos
        else:
            # GPT falló: usar rutina filtrada
            current_routine["exercises"] = ejercicios_filtrados
        
        current_routine["version"] = increment_routine_version(old_routine_version)
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
        logger.error(f"Error en handle_modify_routine_injury: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error adaptando rutina para lesión: {str(e)}",
            "changes": []
        }

def ajustar_cantidad_alimento(alimento: str, factor: float) -> str:
    """
    Ajusta la cantidad de un alimento individual proporcionalmente.
    
    Ejemplos:
        "300ml leche semidesnatada - 150kcal" → "360ml leche semidesnatada - 180kcal" (factor 1.2)
        "40g avena - 150kcal" → "48g avena - 180kcal" (factor 1.2)
        "1 plátano - 100kcal" → "1 plátano - 120kcal" (unidades no se multiplican, solo kcal)
    """
    if not isinstance(alimento, str):
        return str(alimento)
    
    # Patrón para detectar: CANTIDAD + UNIDAD + RESTO + kcal opcional
    patron_cantidad = r'^(\d+(?:\.\d+)?)\s*(ml|g|kg)\s+(.+?)(?:\s+-\s+(\d+)kcal)?$'
    match = re.match(patron_cantidad, alimento, re.IGNORECASE)
    
    if match:
        cantidad_vieja = float(match.group(1))
        unidad = match.group(2)
        resto = match.group(3)
        kcal_viejas = int(match.group(4)) if match.group(4) else None
        
        # Ajustar cantidad (mínimo 1 para evitar 0)
        cantidad_nueva = max(int(round(cantidad_vieja * factor)), 1)
        
        # Ajustar kcal si existen
        if kcal_viejas:
            kcal_nuevas = int(round(kcal_viejas * factor))
            return f"{cantidad_nueva}{unidad} {resto} - {kcal_nuevas}kcal"
        else:
            return f"{cantidad_nueva}{unidad} {resto}"
    
    # Si no tiene cantidad medible (ej: "1 plátano - 100kcal"), solo ajustar kcal
    patron_kcal = r'^(.+?)\s+-\s+(\d+)kcal$'
    match_kcal = re.match(patron_kcal, alimento, re.IGNORECASE)
    
    if match_kcal:
        descripcion = match_kcal.group(1)
        kcal_viejas = int(match_kcal.group(2))
        kcal_nuevas = int(round(kcal_viejas * factor))
        return f"{descripcion} - {kcal_nuevas}kcal"
    
    # Si no tiene formato reconocible, devolver sin cambios
    logger.debug(f"⚠️ Alimento sin formato reconocible: {alimento}")  # 🔧 FIX
    return alimento


def ajustar_cantidades_dieta_proporcional(
    dieta_actual: Dict,
    nuevas_calorias_totales: int,
    nuevos_macros: Dict[str, int]
) -> List[Dict]:
    """
    Ajusta las cantidades de alimentos proporcionalmente según nuevas calorías objetivo.
    
    Args:
        dieta_actual: Dieta actual con formato {"meals": [...]} o {"comidas": [...]}
        nuevas_calorias_totales: Nuevo objetivo calórico total
        nuevos_macros: {"proteina": X, "carbohidratos": Y, "grasas": Z}
    
    Returns:
        Lista de comidas con cantidades ajustadas
    
    Raises:
        ValueError: Si la dieta actual está vacía o no tiene formato válido
    """
    
    # VALIDACIÓN 1: Verificar que dieta_actual existe y tiene formato correcto
    if not dieta_actual or not isinstance(dieta_actual, dict):
        raise ValueError("dieta_actual debe ser un diccionario válido")
    
    # VALIDACIÓN 2: Verificar que tiene meals/comidas
    meals_actuales = dieta_actual.get("meals") or dieta_actual.get("comidas") or []
    if not meals_actuales or len(meals_actuales) == 0:
        raise ValueError("dieta_actual no tiene comidas (meals está vacío)")
    
    # VALIDACIÓN 3: Verificar que tiene calorías actuales válidas
    calorias_actuales = dieta_actual.get("total_kcal") or dieta_actual.get("total_calorias")
    if not calorias_actuales or calorias_actuales <= 0:
        # Calcular desde las comidas si es posible
        calorias_calculadas = sum(
            int(comida.get("kcal", 0) or 0) 
            for comida in meals_actuales
        )
        if calorias_calculadas > 0:
            calorias_actuales = calorias_calculadas
        else:
            logger.warning(f"⚠️ total_kcal no válido, usando 2000 por defecto")
            calorias_actuales = 2000
    
    # 1. Calcular factor de escala basado en calorías
    factor_escala = nuevas_calorias_totales / calorias_actuales
    
    logger.info(f"📊 Ajustando cantidades de dieta proporcionalmente:")
    logger.info(f"   Calorías actuales: {calorias_actuales}")
    logger.info(f"   Calorías objetivo: {nuevas_calorias_totales}")
    logger.info(f"   Factor de escala: {factor_escala:.2f}x")
    
    # 2. Ajustar cada comida
    meals_ajustadas = []
    
    for comida in meals_actuales:
        # Ajustar calorías de la comida
        kcal_vieja = comida.get("kcal", 0)
        if isinstance(kcal_vieja, str):
            try:
                kcal_vieja = int(float(kcal_vieja))
            except:
                kcal_vieja = 0
        
        kcal_nueva = int(round(kcal_vieja * factor_escala))
        
        # 🔧 FIX: Unificar nombres de macros (TODO PLURAL Y COMPLETO)
        macros_viejos = comida.get("macros", {})
        macros_nuevos = {
            "proteinas": int(round(macros_viejos.get("proteinas", macros_viejos.get("proteina", 0)) * factor_escala)),
            "carbohidratos": int(round(macros_viejos.get("carbohidratos", macros_viejos.get("hidratos", 0)) * factor_escala)),
            "grasas": int(round(macros_viejos.get("grasas", 0) * factor_escala))
        }
        
        # Ajustar alimentos (pueden ser strings o objetos)
        alimentos_ajustados = []
        alimentos_originales = comida.get("alimentos", [])
        
        for alimento in alimentos_originales:
            if isinstance(alimento, str):
                alimento_ajustado = ajustar_cantidad_alimento(alimento, factor_escala)
            elif isinstance(alimento, dict):
                # Si es objeto, intentar ajustar campos relevantes
                alimento_ajustado = alimento.copy()
                if "cantidad" in alimento_ajustado:
                    alimento_ajustado["cantidad"] = ajustar_cantidad_alimento(
                        alimento_ajustado["cantidad"], factor_escala
                    )
                if "kcal" in alimento_ajustado:
                    alimento_ajustado["kcal"] = int(round(alimento_ajustado.get("kcal", 0) * factor_escala))
            else:
                alimento_ajustado = alimento
            
            alimentos_ajustados.append(alimento_ajustado)
        
        # Ajustar alternativas (también pueden ser strings o objetos)
        alternativas_ajustadas = []
        alternativas_originales = comida.get("alternativas", [])
        
        for alternativa in alternativas_originales:
            if isinstance(alternativa, str):
                alternativa_ajustada = ajustar_cantidad_alimento(alternativa, factor_escala)
            else:
                alternativa_ajustada = alternativa
            alternativas_ajustadas.append(alternativa_ajustada)
        
        # Crear comida ajustada con formato consistente
        comida_ajustada = {
            "nombre": comida.get("nombre", ""),
            "kcal": kcal_nueva,
            "macros": macros_nuevos,
            "alimentos": alimentos_ajustados,
            "alternativas": alternativas_ajustadas
        }
        meals_ajustadas.append(comida_ajustada)
        
        logger.info(f"   ✅ {comida.get('nombre', 'Comida')}: {kcal_vieja}kcal → {kcal_nueva}kcal")
    
    logger.info(f"✅ Cantidades ajustadas: {len(meals_ajustadas)} comidas")
    return meals_ajustadas


async def handle_recalculate_macros(
    user_id: int,
    weight_change_kg: float = None,
    goal: str = None,
    calorie_adjustment: int = None,
    is_incremental: bool = None,
    adjustment_type: str = None,
    target_calories: int = None,
    db: Session = None
) -> Dict[str, Any]:
    """
    Recalcula los macronutrientes de la dieta - VERSIÓN FINAL CORREGIDA
    
    Esta es la función CRÍTICA para el dashboard. Debe:
    1. Recalcular macros según nuevo peso/objetivo
    2. Regenerar dieta con cantidades ajustadas
    3. Mostrar correctamente en frontend con estructura consistente
    """
    
    logger.info(f"{'='*60}")
    logger.info(f"🔧 RECALCULANDO MACROS PARA USUARIO {user_id}")
    logger.info(f"{'='*60}")
    logger.info(f"📊 Parámetros recibidos:")
    logger.info(f"   weight_change_kg: {weight_change_kg}")
    logger.info(f"   goal: {goal}")
    logger.info(f"   calorie_adjustment: {calorie_adjustment}")
    logger.info(f"   is_incremental: {is_incremental}")
    logger.info(f"   target_calories: {target_calories}")
    
    # Validar que al menos un parámetro esté presente
    if all(param is None for param in [weight_change_kg, goal, calorie_adjustment, target_calories]):
        logger.error("❌ No se proporcionó ningún parámetro para modificar")
        return {
            "success": False,
            "message": "Debes especificar al menos un cambio (peso, objetivo o calorías)"
        }
    
    try:
        # Obtener datos del usuario
        user_data = await db_service.get_user_complete_data(user_id, db)
        current_diet = user_data.get("current_diet")
        
        # Validar estructura de dieta - si no existe o no es dict, inicializar
        if not isinstance(current_diet, dict):
            logger.warning("⚠️ current_diet no es dict, inicializando vacío")
            current_diet = {}
        
        from app.models import Plan, Usuario
        
        # Obtener usuario para verificar si es premium
        usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not usuario:
            logger.error(f"❌ No se encontró usuario {user_id}")
            return {
                "success": False,
                "message": "Usuario no encontrado"
            }
        
        # Verificar si es premium
        is_premium = bool(usuario.is_premium) or (usuario.plan_type == "PREMIUM")
        logger.info(f"💎 Usuario premium: {is_premium}")
        
        # Obtener plan actual
        current_plan = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.id.desc()).first()
        
        if not current_plan:
            logger.error(f"❌ No se encontró plan para usuario {user_id}")
            return {
                "success": False,
                "message": "No se encontró tu plan actual"
            }
        
        # 🔧 FIX: VALIDAR DATOS BÁSICOS DEL USUARIO
        if not current_plan.peso or not current_plan.altura or not current_plan.edad:
            logger.error(f"❌ Perfil incompleto para usuario {user_id}")
            return {
                "success": False,
                "message": "Perfil incompleto. Por favor completa tu peso, altura y edad en configuración."
            }
        
        # Extraer peso actual con validación
        try:
            peso_actual = current_plan.peso
            if isinstance(peso_actual, str):
                peso_actual = float(peso_actual.replace("kg", "").strip())
            else:
                peso_actual = float(peso_actual)
        except (ValueError, TypeError) as e:
            logger.error(f"❌ Peso inválido: {current_plan.peso}")
            return {
                "success": False,
                "message": "Peso inválido en perfil. Por favor actualízalo."
            }
        
        logger.info(f"📊 Peso actual en BD: {peso_actual}kg")
        
        # Calcular nuevo peso si hay cambio
        nuevo_peso = peso_actual
        if weight_change_kg is not None and weight_change_kg != 0:
            nuevo_peso = peso_actual + float(weight_change_kg)
            logger.info(f"⚖️ Cambio de peso: {peso_actual}kg → {nuevo_peso}kg")
            
            # Actualizar peso en BD
            current_plan.peso = str(nuevo_peso)
            db.commit()
            logger.info(f"✅ Peso actualizado en BD: {nuevo_peso}kg")
        
        # Obtener objetivo actual
        objetivo_actual = current_plan.objetivo_nutricional or "mantenimiento"
        
        # Determinar nuevo objetivo
        nuevo_objetivo = objetivo_actual
        if goal is not None:
            goal_map = {
                'definicion': 'definicion',
                'definición': 'definicion',
                'volumen': 'volumen',
                'mantenimiento': 'mantenimiento',
                'mantener': 'mantenimiento',
                'perder': 'definicion',
                'ganar': 'volumen'
            }
            nuevo_objetivo = goal_map.get(goal.lower(), goal.lower())
            logger.info(f"🎯 Cambio de objetivo: {objetivo_actual} → {nuevo_objetivo}")
            
            # Actualizar objetivo en BD
            current_plan.objetivo_nutricional = nuevo_objetivo
            db.commit()
            logger.info(f"✅ Objetivo actualizado en BD: {nuevo_objetivo}")
        
        # Recalcular TMB y TDEE con nuevo peso
        from app.utils.nutrition_calculator import calculate_tmb, calculate_tdee
        
        try:
            altura_cm = int(current_plan.altura)
            edad = int(current_plan.edad)
            sexo = current_plan.sexo
        except (ValueError, TypeError) as e:
            logger.error(f"❌ Datos de perfil inválidos: altura={current_plan.altura}, edad={current_plan.edad}")
            return {
                "success": False,
                "message": "Datos de perfil inválidos. Por favor verifica tu altura y edad."
            }
        
        nivel_actividad = current_plan.nivel_actividad or 'moderado'
        
        tmb = calculate_tmb(float(nuevo_peso), altura_cm, edad, sexo)
        tdee = calculate_tdee(tmb, nivel_actividad)
        
        logger.info(f"📊 TMB: {tmb:.0f} kcal/día")
        logger.info(f"📊 TDEE: {tdee:.0f} kcal/día")
        
        # Calcular target_calories
        AJUSTES_OBJETIVO = {
            'definicion': -300,
            'volumen': 300,
            'mantenimiento': 0
        }
        
        # Prioridad 1: target_calories absolutas
        if target_calories is not None:
            target_calories = int(target_calories)
            logger.info(f"🎯 Usando target_calories absoluto: {target_calories} kcal")
        # Prioridad 2: calorie_adjustment
        elif calorie_adjustment is not None:
            if is_incremental:
                current_cal = current_diet.get("total_kcal", tdee)
                target_calories = current_cal + calorie_adjustment
                logger.info(f"🎯 Ajuste incremental: {current_cal:.0f} + {calorie_adjustment:+d} = {target_calories:.0f} kcal")
            else:
                target_calories = tdee + calorie_adjustment
                logger.info(f"🎯 Ajuste absoluto: TDEE + {calorie_adjustment:+d} = {target_calories:.0f} kcal")
        else:
            # Usar ajuste estándar del objetivo
            ajuste = AJUSTES_OBJETIVO.get(nuevo_objetivo, 0)
            target_calories = tdee + ajuste
            logger.info(f"🎯 Ajuste por objetivo ({nuevo_objetivo}): {ajuste:+d} kcal")
            logger.info(f"🎯 Calorías objetivo: {target_calories:.0f} kcal/día")
        
        # Guardar snapshot de dieta antes de modificar (para revertir cambios)
        previous_diet = json.loads(json.dumps(current_diet))
        
        # Guardar calorías anteriores para el resumen
        calorias_anteriores = int(current_diet.get("total_kcal", target_calories))
        
        # ==========================================
        # CALCULAR MACROS TEÓRICOS (ÚNICA FUENTE DE VERDAD)
        # ==========================================
        
        from app.utils.nutrition_calculator import calculate_macros_distribution
        
        macros_obj = calculate_macros_distribution(
            calorias_totales=int(target_calories),
            peso_kg=float(nuevo_peso),
            goal=nuevo_objetivo
        ) or {}
        
        nuevas_proteinas = int(round(float(macros_obj.get("proteina", 0) or 0)))
        nuevos_carbos = int(round(float(macros_obj.get("carbohidratos", 0) or 0)))
        nuevas_grasas = int(round(float(macros_obj.get("grasas", 0) or 0)))
        
        # 🔧 FIX: VALIDAR QUE MACROS NO SEAN CERO
        if nuevas_proteinas == 0 or nuevos_carbos == 0 or nuevas_grasas == 0:
            logger.error(f"❌ Macros calculados son 0: P={nuevas_proteinas}, C={nuevos_carbos}, G={nuevas_grasas}")
            return {
                "success": False,
                "message": "Error calculando macros nutricionales. Por favor contacta soporte."
            }
        
        logger.info(f"")
        logger.info(f"🔢 MACROS CALCULADOS (TEÓRICOS):")
        logger.info(f"   Proteína: {nuevas_proteinas}g")
        logger.info(f"   Carbohidratos: {nuevos_carbos}g")
        logger.info(f"   Grasas: {nuevas_grasas}g")
        logger.info(f"   Total: {target_calories} kcal")
        logger.info(f"")
        
        # ==========================================
        # REGENERAR DIETA CON SISTEMA DE 3 ESTRATEGIAS
        # ==========================================
        
        logger.info(f"🔄 REGENERANDO DIETA COMPLETA...")
        logger.info(f"   Usuario PREMIUM: {is_premium}")
        logger.info(f"   Calorías anteriores: {calorias_anteriores} kcal")
        logger.info(f"   Calorías nuevas: {target_calories} kcal")
        logger.info(f"   Nuevo peso: {nuevo_peso}kg")
        logger.info(f"   Nuevo objetivo: {nuevo_objetivo}")
        
        # Inicializar meals_updated como None para verificar después
        meals_updated = None
        
        # ==========================================
        # USUARIOS PREMIUM: SISTEMA DE 3 ESTRATEGIAS
        # ==========================================
        if is_premium:
            
            # ==========================================
            # ESTRATEGIA 1: INTENTAR GPT CON TIMEOUT
            # ==========================================
            try:
                logger.info(f"🤖 ESTRATEGIA 1: Generando dieta con GPT (timeout {GPT_TIMEOUT_SECONDS}s)...")
                logger.info(f"   Datos usuario: peso={nuevo_peso}kg, objetivo_nutricional={nuevo_objetivo}, altura={altura_cm}cm")
                
                # Preparar datos para GPT
                datos_usuario = {
                    'altura': altura_cm,
                    'peso': float(nuevo_peso),
                    'edad': edad,
                    'sexo': sexo,
                    'objetivo': current_plan.objetivo or 'ganar_musculo',
                    'nutrition_goal': nuevo_objetivo,
                    'experiencia': current_plan.experiencia or 'intermedio',
                    'materiales': current_plan.materiales or 'gym_completo',
                    'tipo_cuerpo': current_plan.tipo_cuerpo or 'mesomorfo',
                    'alergias': current_plan.alergias or 'Ninguna',
                    'restricciones': current_plan.restricciones_dieta or 'Ninguna',
                    'lesiones': current_plan.lesiones or 'Ninguna',
                    'nivel_actividad': nivel_actividad,
                    # 🔧 FIX: Pasar calorías objetivo específicas si fueron solicitadas
                    'target_calories_override': int(target_calories) if target_calories is not None else None
                }
                
                # Llamar a GPT con timeout
                try:
                    plan_generado = await asyncio.wait_for(
                        generar_plan_personalizado(datos_usuario),
                        timeout=GPT_TIMEOUT_SECONDS
                    )
                except asyncio.CancelledError:
                    # 🔧 FIX: Si se cancela durante shutdown, propagar limpiamente
                    logger.warning("⚠️ Generación GPT cancelada (shutdown del servidor)")
                    raise  # Propagar para manejo correcto del shutdown
                
                # Extraer dieta del plan generado
                dieta_generada = plan_generado.get("dieta", {})
                meals_from_gpt = dieta_generada.get("comidas", [])
                
                # 🔧 FIX: VALIDAR que GPT no devolvió template genérico
                # El template genérico siempre tiene "300ml leche semidesnatada - 150kcal" en desayuno
                es_template_generico = False
                if meals_from_gpt:
                    # Buscar en la primera comida (desayuno)
                    primera_comida = meals_from_gpt[0]
                    alimentos_primera = primera_comida.get("alimentos", [])
                    if alimentos_primera:
                        primer_alimento = str(alimentos_primera[0]).lower()
                        # Detectar si es el template genérico exacto
                        if "300ml leche semidesnatada - 150kcal" in primer_alimento:
                            logger.warning(f"⚠️ GPT devolvió template genérico - Primer alimento: {alimentos_primera[0]}")
                            es_template_generico = True
                
                # Si es template genérico, marcar como fallido para usar estrategia 2
                if es_template_generico:
                    logger.warning(f"⚠️ GPT devolvió template genérico, marcando como fallido para estrategia 2")
                    meals_updated = None
                else:
                    # 🔧 FIX: Normalizar formato de comidas con NOMBRES CONSISTENTES
                    meals_updated = []
                    for comida in meals_from_gpt:
                        # Normalizar macros a formato consistente (TODO PLURAL)
                        macros_comida = comida.get("macros", {})
                        comida_formato = {
                            "nombre": comida.get("nombre", ""),
                            "kcal": comida.get("kcal", 0),
                            "macros": {
                                "proteinas": macros_comida.get("proteinas", macros_comida.get("proteina", 0)),
                                "carbohidratos": macros_comida.get("carbohidratos", macros_comida.get("hidratos", 0)),
                                "grasas": macros_comida.get("grasas", 0)
                            },
                            "alimentos": comida.get("alimentos", []),
                            "alternativas": comida.get("alternativas", [])
                        }
                        meals_updated.append(comida_formato)
                    
                    # 🔧 FIX: DETECTAR COMIDAS VACÍAS
                    if not meals_updated or len(meals_updated) == 0:
                        logger.warning(f"⚠️ GPT devolvió 0 comidas, marcando como fallido para estrategia 2")
                        meals_updated = None
                    else:
                        logger.info(f"✅ ESTRATEGIA 1 EXITOSA: Dieta regenerada con GPT ({len(meals_updated)} comidas)")
                        # Log del primer alimento para validar que no es genérico
                        if meals_updated[0].get("alimentos"):
                            primer_alimento = meals_updated[0]["alimentos"][0]
                            logger.info(f"   Primer alimento: {primer_alimento}")
                
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ GPT timeout después de {GPT_TIMEOUT_SECONDS}s - Probando estrategia 2...")
                meals_updated = None
                
            except Exception as e:
                logger.error(f"❌ Error con GPT: {e}")
                logger.warning(f"⚠️ Probando estrategia 2...")
                meals_updated = None
            
            # ==========================================
            # ESTRATEGIA 2: AJUSTE PROPORCIONAL DE CANTIDADES
            # ==========================================
            if meals_updated is None:
                # 1) Tomar la dieta actual si está completa
                meals_fuente = current_diet.get("meals") or current_diet.get("comidas") or []
                
                # 2) Si la fuente tiene menos de 3 comidas, intentar cargar la última dieta completa del Plan
                if len(meals_fuente) < 3:
                    try:
                        from app.models import Plan
                        plan_last = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.id.desc()).first()
                        if plan_last and plan_last.dieta:
                            dieta_plan = json.loads(plan_last.dieta)
                            meals_plan = dieta_plan.get("meals") or dieta_plan.get("comidas") or []
                            if len(meals_plan) >= 3:
                                logger.info(f"📦 Estrategia 2: usando Plan.dieta como fuente ({len(meals_plan)} comidas)")
                                meals_fuente = meals_plan
                                # sincronizar current_diet para el ajustador
                                current_diet = dieta_plan
                            else:
                                logger.warning(f"⚠️ Plan.dieta también incompleta ({len(meals_plan)} comidas)")
                    except Exception as e_load:
                        logger.error(f"❌ Error cargando Plan.dieta para estrategia 2: {e_load}")
                
                if meals_fuente and len(meals_fuente) > 0:
                    logger.info(f"🔢 ESTRATEGIA 2: Ajustando cantidades proporcionalmente (fuente: {len(meals_fuente)} comidas)...")
                    
                    try:
                        meals_updated = ajustar_cantidades_dieta_proporcional(
                            dieta_actual=current_diet,
                            nuevas_calorias_totales=int(target_calories),
                            nuevos_macros={
                                "proteina": nuevas_proteinas,
                                "carbohidratos": nuevos_carbos,
                                "grasas": nuevas_grasas
                            }
                        )
                        logger.info(f"✅ ESTRATEGIA 2 EXITOSA: Cantidades ajustadas proporcionalmente ({len(meals_updated)} comidas)")
                        
                        # Si por algún motivo salió con 1-2 comidas, no es aceptable: pasar a estrategia 3
                        if not meals_updated or len(meals_updated) < 3:
                            logger.warning(f"⚠️ Estrategia 2 produjo {len(meals_updated) if meals_updated else 0} comidas; se forzará estrategia 3")
                            meals_updated = None
                    except Exception as e2:
                        logger.error(f"❌ Error ajustando cantidades proporcionalmente: {e2}")
                        logger.warning(f"⚠️ Probando estrategia 3...")
                        meals_updated = None
                else:
                    logger.warning(f"⚠️ No hay dieta previa completa para ajustar, saltando a estrategia 3...")
            
            # ==========================================
            # ESTRATEGIA 3: TEMPLATE GENÉRICO (ÚLTIMO RECURSO)
            # ==========================================
            if meals_updated is None:
                logger.info(f"📋 ESTRATEGIA 3: Usando template genérico ajustado...")
                is_premium = False  # Para que caiga al bloque FREE de abajo
        
        # ==========================================
        # USUARIOS FREE: TEMPLATE GENÉRICO SIEMPRE
        # ==========================================
        if not is_premium:
            logger.info(f"📋 Generando dieta genérica para usuario FREE...")
            
            # Preparar datos para template genérico
            user_data_generic = {
                'peso': float(nuevo_peso),
                'altura': altura_cm,
                'edad': edad,
                'sexo': sexo,
                'objetivo': nuevo_objetivo,
                'nivel_actividad': nivel_actividad
            }
            
            try:
                # Generar plan genérico
                plan_generico = get_generic_plan(user_data_generic)
                dieta_generica = plan_generico.get("dieta", {})
                
                # 🔧 FIX: Convertir formato con normalización consistente
                meals_from_template = dieta_generica.get("comidas", [])
                meals_updated = []
                for comida in meals_from_template:
                    # Normalizar macros a formato consistente
                    macros_comida = comida.get("macros", {})
                    comida_formato = {
                        "nombre": comida.get("nombre", ""),
                        "kcal": comida.get("kcal", 0),
                        "macros": {
                            "proteinas": macros_comida.get("proteinas", macros_comida.get("proteina", 0)),
                            "carbohidratos": macros_comida.get("carbohidratos", macros_comida.get("hidratos", 0)),
                            "grasas": macros_comida.get("grasas", 0)
                        },
                        "alimentos": comida.get("alimentos", []),
                        "alternativas": comida.get("alternativas", [])
                    }
                    meals_updated.append(comida_formato)
                
                logger.info(f"✅ Dieta genérica regenerada: {len(meals_updated)} comidas")
                
            except Exception as e:
                logger.error(f"❌ Error generando dieta genérica: {e}")
                # Si falla, mantener meals existentes
                meals_existing = current_diet.get("meals") or current_diet.get("comidas") or []
                meals_updated = meals_existing
        
        # ==========================================
        # VERIFICACIÓN FINAL DE SEGURIDAD
        # ==========================================
        if meals_updated is None:
            logger.error(f"❌ CRÍTICO: No se pudo generar dieta por ninguna estrategia")
            meals_existing = current_diet.get("meals") or current_diet.get("comidas") or []
            meals_updated = meals_existing if meals_existing else []
            
            if not meals_updated:
                logger.error(f"❌ CRÍTICO: No hay meals para actualizar - dieta quedará vacía")
        
        logger.info(f"🔄 Dieta final: {len(meals_updated)} comidas")
        
        # 🔧 FIX: GUARDAR VERSIÓN ANTIGUA ANTES DE REDEFINIR current_diet
        old_version = current_diet.get("version", "1.0.0") if isinstance(current_diet, dict) else "1.0.0"
        
        # ==========================================
        # ACTUALIZAR current_diet CON DATOS FINALES
        # ==========================================
        # 🔧 FIX CRÍTICO: USAR NOMBRES CONSISTENTES (TODO PLURAL Y COMPLETO)
        current_diet = {
            "meals": meals_updated,
            "total_kcal": int(target_calories),
            "macros": {
                "proteinas": nuevas_proteinas,      # 🔧 FIX: Plural
                "carbohidratos": nuevos_carbos,     # 🔧 FIX: Completo
                "grasas": nuevas_grasas
            },
            "objetivo": nuevo_objetivo,
            "updated_at": datetime.utcnow().isoformat(),
            "version": increment_diet_version(old_version)  # 🔧 FIX: Usar versión guardada
        }
        
        # Logs de verificación
        logger.info(f"📋 current_diet creado:")
        logger.info(f"   Meals count: {len(current_diet['meals'])}")
        logger.info(f"   Total kcal: {current_diet['total_kcal']}")
        logger.info(f"   Version: {current_diet['version']}")
        if current_diet['meals'] and len(current_diet['meals']) > 0:
            primer_meal = current_diet['meals'][0]
            logger.info(f"   Primera comida: {primer_meal.get('nombre', 'Sin nombre')}")
            if primer_meal.get('alimentos') and len(primer_meal['alimentos']) > 0:
                logger.info(f"   Primer alimento: {primer_meal['alimentos'][0]}")
            else:
                logger.warning(f"   ⚠️ Primera comida sin alimentos")
        else:
            logger.error(f"   ❌ NO HAY COMIDAS EN LA DIETA")
        
        # ==========================================
        # GUARDAR EN BASE DE DATOS
        # ==========================================
        logger.info(f"💾 Actualizando dieta en BD:")
        logger.info(f"   Total kcal: {current_diet['total_kcal']}")
        logger.info(f"   Macros: P={current_diet['macros']['proteinas']}g, C={current_diet['macros']['carbohidratos']}g, G={current_diet['macros']['grasas']}g")
        
        # Guardar en BD - Actualizar tanto Plan.dieta como usuario.current_diet
        current_plan.dieta = json.dumps(current_diet)
        usuario.current_diet = json.dumps(current_diet)
        
        db.commit()
        
        logger.info(f"✅ Dieta actualizada en BD - Plan.dieta y usuario.current_diet")
        
        # Preparar cambios para respuesta
        changes = []
        
        if weight_change_kg is not None and weight_change_kg != 0:
            changes.append(f"Peso: {peso_actual:.1f}kg → {nuevo_peso:.1f}kg")
        
        if goal is not None and objetivo_actual != nuevo_objetivo:
            changes.append(f"Objetivo: {objetivo_actual} → {nuevo_objetivo}")
        
        changes.append(f"Calorías: {calorias_anteriores} → {target_calories} kcal/día")
        changes.append(f"Proteína: {nuevas_proteinas}g/día")
        changes.append(f"Carbohidratos: {nuevos_carbos}g/día")
        changes.append(f"Grasas: {nuevas_grasas}g/día")
        
        logger.info(f"")
        logger.info(f"✅ RECÁLCULO COMPLETADO")
        logger.info(f"📊 Resumen de cambios:")
        for cambio in changes:
            logger.info(f"   • {cambio}")
        logger.info(f"{'='*60}")
        
        # Añadir registro de modificación
        await db_service.add_modification_record(
            user_id,
            "diet_macro_recalculation",
            {
                "previous_diet": previous_diet,  # Snapshot para revertir cambios
                "weight_change": weight_change_kg,
                "goal": goal,
                "changes": changes
            },
            f"Recálculo de macros",
            db
        )
        
        # 🔧 FIX: RESPUESTA SIMPLIFICADA SIN DUPLICACIÓN
        return {
            "success": True,
            "message": "Plan actualizado correctamente",
            "summary": "\n".join(changes),
            "plan_updated": True,
            "changes": changes,
            "dieta": current_diet  # ✅ Solo devolver dieta completa
        }
        
    except Exception as e:
        logger.error(f"Error en handle_recalculate_macros: {e}", exc_info=True)
        if db is not None:
            db.rollback()
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
    Ajusta la dificultad de la rutina - VERSIÓN CORREGIDA
    """
    try:
        # Obtener datos del usuario
        user_data = await db_service.get_user_complete_data(user_id, db)
        current_routine = user_data["current_routine"]
        
        # Validar estructura de rutina
        if not isinstance(current_routine, dict) or "exercises" not in current_routine:
            return {
                "success": False,
                "message": "Estructura de rutina inválida. No se puede modificar.",
                "changes": []
            }
        
        # Guardar snapshot de rutina antes de modificar (para revertir cambios)
        previous_routine = json.loads(json.dumps(current_routine))
        
        # 🔧 FIX: Guardar versión antes de modificar
        old_routine_version = current_routine.get("version", "1.0.0")
        
        changes = []
        
        # Ajustar dificultad de manera eficiente
        for ejercicio in current_routine.get("exercises", []):
            if isinstance(ejercicio, dict):
                if difficulty_change == "increase":
                    # Aumentar series o peso
                    current_sets = ejercicio.get("sets", 3)
                    new_sets = min(current_sets + 1, 5)  # Máximo 5 series
                    ejercicio["sets"] = new_sets
                    changes.append(f"{ejercicio.get('name', 'Ejercicio')}: series {current_sets} → {new_sets}")
                elif difficulty_change == "decrease":
                    # Disminuir series o peso
                    current_sets = ejercicio.get("sets", 3)
                    new_sets = max(current_sets - 1, 2)  # Mínimo 2 series
                    ejercicio["sets"] = new_sets
                    changes.append(f"{ejercicio.get('name', 'Ejercicio')}: series {current_sets} → {new_sets}")
        
        # Actualizar versión y timestamp
        current_routine["version"] = increment_routine_version(old_routine_version)  # 🔧 FIX
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
                "previous_routine": previous_routine,  # Snapshot para revertir cambios
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
        logger.error(f"Error en handle_adjust_routine_difficulty: {e}", exc_info=True)
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
    Modifica la rutina para enfocar más un área específica - VERSIÓN CON GPT
    🔧 NUEVO: Ahora GPT genera una rutina completamente nueva enfocada en el área solicitada
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
        
        # 🔧 FIX: Guardar versión ANTES de modificar
        previous_routine = json.loads(json.dumps(current_routine))
        old_routine_version = current_routine.get("version", "1.0.0")
        
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
            "glutes": "gluteos",
            "glúteos": "gluteos",
            "core": "core",
            "abdomen": "core",
            "abs": "core"
        }
        
        # Mapear el área de enfoque
        mapped_focus_area = area_mapping.get(focus_area.lower(), focus_area.lower())
        
        logger.info(f"🎯 GENERANDO RUTINA CON GPT PARA ENFOQUE:")
        logger.info(f"   Área de enfoque: {mapped_focus_area}")
        logger.info(f"   Aumentar frecuencia: {increase_frequency}")
        logger.info(f"   Cambio de volumen: {volume_change}")
        
        # Obtener datos del Plan para pasar a GPT
        from app.models import Plan
        plan_actual = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.id.desc()).first()
        
        if not plan_actual:
            logger.error(f"❌ No se encontró Plan para usuario {user_id}")
            return {
                "success": False,
                "message": "No se encontró plan del usuario. Completa el onboarding primero.",
                "changes": []
            }
        
        # Preparar datos para GPT con información del enfoque
        datos_gpt = {
            'altura': plan_actual.altura or 175,
            'peso': float(plan_actual.peso) if plan_actual.peso else 75.0,
            'edad': plan_actual.edad or 25,
            'sexo': plan_actual.sexo or 'masculino',
            'objetivo': plan_actual.objetivo_gym or (plan_actual.objetivo or 'ganar_musculo'),
            'gym_goal': plan_actual.objetivo_gym or 'ganar_musculo',
            'nutrition_goal': plan_actual.objetivo_nutricional or (plan_actual.objetivo_dieta or 'mantenimiento'),
            'experiencia': plan_actual.experiencia or 'principiante',
            'materiales': plan_actual.materiales or 'gym_completo',
            'tipo_cuerpo': plan_actual.tipo_cuerpo or 'mesomorfo',
            'alergias': plan_actual.alergias or 'Ninguna',
            'restricciones': plan_actual.restricciones_dieta or 'Ninguna',
            'lesiones': plan_actual.lesiones or 'Ninguna',
            'nivel_actividad': plan_actual.nivel_actividad or 'moderado',
            'training_frequency': 4,
            'training_days': ['lunes', 'martes', 'jueves', 'viernes'],
            # 🔧 NUEVO: Información específica del enfoque
            'focus_area': mapped_focus_area,
            'increase_frequency': increase_frequency,
            'volume_change': volume_change
        }
        
        # Llamar a GPT para generar rutina nueva con enfoque
        from app.utils.gpt import generar_plan_personalizado
        
        exercises_nuevos = None  # Variable para controlar si GPT funcionó
        
        try:
            logger.info(f"🤖 Generando rutina con GPT enfocada en {mapped_focus_area}...")
            plan_generado = await generar_plan_personalizado(datos_gpt)
            
            # Extraer solo la rutina (no necesitamos regenerar dieta)
            rutina_gpt = plan_generado.get("rutina", {})
            dias_rutina = rutina_gpt.get("dias", [])
            
            if not dias_rutina:
                raise ValueError("GPT no generó rutina válida")
            
            # Convertir formato de "dias" a "exercises" (formato que usa current_routine)
            exercises_nuevos = []
            for dia in dias_rutina:
                nombre_dia = dia.get("dia", "")
                grupos_musculares = dia.get("grupos_musculares", "")
                ejercicios_dia = dia.get("ejercicios", [])
                
                for ejercicio in ejercicios_dia:
                    exercises_nuevos.append({
                        "name": ejercicio.get("nombre", ""),
                        "sets": ejercicio.get("series", 3),
                        "reps": ejercicio.get("repeticiones", "10-12"),
                        "weight": "moderado",
                        "day": nombre_dia
                    })
            
            logger.info(f"✅ Rutina generada con GPT enfocada en {mapped_focus_area}: {len(exercises_nuevos)} ejercicios")
            
            # Preparar cambios para el registro
            changes = [
                f"Rutina regenerada con GPT enfocada en {mapped_focus_area}",
                f"Volumen: {volume_change}",
                f"Total ejercicios: {len(exercises_nuevos)}"
            ]
            
        except Exception as e_gpt:
            logger.error(f"❌ Error generando rutina con GPT: {e_gpt}")
            logger.warning(f"⚠️ Fallando a método tradicional de añadir ejercicios...")
            exercises_nuevos = None  # GPT falló, usar fallback
        
        # FALLBACK: Si GPT falló, usar método tradicional de añadir ejercicios
        if exercises_nuevos is None:
            logger.info(f"📋 Usando método tradicional de enfoque...")
            changes = []
            
            # Ejercicios específicos por área de enfoque (fallback)
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
                ],
                "espalda": [
                    {"name": "Remo con barra", "sets": 4, "reps": "8-10", "weight": "moderado"},
                    {"name": "Dominadas", "sets": 3, "reps": "8-12", "weight": "cuerpo"},
                    {"name": "Pulldown", "sets": 3, "reps": "10-12", "weight": "moderado"}
                ],
                "hombros": [
                    {"name": "Press militar", "sets": 4, "reps": "8-10", "weight": "moderado"},
                    {"name": "Elevaciones laterales", "sets": 3, "reps": "12-15", "weight": "ligero"},
                    {"name": "Facepulls", "sets": 3, "reps": "15-20", "weight": "ligero"}
                ],
                "core": [
                    {"name": "Plancha", "sets": 3, "reps": "30-60s", "weight": "cuerpo"},
                    {"name": "Crunch", "sets": 3, "reps": "15-20", "weight": "cuerpo"},
                    {"name": "Mountain climbers", "sets": 3, "reps": "20", "weight": "cuerpo"}
                ]
            }
            
            # Añadir ejercicios de enfoque
            if mapped_focus_area in focus_exercises:
                new_exercises = focus_exercises[mapped_focus_area].copy()
                
                # Ajustar volumen según volume_change
                if volume_change == "aumento_significativo":
                    for exercise in new_exercises:
                        exercise["sets"] = min(exercise["sets"] + 2, 6)
                elif volume_change == "aumento_moderado":
                    for exercise in new_exercises:
                        exercise["sets"] = min(exercise["sets"] + 1, 5)
                elif volume_change == "ligero_aumento":
                    for exercise in new_exercises:
                        exercise["sets"] = min(exercise["sets"], 4)
                
                # Añadir a la rutina
                current_routine["exercises"].extend(new_exercises)
                
                for exercise in new_exercises:
                    changes.append(f"Añadido: {exercise['name']} ({exercise['sets']} series)")
            else:
                changes.append(f"Área '{mapped_focus_area}' no reconocida, no se añadieron ejercicios")
            
            exercises_nuevos = current_routine["exercises"]
        
        # Actualizar rutina con el método que funcionó
        if exercises_nuevos is not None:
            current_routine["exercises"] = exercises_nuevos
        
        current_routine["version"] = increment_routine_version(old_routine_version)
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
                "mapped_focus_area": mapped_focus_area,
                "increase_frequency": increase_frequency,
                "volume_change": volume_change,
                "previous_routine": previous_routine,
                "changes": changes
            },
            f"Enfoque en {mapped_focus_area}",
            db
        )
        
        return {
            "success": True,
            "message": f"Rutina regenerada enfocada en {mapped_focus_area} con {volume_change}",
            "changes": changes
        }
        
    except Exception as e:
        logger.error(f"Error en handle_modify_routine_focus: {e}", exc_info=True)
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
        logger.error(f"Error en handle_revert_modification: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error revirtiendo modificación: {str(e)}",
            "changes": []
        }


async def handle_substitute_food(
    user_id: int,
    disliked_food: str,
    meal_type: str = "todos",
    db: Session = None
) -> Dict[str, Any]:
    """
    Handler para sustitución de alimentos no deseados - VERSIÓN CON GPT PRIORITARIO
    Flujo: 1) Intentar GPT (regenerar dieta completa excluyendo alimento), 2) Fallback a lista de sustituciones
    """
    try:
        logger.info(f"🍽️ Sustituyendo alimento no deseado: {disliked_food} en {meal_type}")
        
        # Obtener datos del usuario
        user_data = await db_service.get_user_complete_data(user_id, db)
        current_diet = user_data["current_diet"]
        
        # Validar estructura de dieta
        if not isinstance(current_diet, dict) or "meals" not in current_diet:
            return {
                "success": False,
                "message": "Estructura de dieta inválida. No se puede modificar.",
                "changes": []
            }
        
        # Obtener usuario para verificar si es premium
        from app.models import Usuario, Plan
        usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not usuario:
            return {
                "success": False,
                "message": "Usuario no encontrado",
                "changes": []
            }
        
        is_premium = bool(usuario.is_premium) or (usuario.plan_type == "PREMIUM")
        logger.info(f"💎 Usuario premium: {is_premium}")
        
        # Guardar snapshot de dieta antes de modificar (para revertir cambios)
        previous_diet = json.loads(json.dumps(current_diet))
        
        # Guardar versión antes de modificar
        old_diet_version = current_diet.get("version", "1.0.0")
        changes = []
        disliked_food_lower = disliked_food.lower()
        
        # ==========================================
        # ESTRATEGIA 1: GPT (Solo para premium)
        # ==========================================
        dieta_regenerada = None
        
        if is_premium:
            try:
                logger.info(f"🤖 ESTRATEGIA 1: Regenerando dieta con GPT excluyendo '{disliked_food}'...")
                
                # Obtener plan actual para datos del usuario
                current_plan = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.id.desc()).first()
                if not current_plan:
                    logger.warning(f"⚠️ No se encontró plan para usuario {user_id}, usando fallback")
                else:
                    # Preparar datos para GPT
                    datos_usuario = {
                        'altura': int(current_plan.altura) if current_plan.altura else 175,
                        'peso': float(current_plan.peso.replace("kg", "").strip()) if current_plan.peso else 75.0,
                        'edad': int(current_plan.edad) if current_plan.edad else 25,
                        'sexo': current_plan.sexo or 'masculino',
                        'objetivo': current_plan.objetivo_gym or 'ganar_musculo',
                        'nutrition_goal': current_plan.objetivo_nutricional or 'mantenimiento',
                        'experiencia': current_plan.experiencia or 'intermedio',
                        'materiales': current_plan.materiales.split(", ") if current_plan.materiales else ['gym_completo'],
                        'tipo_cuerpo': current_plan.tipo_cuerpo or 'mesomorfo',
                        'alergias': current_plan.alergias or 'Ninguna',
                        'restricciones': current_plan.restricciones_dieta or 'Ninguna',
                        'lesiones': current_plan.lesiones or 'Ninguna',
                        'nivel_actividad': current_plan.nivel_actividad or 'moderado',
                        'training_frequency': 4,
                        'training_days': ['lunes', 'martes', 'jueves', 'viernes'],
                        # 🔧 CRÍTICO: Pasar alimentos excluidos
                        'excluded_foods': [disliked_food],
                        # Pasar calorías objetivo actuales
                        'target_calories_override': current_diet.get("total_kcal")
                    }
                    
                    # Llamar a GPT con timeout
                    try:
                        plan_generado = await asyncio.wait_for(
                            generar_plan_personalizado(datos_usuario),
                            timeout=GPT_TIMEOUT_SECONDS
                        )
                        
                        # Extraer dieta del plan generado
                        dieta_generada = plan_generado.get("dieta", {})
                        meals_from_gpt = dieta_generada.get("comidas", [])
                        
                        # Validar que GPT no devolvió template genérico o dieta vacía
                        if meals_from_gpt and len(meals_from_gpt) >= 3:
                            # Normalizar formato de comidas
                            dieta_regenerada = []
                            for comida in meals_from_gpt:
                                macros_comida = comida.get("macros", {})
                                comida_formato = {
                                    "nombre": comida.get("nombre", ""),
                                    "kcal": comida.get("kcal", 0),
                                    "macros": {
                                        "proteinas": macros_comida.get("proteinas", macros_comida.get("proteina", 0)),
                                        "carbohidratos": macros_comida.get("carbohidratos", macros_comida.get("hidratos", 0)),
                                        "grasas": macros_comida.get("grasas", 0)
                                    },
                                    "alimentos": comida.get("alimentos", []),
                                    "alternativas": comida.get("alternativas", [])
                                }
                                dieta_regenerada.append(comida_formato)
                            
                            logger.info(f"✅ ESTRATEGIA 1 EXITOSA: Dieta regenerada con GPT ({len(dieta_regenerada)} comidas)")
                            
                            # 🔧 FIX CRÍTICO: Verificar que no contiene el alimento excluido O SUS VARIANTES/SINÓNIMOS
                            # Crear lista de variantes del alimento excluido
                            variantes_alimento = [disliked_food_lower]
                            
                            # Diccionario de sinónimos/variantes comunes (CRÍTICO para evitar confusiones)
                            # 📋 LISTA EXHAUSTIVA DE SINÓNIMOS Y VARIANTES
                            sinonimos = {
                                # 🥜 FRUTOS SECOS Y CREMAS
                                "mantequilla de cacahuete": ["crema de cacahuete", "crema cacahuete", "mantequilla cacahuete", "peanut butter", "mantequilla de cacahuate", "crema de cacahuate", "crema de maní", "manteca de maní", "manteca de cacahuate"],
                                "crema de cacahuete": ["mantequilla de cacahuete", "mantequilla cacahuete", "crema cacahuete", "peanut butter", "mantequilla de cacahuate", "crema de cacahuate", "crema de maní", "manteca de maní", "manteca de cacahuate"],
                                "mantequilla cacahuete": ["crema de cacahuete", "mantequilla de cacahuete", "crema cacahuete", "peanut butter", "crema de maní", "manteca de maní"],
                                "crema cacahuete": ["mantequilla de cacahuete", "crema de cacahuete", "mantequilla cacahuete", "peanut butter", "crema de maní", "manteca de maní"],
                                "peanut butter": ["mantequilla de cacahuete", "crema de cacahuete", "crema de maní", "manteca de maní"],
                                "crema de maní": ["mantequilla de cacahuete", "crema de cacahuete", "manteca de maní", "peanut butter"],
                                "manteca de maní": ["mantequilla de cacahuete", "crema de cacahuete", "crema de maní", "peanut butter"],
                                "nueces": ["nueces de nogal", "nuez común", "nuez de castilla", "walnuts", "nuez"],
                                "nueces de nogal": ["nueces", "nuez común", "nuez de castilla", "walnuts"],
                                "walnuts": ["nueces", "nueces de nogal", "nuez común"],
                                "almendras": ["almendra cruda", "almendra tostada", "almonds", "almendra"],
                                "almonds": ["almendras", "almendra cruda", "almendra tostada"],
                                "anacardos": ["marañones", "cashews", "anacardo"],
                                "cashews": ["anacardos", "marañones"],
                                "avellanas": ["hazelnut", "avellana tostada", "avellana"],
                                "hazelnut": ["avellanas", "avellana tostada"],
                                "pistachos": ["pistacho pelado", "pistacho natural", "pistachio", "pistacho"],
                                "pistachio": ["pistachos", "pistacho pelado", "pistacho natural"],
                                
                                # 🍞 CEREALES, PANES Y HARINAS
                                "pan integral": ["pan de trigo integral", "pan 100% integral", "pan con salvado", "whole wheat bread", "pan integral"],
                                "pan": ["bread", "pan integral", "pan blanco", "pan de molde"],
                                "bread": ["pan", "pan integral", "pan blanco"],
                                "avena": ["oatmeal", "gachas", "avena en copos", "copos de avena", "avena en hojuelas", "porridge", "avena integral"],
                                "gachas": ["avena", "oatmeal", "avena en copos", "copos de avena", "porridge", "avena en hojuelas"],
                                "oatmeal": ["avena", "gachas", "avena en copos", "copos de avena", "porridge", "avena en hojuelas"],
                                "porridge": ["avena", "gachas", "oatmeal", "avena en copos", "copos de avena"],
                                "copos de avena": ["avena", "gachas", "oatmeal", "porridge", "avena en hojuelas"],
                                "avena en hojuelas": ["avena", "gachas", "oatmeal", "porridge", "copos de avena"],
                                "arroz integral": ["arroz moreno", "arroz de grano entero", "brown rice", "arroz brown", "arroz integral"],
                                "arroz moreno": ["arroz integral", "arroz de grano entero", "brown rice"],
                                "brown rice": ["arroz integral", "arroz moreno", "arroz de grano entero"],
                                "arroz blanco": ["arroz normal", "arroz pulido", "arroz cocido", "rice", "arroz"],
                                "arroz": ["rice", "arroz blanco", "arroz normal", "arroz pulido"],
                                "rice": ["arroz", "arroz blanco", "arroz normal"],
                                "pasta integral": ["macarrones integrales", "espaguetis integrales", "whole wheat pasta"],
                                "pasta": ["pasta italiana", "macarrones", "espaguetis", "fideos", "pasta"],
                                "macarrones": ["pasta", "espaguetis", "fideos"],
                                "espaguetis": ["pasta", "macarrones", "fideos"],
                                "tortitas de arroz": ["galletas de arroz", "tortas de arroz inflado", "rice cakes"],
                                "galletas de arroz": ["tortitas de arroz", "tortas de arroz inflado", "rice cakes"],
                                "rice cakes": ["tortitas de arroz", "galletas de arroz", "tortas de arroz inflado"],
                                
                                # LECHE
                                "leche": ["milk", "leche entera", "leche completa"],
                                "leche semidesnatada": ["leche semi-desnatada", "leche semidesnatada", "semi-skimmed milk", "leche 2%", "leche desnatada parcialmente"],
                                "leche desnatada": ["leche descremada", "skimmed milk", "leche 0%", "leche sin grasa"],
                                "leche entera": ["leche completa", "whole milk", "leche"],
                                "milk": ["leche", "leche entera", "leche completa"],
                                
                                # 🍗 PROTEÍNAS ANIMALES
                                "pollo": ["chicken", "pechuga de pollo", "pollo a la plancha", "pollo asado", "carne blanca", "muslo de pollo"],
                                "chicken": ["pollo", "pechuga de pollo", "carne blanca", "muslo de pollo"],
                                "pechuga de pollo": ["pollo", "chicken", "pechuga pollo", "carne blanca"],
                                "pechuga pollo": ["pollo", "chicken", "pechuga de pollo"],
                                "carne blanca": ["pollo", "chicken", "pechuga de pollo"],
                                "muslo de pollo": ["pollo", "chicken"],
                                "ternera": ["beef", "carne de ternera", "carne ternera", "vaca", "carne de vaca", "vacuno", "carne de res", "carne roja"],
                                "beef": ["ternera", "carne de ternera", "vaca", "vacuno", "carne de res", "carne roja"],
                                "carne": ["ternera", "beef", "vaca", "carne de vaca", "vacuno", "carne de res", "carne roja"],
                                "vacuno": ["ternera", "beef", "carne de ternera", "carne de res"],
                                "carne de res": ["ternera", "beef", "vacuno", "carne de ternera"],
                                "carne roja": ["ternera", "beef", "vacuno", "carne de res"],
                                "pavo": ["turkey", "pechuga de pavo", "pechuga pavo", "fiambre de pavo"],
                                "turkey": ["pavo", "pechuga de pavo", "fiambre de pavo"],
                                "pechuga de pavo": ["pavo", "turkey", "pechuga pavo", "fiambre de pavo"],
                                "fiambre de pavo": ["pavo", "turkey", "pechuga de pavo"],
                                "cerdo": ["lomo de cerdo", "carne de cerdo", "jamón", "pork"],
                                "lomo de cerdo": ["cerdo", "carne de cerdo", "jamón"],
                                "carne de cerdo": ["cerdo", "lomo de cerdo", "jamón"],
                                "jamón": ["cerdo", "lomo de cerdo", "carne de cerdo"],
                                "pork": ["cerdo", "lomo de cerdo", "carne de cerdo"],
                                "pescado": ["fish", "pescado blanco", "pescado azul"],
                                "fish": ["pescado", "pescado blanco"],
                                "salmón": ["salmon", "salmón fresco", "salmón ahumado", "filete de salmón", "pescado azul"],
                                "salmon": ["salmón", "salmón fresco", "filete de salmón"],
                                "filete de salmón": ["salmón", "salmon", "salmón fresco"],
                                "atún": ["tuna", "atún en lata", "atún en conserva", "atún natural", "bonito"],
                                "tuna": ["atún", "atún en lata", "atún en conserva", "bonito"],
                                "atún en lata": ["atún", "tuna", "atún en conserva"],
                                "bonito": ["atún", "tuna", "atún en lata"],
                                
                                # 🥚 HUEVOS
                                "huevos": ["huevo", "eggs", "huevos enteros", "huevo entero"],
                                "huevo": ["huevos", "eggs", "huevos enteros"],
                                "eggs": ["huevos", "huevo", "huevos enteros"],
                                "claras de huevo": ["clara de huevo", "egg whites", "claras huevo", "albúmina", "parte blanca del huevo"],
                                "clara de huevo": ["claras de huevo", "egg whites", "claras huevo", "albúmina", "parte blanca del huevo"],
                                "egg whites": ["claras de huevo", "clara de huevo", "albúmina"],
                                "albúmina": ["claras de huevo", "clara de huevo", "egg whites", "parte blanca del huevo"],
                                "parte blanca del huevo": ["claras de huevo", "clara de huevo", "albúmina"],
                                
                                # 🥦 VERDURAS Y HORTALIZAS
                                "espinacas": ["hojas verdes", "acelga", "spinach"],
                                "hojas verdes": ["espinacas", "acelga"],
                                "acelga": ["espinacas", "hojas verdes"],
                                "spinach": ["espinacas", "hojas verdes"],
                                "brócoli": ["brécol", "col verde", "broccoli"],
                                "brécol": ["brócoli", "col verde", "broccoli"],
                                "col verde": ["brócoli", "brécol"],
                                "broccoli": ["brócoli", "brécol", "col verde"],
                                "zanahoria": ["zanahoria cruda", "zanahoria cocida", "carrot"],
                                "zanahoria cruda": ["zanahoria", "carrot"],
                                "zanahoria cocida": ["zanahoria", "carrot"],
                                "carrot": ["zanahoria", "zanahoria cruda", "zanahoria cocida"],
                                "calabacín": ["zucchini", "calabacín"],
                                "zucchini": ["calabacín"],
                                "pimiento": ["ají", "morrón", "pepper"],
                                "ají": ["pimiento", "morrón"],
                                "morrón": ["pimiento", "ají"],
                                "pepper": ["pimiento", "ají", "morrón"],
                                "tomate": ["jitomate", "tomate rojo", "tomato"],
                                "jitomate": ["tomate", "tomate rojo"],
                                "tomate rojo": ["tomate", "jitomate"],
                                "tomato": ["tomate", "jitomate", "tomate rojo"],
                                "patata": ["patatas", "potato", "potatoes", "papas", "papa"],
                                "patatas": ["patata", "potato", "potatoes", "papas", "papa"],
                                "potato": ["patata", "patatas", "papas", "papa"],
                                "potatoes": ["patata", "patatas", "papas", "papa"],
                                "papas": ["patata", "patatas", "potato", "potatoes"],
                                "papa": ["patata", "patatas", "potato", "potatoes"],
                                "boniato": ["batata", "sweet potato", "camote"],
                                "batata": ["boniato", "sweet potato", "camote"],
                                "sweet potato": ["boniato", "batata", "camote"],
                                "camote": ["boniato", "batata", "sweet potato"],
                                
                                # 🍚 LEGUMBRES
                                "lentejas": ["lentejas pardinas", "lentejas cocidas", "lentils"],
                                "lentejas pardinas": ["lentejas", "lentejas cocidas"],
                                "lentejas cocidas": ["lentejas", "lentejas pardinas"],
                                "lentils": ["lentejas", "lentejas pardinas", "lentejas cocidas"],
                                "garbanzos": ["chickpeas", "garbanzo cocido", "garbanzo"],
                                "chickpeas": ["garbanzos", "garbanzo cocido"],
                                "garbanzo cocido": ["garbanzos", "chickpeas"],
                                "judías": ["alubias", "porotos", "frijoles", "beans"],
                                "alubias": ["judías", "porotos", "frijoles"],
                                "porotos": ["judías", "alubias", "frijoles"],
                                "frijoles": ["judías", "alubias", "porotos"],
                                "beans": ["judías", "alubias", "porotos", "frijoles"],
                                "soja": ["habas de soja", "soya", "soy"],
                                "habas de soja": ["soja", "soya"],
                                "soya": ["soja", "habas de soja"],
                                "soy": ["soja", "soya", "habas de soja"],
                                
                                # 🧀 LÁCTEOS Y DERIVADOS
                                "leche": ["milk", "leche entera", "leche completa", "leche de vaca"],
                                "milk": ["leche", "leche entera", "leche de vaca"],
                                "leche de vaca": ["leche", "milk", "leche entera"],
                                "leche semidesnatada": ["leche semi-desnatada", "leche semidesnatada", "semi-skimmed milk", "leche 2%", "leche desnatada parcialmente"],
                                "leche desnatada": ["leche descremada", "skimmed milk", "leche 0%", "leche sin grasa"],
                                "leche entera": ["leche completa", "whole milk", "leche", "leche de vaca"],
                                "yogur": ["yogurt", "yoghurt", "yogur natural", "yogur griego", "yogur blanco", "yogur sin azúcar"],
                                "yogurt": ["yogur", "yoghurt", "yogur natural", "yogur blanco"],
                                "yogur natural": ["yogur", "yogurt", "yogur blanco", "yogur sin azúcar"],
                                "yogur blanco": ["yogur natural", "yogur", "yogur sin azúcar"],
                                "yogur sin azúcar": ["yogur natural", "yogur blanco", "yogur"],
                                "yogur griego": ["greek yogurt", "yogur griego natural"],
                                "queso": ["cheese", "queso fresco", "queso tierno"],
                                "cheese": ["queso", "queso fresco"],
                                "queso fresco": ["queso tipo burgos", "queso", "cheese", "requesón"],
                                "queso tipo burgos": ["queso fresco", "requesón"],
                                "requesón": ["ricotta", "requesón fresco", "cuajada de leche", "queso tipo burgos"],
                                "ricotta": ["requesón", "requesón fresco", "cuajada de leche"],
                                "cuajada de leche": ["requesón", "ricotta"],
                                "mantequilla": ["manteca", "manteca de leche", "butter"],
                                "manteca": ["mantequilla", "manteca de leche"],
                                "manteca de leche": ["mantequilla", "manteca"],
                                "butter": ["mantequilla", "manteca"],
                                "leche vegetal": ["bebida de soja", "bebida de avena", "leche de almendras", "leche de soja", "leche de avena"],
                                "bebida de soja": ["leche vegetal", "leche de soja", "bebida de avena"],
                                "bebida de avena": ["leche vegetal", "leche de avena", "bebida de soja"],
                                "leche de almendras": ["leche vegetal", "bebida de almendras"],
                                "leche de soja": ["leche vegetal", "bebida de soja"],
                                "leche de avena": ["leche vegetal", "bebida de avena"],
                                
                                # 🍎 FRUTAS
                                "plátano": ["banana", "plátano canario", "banano", "cambur"],
                                "banana": ["plátano", "plátano canario", "banano", "cambur"],
                                "banano": ["plátano", "banana", "cambur"],
                                "cambur": ["plátano", "banana", "banano"],
                                "manzana": ["apple", "manzana roja", "manzana verde"],
                                "apple": ["manzana", "manzana roja", "manzana verde"],
                                "manzana roja": ["manzana", "apple"],
                                "manzana verde": ["manzana", "apple"],
                                "pera": ["pear", "pera verde"],
                                "pear": ["pera", "pera verde"],
                                "aguacate": ["avocado", "palta", "aguacate hass"],
                                "avocado": ["aguacate", "palta"],
                                "palta": ["aguacate", "avocado"],
                                "sandía": ["patilla", "melón de agua", "watermelon"],
                                "patilla": ["sandía", "melón de agua"],
                                "melón de agua": ["sandía", "patilla"],
                                "watermelon": ["sandía", "patilla", "melón de agua"],
                                "melón": ["melón cantalupo", "melón verde", "melon"],
                                "melón cantalupo": ["melón", "melón verde"],
                                "melón verde": ["melón", "melón cantalupo"],
                                "uvas": ["racimo de uvas", "uvas sin semilla", "grapes"],
                                "racimo de uvas": ["uvas", "grapes"],
                                "uvas sin semilla": ["uvas", "grapes"],
                                "grapes": ["uvas", "racimo de uvas"],
                                "frutos rojos": ["frutos del bosque", "berries", "arándanos", "frambuesas", "fresas"],
                                "frutos del bosque": ["frutos rojos", "berries", "arándanos", "frambuesas", "fresas"],
                                "berries": ["frutos rojos", "frutos del bosque", "arándanos", "frambuesas", "fresas"],
                                "arándanos": ["frutos rojos", "frutos del bosque", "berries", "blueberries"],
                                "frambuesas": ["frutos rojos", "frutos del bosque", "berries", "raspberries"],
                                "fresas": ["frutos rojos", "frutos del bosque", "berries", "strawberries"],
                                
                                # 🥑 GRASAS Y ACEITES
                                "aceite de oliva": ["olive oil", "aceite oliva", "aove", "aceite oliva virgen", "aceite virgen extra", "aceite virgen"],
                                "olive oil": ["aceite de oliva", "aceite oliva", "aove", "aceite virgen extra"],
                                "aceite oliva": ["aceite de oliva", "olive oil", "aove"],
                                "aove": ["aceite de oliva", "olive oil", "aceite virgen extra"],
                                "aceite virgen extra": ["aceite de oliva", "aove", "olive oil"],
                                "aceite de girasol": ["aceite vegetal", "sunflower oil"],
                                "aceite vegetal": ["aceite de girasol", "sunflower oil"],
                                "sunflower oil": ["aceite de girasol", "aceite vegetal"],
                                "frutos secos": ["mix de frutos", "frutos grasos", "nuts", "frutos secos mix"],
                                "mix de frutos": ["frutos secos", "frutos grasos"],
                                "frutos grasos": ["frutos secos", "mix de frutos"],
                                "nuts": ["frutos secos", "mix de frutos"],
                                
                                # 🍫 OTROS / DULCES
                                "chocolate negro": ["cacao", "chocolate amargo", "dark chocolate"],
                                "chocolate amargo": ["chocolate negro", "cacao", "dark chocolate"],
                                "cacao": ["chocolate negro", "chocolate amargo", "dark chocolate"],
                                "dark chocolate": ["chocolate negro", "chocolate amargo", "cacao"],
                                "miel": ["miel natural", "néctar de abejas", "honey"],
                                "miel natural": ["miel", "néctar de abejas"],
                                "néctar de abejas": ["miel", "miel natural"],
                                "honey": ["miel", "miel natural"],
                                "azúcar": ["sugar", "azúcar blanca", "azúcar blanco", "azúcar refinada", "azúcar refinado", "sacarosa"],
                                "sugar": ["azúcar", "azúcar blanca", "azúcar blanco", "azúcar refinada"],
                                "azúcar blanca": ["azúcar", "sugar", "azúcar refinada"],
                                "azúcar refinada": ["azúcar", "azúcar blanca", "sacarosa"],
                                "azúcar refinado": ["azúcar", "azúcar blanca", "sacarosa"],
                                "sacarosa": ["azúcar", "azúcar refinada", "azúcar refinado"],
                                "edulcorante": ["stevia", "eritritol", "sucralosa", "sweetener"],
                                "stevia": ["edulcorante", "sweetener"],
                                "eritritol": ["edulcorante", "sweetener"],
                                "sucralosa": ["edulcorante", "sweetener"],
                                "sweetener": ["edulcorante", "stevia", "eritritol", "sucralosa"],
                                
                                # 💧 BEBIDAS
                                "agua con gas": ["agua carbonatada", "soda", "sparkling water"],
                                "agua carbonatada": ["agua con gas", "soda"],
                                "soda": ["agua con gas", "agua carbonatada"],
                                "sparkling water": ["agua con gas", "agua carbonatada"],
                                "refresco": ["bebida azucarada", "gaseosa", "soda", "soft drink"],
                                "bebida azucarada": ["refresco", "gaseosa"],
                                "gaseosa": ["refresco", "bebida azucarada"],
                                "soft drink": ["refresco", "bebida azucarada", "gaseosa"],
                                "café": ["espresso", "café solo", "americano", "coffee"],
                                "espresso": ["café", "café solo"],
                                "café solo": ["café", "espresso"],
                                "americano": ["café", "coffee"],
                                "coffee": ["café", "espresso", "americano"],
                                "té verde": ["infusión de té", "matcha", "green tea"],
                                "infusión de té": ["té verde", "matcha"],
                                "matcha": ["té verde", "infusión de té"],
                                "green tea": ["té verde", "infusión de té", "matcha"],
                                
                                # 💪 PROTEÍNA EN POLVO
                                "proteína en polvo": ["proteína polvo", "whey protein", "proteína whey", "proteína de suero"],
                                "proteína polvo": ["proteína en polvo", "whey protein", "proteína whey"],
                                "whey protein": ["proteína en polvo", "proteína polvo", "proteína whey"],
                                "proteína whey": ["proteína en polvo", "proteína polvo", "whey protein"],
                                "proteína de suero": ["proteína en polvo", "whey protein"],
                                
                                # 🧂 VARIOS
                                "sal": ["salt", "sal marina", "sal común"],
                                "salt": ["sal", "sal marina"],
                                "sal marina": ["sal", "salt"],
                                "sal común": ["sal", "salt"],
                                
                                # 🍞 CEREALES (ya incluidos arriba pero para completitud)
                                "quinoa": ["quinua"],
                                "quinua": ["quinoa"]
                            }
                            
                            # Añadir sinónimos a la lista de variantes
                            for alimento, variantes in sinonimos.items():
                                if alimento.lower() in disliked_food_lower or disliked_food_lower in alimento.lower():
                                    variantes_alimento.extend([v.lower() for v in variantes])
                                    break
                            
                            # Eliminar duplicados
                            variantes_alimento = list(set(variantes_alimento))
                            logger.info(f"🔍 Buscando variantes del alimento excluido: {variantes_alimento}")
                            
                            # Verificar que no contiene ninguna variante
                            contiene_excluido = False
                            alimento_prohibido_encontrado = None
                            for comida in dieta_regenerada:
                                for alimento in comida.get("alimentos", []):
                                    if isinstance(alimento, str):
                                        alimento_lower = alimento.lower()
                                        # Buscar si alguna variante está en el alimento
                                        for variante in variantes_alimento:
                                            if variante in alimento_lower:
                                                contiene_excluido = True
                                                alimento_prohibido_encontrado = alimento
                                                logger.warning(f"⚠️ GPT incluyó alimento excluido o variante: '{alimento}' (buscaba: {variantes_alimento})")
                                                break
                                        if contiene_excluido:
                                            break
                                if contiene_excluido:
                                    break
                            
                            if contiene_excluido:
                                logger.warning(f"⚠️ GPT incluyó alimento excluido o variante '{alimento_prohibido_encontrado}', usando estrategia 2...")
                                dieta_regenerada = None
                            else:
                                logger.info(f"✅ Verificado: GPT excluyó correctamente '{disliked_food}' y sus variantes")
                        else:
                            logger.warning(f"⚠️ GPT devolvió dieta incompleta ({len(meals_from_gpt) if meals_from_gpt else 0} comidas), usando estrategia 2...")
                            dieta_regenerada = None
                            
                    except asyncio.TimeoutError:
                        logger.warning(f"⏱️ GPT timeout después de {GPT_TIMEOUT_SECONDS}s, usando estrategia 2...")
                        dieta_regenerada = None
                    except Exception as e:
                        logger.error(f"❌ Error con GPT: {e}")
                        logger.warning(f"⚠️ Usando estrategia 2 (lista de sustituciones)...")
                        dieta_regenerada = None
                        
            except Exception as e:
                logger.error(f"❌ Error preparando datos para GPT: {e}")
                dieta_regenerada = None
        
        # ==========================================
        # ESTRATEGIA 2: Lista de sustituciones (Fallback)
        # ==========================================
        mejor_sustitucion = None
        total_sustituciones = 0
        
        if dieta_regenerada is None:
            logger.info(f"📋 ESTRATEGIA 2: Usando lista de sustituciones predefinidas...")
            meals = current_diet.get("meals", [])
            
            # Diccionario de sustituciones con macros similares
            # 🔧 FIX: Incluir variantes y sinónimos en el diccionario
            sustituciones = {
                # 🧀 LÁCTEOS Y DERIVADOS
                "leche": ["leche de almendras", "leche de avena", "leche de soja", "yogur natural"],
                "leche de vaca": ["leche de almendras", "leche de avena", "leche de soja", "yogur natural"],
                "leche semidesnatada": ["leche de almendras", "leche de avena", "yogur natural"],
                "leche desnatada": ["leche de almendras", "leche de avena", "yogur natural"],
                "leche entera": ["leche de almendras", "leche de avena", "leche de soja", "yogur natural"],
                "milk": ["leche de almendras", "leche de avena", "leche de soja", "yogur natural"],
                "yogur": ["kéfir", "requesón", "cuajada", "yogur griego"],
                "yogur natural": ["kéfir", "requesón", "cuajada", "yogur griego"],
                "yogur blanco": ["kéfir", "requesón", "cuajada", "yogur griego"],
                "yogur sin azúcar": ["kéfir", "requesón", "cuajada", "yogur griego"],
                "yogurt": ["kéfir", "requesón", "cuajada", "yogur griego"],
                "yoghurt": ["kéfir", "requesón", "cuajada", "yogur griego"],
                "yogur griego": ["kéfir", "requesón", "cuajada", "yogur natural"],
                "queso": ["requesón", "queso fresco", "tofu", "yogur griego"],
                "cheese": ["requesón", "queso fresco", "tofu", "yogur griego"],
                "queso fresco": ["requesón", "queso tipo burgos", "tofu", "yogur griego"],
                "queso tipo burgos": ["requesón", "queso fresco", "tofu"],
                "requesón": ["ricotta", "queso fresco", "cuajada de leche"],
                "ricotta": ["requesón", "queso fresco", "cuajada de leche"],
                "cuajada de leche": ["requesón", "ricotta", "queso fresco"],
                "mantequilla": ["manteca", "aceite de oliva", "aguacate"],
                "manteca": ["mantequilla", "aceite de oliva", "aguacate"],
                "manteca de leche": ["mantequilla", "aceite de oliva", "aguacate"],
                "butter": ["mantequilla", "aceite de oliva", "aguacate"],
                "leche vegetal": ["bebida de soja", "bebida de avena", "leche de almendras"],
                "bebida de soja": ["leche vegetal", "leche de soja", "bebida de avena"],
                "bebida de avena": ["leche vegetal", "leche de avena", "bebida de soja"],
                "leche de almendras": ["leche vegetal", "bebida de almendras", "leche de soja"],
                "leche de soja": ["leche vegetal", "bebida de soja", "leche de avena"],
                "leche de avena": ["leche vegetal", "bebida de avena", "leche de soja"],
                
                # 🍞 CEREALES, PANES Y HARINAS
                "pan integral": ["pan de trigo integral", "pan 100% integral", "pan con salvado"],
                "pan de trigo integral": ["pan integral", "pan 100% integral", "pan con salvado"],
                "pan 100% integral": ["pan integral", "pan de trigo integral", "pan con salvado"],
                "pan con salvado": ["pan integral", "pan de trigo integral", "pan 100% integral"],
                "pan": ["tortitas de arroz", "crackers integrales", "pan de centeno"],
                "bread": ["tortitas de arroz", "crackers integrales", "pan de centeno"],
                "avena": ["quinoa", "arroz integral", "mijo", "trigo sarraceno"],
                "oatmeal": ["quinoa", "arroz integral", "mijo", "trigo sarraceno"],
                "gachas": ["quinoa", "arroz integral", "mijo", "trigo sarraceno"],
                "porridge": ["quinoa", "arroz integral", "mijo", "trigo sarraceno"],
                "copos de avena": ["quinoa", "arroz integral", "mijo", "trigo sarraceno"],
                "avena en copos": ["quinoa", "arroz integral", "mijo", "trigo sarraceno"],
                "avena en hojuelas": ["quinoa", "arroz integral", "mijo", "trigo sarraceno"],
                "arroz integral": ["arroz moreno", "arroz de grano entero", "quinoa", "mijo"],
                "arroz moreno": ["arroz integral", "arroz de grano entero", "quinoa"],
                "arroz de grano entero": ["arroz integral", "arroz moreno", "quinoa"],
                "brown rice": ["arroz integral", "arroz moreno", "quinoa"],
                "arroz blanco": ["arroz normal", "arroz pulido", "arroz cocido", "quinoa"],
                "arroz": ["arroz normal", "arroz pulido", "quinoa", "mijo"],
                "arroz normal": ["arroz blanco", "arroz pulido", "quinoa"],
                "arroz pulido": ["arroz blanco", "arroz normal", "quinoa"],
                "arroz cocido": ["arroz blanco", "arroz normal", "quinoa"],
                "rice": ["quinoa", "mijo", "boniato", "patata"],
                "pasta integral": ["macarrones integrales", "espaguetis integrales", "arroz integral"],
                "pasta": ["arroz integral", "quinoa", "boniato"],
                "macarrones": ["arroz integral", "quinoa", "boniato"],
                "macarrones integrales": ["pasta integral", "espaguetis integrales", "arroz integral"],
                "espaguetis": ["arroz integral", "quinoa", "boniato"],
                "espaguetis integrales": ["pasta integral", "macarrones integrales", "arroz integral"],
                "fideos": ["arroz integral", "quinoa", "boniato"],
                "tortitas de arroz": ["galletas de arroz", "tortas de arroz inflado", "pan integral"],
                "galletas de arroz": ["tortitas de arroz", "tortas de arroz inflado", "pan integral"],
                "tortas de arroz inflado": ["tortitas de arroz", "galletas de arroz", "pan integral"],
                "rice cakes": ["tortitas de arroz", "galletas de arroz", "pan integral"],
                "patata": ["boniato", "quinoa", "arroz integral"],
                "patatas": ["boniato", "quinoa", "arroz integral"],
                "potato": ["boniato", "quinoa", "arroz integral"],
                "potatoes": ["boniato", "quinoa", "arroz integral"],
                "papas": ["boniato", "quinoa", "arroz integral"],
                "papa": ["boniato", "quinoa", "arroz integral"],
                "boniato": ["patata", "quinoa", "arroz integral"],
                "batata": ["patata", "quinoa", "arroz integral"],
                "sweet potato": ["patata", "quinoa", "arroz integral"],
                "camote": ["patata", "quinoa", "arroz integral"],
                "quinoa": ["quinua", "arroz integral", "mijo"],
                "quinua": ["quinoa", "arroz integral", "mijo"],
                
                # 🍗 PROTEÍNAS ANIMALES
                "pollo": ["pavo", "ternera magra", "pescado blanco", "tofu"],
                "chicken": ["pavo", "ternera magra", "pescado blanco", "tofu"],
                "pechuga de pollo": ["pavo", "ternera magra", "pescado blanco", "tofu"],
                "pechuga pollo": ["pavo", "ternera magra", "pescado blanco", "tofu"],
                "carne blanca": ["pollo", "pavo", "ternera magra", "tofu"],
                "muslo de pollo": ["pavo", "ternera magra", "pescado blanco", "tofu"],
                "ternera": ["pollo", "pavo", "cerdo magro", "pescado"],
                "beef": ["pollo", "pavo", "cerdo magro", "pescado"],
                "carne": ["pollo", "pavo", "cerdo magro", "pescado"],
                "carne de ternera": ["pollo", "pavo", "cerdo magro", "pescado"],
                "vaca": ["pollo", "pavo", "cerdo magro", "pescado"],
                "vacuno": ["pollo", "pavo", "cerdo magro", "pescado"],
                "carne de res": ["pollo", "pavo", "cerdo magro", "pescado"],
                "carne roja": ["pollo", "pavo", "cerdo magro", "pescado"],
                "pavo": ["turkey", "pechuga de pavo", "pollo", "ternera magra"],
                "turkey": ["pavo", "pechuga de pavo", "pollo", "ternera magra"],
                "pechuga de pavo": ["pavo", "turkey", "pollo", "ternera magra"],
                "fiambre de pavo": ["pavo", "turkey", "pollo", "ternera magra"],
                "cerdo": ["lomo de cerdo", "carne de cerdo", "jamón", "pollo"],
                "lomo de cerdo": ["cerdo", "carne de cerdo", "jamón", "pollo"],
                "carne de cerdo": ["cerdo", "lomo de cerdo", "jamón", "pollo"],
                "jamón": ["cerdo", "lomo de cerdo", "carne de cerdo", "pollo"],
                "pork": ["cerdo", "lomo de cerdo", "carne de cerdo", "pollo"],
                "pescado": ["pollo", "pavo", "huevos", "tofu"],
                "fish": ["pollo", "pavo", "huevos", "tofu"],
                "pescado blanco": ["pollo", "pavo", "huevos", "tofu"],
                "pescado azul": ["pollo", "pavo", "huevos", "tofu"],
                "atún": ["salmón", "pollo", "pavo", "huevos"],
                "tuna": ["salmón", "pollo", "pavo", "huevos"],
                "atún en lata": ["atún natural", "salmón", "pollo", "pavo"],
                "atún en conserva": ["atún natural", "salmón", "pollo", "pavo"],
                "atún natural": ["atún en lata", "salmón", "pollo", "pavo"],
                "bonito": ["atún", "salmón", "pollo", "pavo"],
                "salmón": ["atún", "pollo", "pavo", "huevos"],
                "salmon": ["atún", "pollo", "pavo", "huevos"],
                "salmón fresco": ["salmón ahumado", "atún", "pollo", "pavo"],
                "salmón ahumado": ["salmón fresco", "atún", "pollo", "pavo"],
                "filete de salmón": ["salmón fresco", "atún", "pollo", "pavo"],
                "huevos": ["claras de huevo", "tofu", "proteína en polvo"],
                "huevo": ["claras de huevo", "tofu", "proteína en polvo"],
                "eggs": ["claras de huevo", "tofu", "proteína en polvo"],
                "huevos enteros": ["claras de huevo", "tofu", "proteína en polvo"],
                "huevo entero": ["claras de huevo", "tofu", "proteína en polvo"],
                "claras de huevo": ["albúmina", "parte blanca del huevo", "huevos", "tofu"],
                "clara de huevo": ["albúmina", "parte blanca del huevo", "huevos", "tofu"],
                "egg whites": ["albúmina", "parte blanca del huevo", "huevos", "tofu"],
                "albúmina": ["claras de huevo", "parte blanca del huevo", "huevos", "tofu"],
                "parte blanca del huevo": ["claras de huevo", "albúmina", "huevos", "tofu"],
                
                # 🍎 FRUTAS
                "plátano": ["manzana", "pera", "dátiles", "uvas"],
                "banana": ["manzana", "pera", "dátiles", "uvas"],
                "banano": ["manzana", "pera", "dátiles", "uvas"],
                "cambur": ["manzana", "pera", "dátiles", "uvas"],
                "manzana": ["pera", "naranja", "kiwi", "fresas"],
                "manzana roja": ["pera", "naranja", "kiwi", "fresas"],
                "manzana verde": ["pera", "naranja", "kiwi", "fresas"],
                "apple": ["pera", "naranja", "kiwi", "fresas"],
                "pera": ["manzana", "naranja", "kiwi", "fresas"],
                "pera verde": ["manzana", "naranja", "kiwi", "fresas"],
                "pear": ["manzana", "naranja", "kiwi", "fresas"],
                "aguacate": ["aceite de oliva", "frutos secos", "semillas"],
                "avocado": ["aceite de oliva", "frutos secos", "semillas"],
                "palta": ["aceite de oliva", "frutos secos", "semillas"],
                "aguacate hass": ["aceite de oliva", "frutos secos", "semillas"],
                "sandía": ["patilla", "melón de agua", "melón", "manzana"],
                "patilla": ["sandía", "melón de agua", "melón", "manzana"],
                "melón de agua": ["sandía", "patilla", "melón", "manzana"],
                "watermelon": ["sandía", "patilla", "melón", "manzana"],
                "melón": ["melón cantalupo", "melón verde", "sandía", "manzana"],
                "melón cantalupo": ["melón", "melón verde", "sandía"],
                "melón verde": ["melón", "melón cantalupo", "sandía"],
                "melon": ["melón", "melón cantalupo", "sandía"],
                "uvas": ["racimo de uvas", "uvas sin semilla", "manzana", "pera"],
                "racimo de uvas": ["uvas", "uvas sin semilla", "manzana", "pera"],
                "uvas sin semilla": ["uvas", "racimo de uvas", "manzana", "pera"],
                "grapes": ["uvas", "racimo de uvas", "manzana", "pera"],
                "frutos rojos": ["frutos del bosque", "berries", "arándanos", "frambuesas", "fresas"],
                "frutos del bosque": ["frutos rojos", "berries", "arándanos", "frambuesas", "fresas"],
                "berries": ["frutos rojos", "frutos del bosque", "arándanos", "frambuesas", "fresas"],
                "arándanos": ["frutos rojos", "frutos del bosque", "berries", "frambuesas", "fresas"],
                "blueberries": ["frutos rojos", "frutos del bosque", "berries", "frambuesas", "fresas"],
                "frambuesas": ["frutos rojos", "frutos del bosque", "berries", "arándanos", "fresas"],
                "raspberries": ["frutos rojos", "frutos del bosque", "berries", "arándanos", "fresas"],
                "fresas": ["frutos rojos", "frutos del bosque", "berries", "arándanos", "frambuesas"],
                "strawberries": ["frutos rojos", "frutos del bosque", "berries", "arándanos", "frambuesas"],
                
                # 🥜 FRUTOS SECOS Y CREMAS
                "mantequilla de cacahuete": ["mantequilla de almendras", "tahini", "aguacate"],
                "crema de cacahuete": ["mantequilla de almendras", "tahini", "aguacate"],
                "crema cacahuete": ["mantequilla de almendras", "tahini", "aguacate"],
                "mantequilla cacahuete": ["mantequilla de almendras", "tahini", "aguacate"],
                "peanut butter": ["mantequilla de almendras", "tahini", "aguacate"],
                "crema de maní": ["mantequilla de almendras", "tahini", "aguacate"],
                "manteca de maní": ["mantequilla de almendras", "tahini", "aguacate"],
                "manteca de cacahuate": ["mantequilla de almendras", "tahini", "aguacate"],
                "nueces": ["almendras", "avellanas", "anacardos"],
                "walnuts": ["almendras", "avellanas", "anacardos"],
                "nueces de nogal": ["almendras", "avellanas", "anacardos"],
                "almendras": ["nueces", "avellanas", "anacardos"],
                "almonds": ["nueces", "avellanas", "anacardos"],
                "anacardos": ["almendras", "nueces", "avellanas"],
                "cashews": ["almendras", "nueces", "avellanas"],
                "marañones": ["almendras", "nueces", "avellanas"],
                "avellanas": ["almendras", "nueces", "anacardos"],
                "hazelnut": ["almendras", "nueces", "anacardos"],
                "pistachos": ["almendras", "nueces", "avellanas"],
                "pistachio": ["almendras", "nueces", "avellanas"],
                
                # 🥑 GRASAS Y ACEITES
                "aceite de oliva": ["aguacate", "frutos secos", "semillas"],
                "aceite oliva": ["aguacate", "frutos secos", "semillas"],
                "olive oil": ["aguacate", "frutos secos", "semillas"],
                "aove": ["aguacate", "frutos secos", "semillas"],
                "aceite virgen extra": ["aguacate", "frutos secos", "semillas"],
                "aceite de girasol": ["aceite de oliva", "aguacate", "frutos secos"],
                "aceite vegetal": ["aceite de oliva", "aguacate", "frutos secos"],
                "sunflower oil": ["aceite de oliva", "aguacate", "frutos secos"],
                "frutos secos": ["mix de frutos", "almendras", "nueces"],
                "mix de frutos": ["almendras", "nueces", "avellanas"],
                "frutos grasos": ["almendras", "nueces", "avellanas"],
                "nuts": ["almendras", "nueces", "avellanas"],
                
                # 🥦 VERDURAS Y HORTALIZAS
                "espinacas": ["hojas verdes", "acelga", "brócoli"],
                "hojas verdes": ["espinacas", "acelga", "brócoli"],
                "acelga": ["espinacas", "hojas verdes", "brócoli"],
                "spinach": ["espinacas", "hojas verdes", "acelga"],
                "brócoli": ["brécol", "col verde", "espinacas"],
                "brécol": ["brócoli", "col verde", "espinacas"],
                "col verde": ["brócoli", "brécol", "espinacas"],
                "broccoli": ["brócoli", "brécol", "col verde"],
                "zanahoria": ["zanahoria cruda", "zanahoria cocida", "tomate"],
                "zanahoria cruda": ["zanahoria", "zanahoria cocida", "tomate"],
                "zanahoria cocida": ["zanahoria", "zanahoria cruda", "tomate"],
                "carrot": ["zanahoria", "zanahoria cruda", "zanahoria cocida"],
                "calabacín": ["zucchini", "calabacín", "pimiento"],
                "zucchini": ["calabacín", "pimiento"],
                "pimiento": ["ají", "morrón", "calabacín"],
                "ají": ["pimiento", "morrón", "calabacín"],
                "morrón": ["pimiento", "ají", "calabacín"],
                "pepper": ["pimiento", "ají", "morrón"],
                "tomate": ["jitomate", "tomate rojo", "zanahoria"],
                "jitomate": ["tomate", "tomate rojo", "zanahoria"],
                "tomate rojo": ["tomate", "jitomate", "zanahoria"],
                "tomato": ["tomate", "jitomate", "tomate rojo"],
                
                # 🍚 LEGUMBRES
                "lentejas": ["lentejas pardinas", "lentejas cocidas", "garbanzos"],
                "lentejas pardinas": ["lentejas", "lentejas cocidas", "garbanzos"],
                "lentejas cocidas": ["lentejas", "lentejas pardinas", "garbanzos"],
                "lentils": ["lentejas", "lentejas pardinas", "garbanzos"],
                "garbanzos": ["chickpeas", "garbanzo cocido", "lentejas"],
                "chickpeas": ["garbanzos", "garbanzo cocido", "lentejas"],
                "garbanzo cocido": ["garbanzos", "chickpeas", "lentejas"],
                "judías": ["alubias", "porotos", "frijoles", "garbanzos"],
                "alubias": ["judías", "porotos", "frijoles", "garbanzos"],
                "porotos": ["judías", "alubias", "frijoles", "garbanzos"],
                "frijoles": ["judías", "alubias", "porotos", "garbanzos"],
                "beans": ["judías", "alubias", "porotos", "frijoles"],
                "soja": ["habas de soja", "soya", "tofu"],
                "habas de soja": ["soja", "soya", "tofu"],
                "soya": ["soja", "habas de soja", "tofu"],
                "soy": ["soja", "soya", "habas de soja"],
                
                # 🍫 OTROS / DULCES
                "chocolate negro": ["cacao", "chocolate amargo", "miel"],
                "chocolate amargo": ["chocolate negro", "cacao", "miel"],
                "cacao": ["chocolate negro", "chocolate amargo", "miel"],
                "dark chocolate": ["chocolate negro", "chocolate amargo", "cacao"],
                "miel": ["miel natural", "néctar de abejas", "edulcorante"],
                "miel natural": ["miel", "néctar de abejas", "edulcorante"],
                "néctar de abejas": ["miel", "miel natural", "edulcorante"],
                "honey": ["miel", "miel natural", "edulcorante"],
                "azúcar": ["sugar", "azúcar blanca", "azúcar refinada", "edulcorante"],
                "sugar": ["azúcar", "azúcar blanca", "azúcar refinada", "edulcorante"],
                "azúcar blanca": ["azúcar", "sugar", "azúcar refinada", "edulcorante"],
                "azúcar refinada": ["azúcar", "azúcar blanca", "sacarosa", "edulcorante"],
                "azúcar refinado": ["azúcar", "azúcar blanca", "sacarosa", "edulcorante"],
                "sacarosa": ["azúcar", "azúcar refinada", "azúcar refinado", "edulcorante"],
                "edulcorante": ["stevia", "eritritol", "sucralosa", "miel"],
                "stevia": ["edulcorante", "eritritol", "sucralosa", "miel"],
                "eritritol": ["edulcorante", "stevia", "sucralosa", "miel"],
                "sucralosa": ["edulcorante", "stevia", "eritritol", "miel"],
                "sweetener": ["edulcorante", "stevia", "eritritol", "sucralosa"],
                
                # 💧 BEBIDAS
                "agua con gas": ["agua carbonatada", "soda", "agua"],
                "agua carbonatada": ["agua con gas", "soda", "agua"],
                "soda": ["agua con gas", "agua carbonatada", "agua"],
                "sparkling water": ["agua con gas", "agua carbonatada", "agua"],
                "refresco": ["bebida azucarada", "gaseosa", "agua"],
                "bebida azucarada": ["refresco", "gaseosa", "agua"],
                "gaseosa": ["refresco", "bebida azucarada", "agua"],
                "soft drink": ["refresco", "bebida azucarada", "gaseosa"],
                "café": ["espresso", "café solo", "americano", "té verde"],
                "espresso": ["café", "café solo", "americano", "té verde"],
                "café solo": ["café", "espresso", "americano", "té verde"],
                "americano": ["café", "coffee", "té verde"],
                "coffee": ["café", "espresso", "americano", "té verde"],
                "té verde": ["infusión de té", "matcha", "café"],
                "infusión de té": ["té verde", "matcha", "café"],
                "matcha": ["té verde", "infusión de té", "café"],
                "green tea": ["té verde", "infusión de té", "matcha"],
                
                # 💪 PROTEÍNA EN POLVO
                "proteína en polvo": ["claras de huevo", "huevos", "tofu"],
                "proteína polvo": ["claras de huevo", "huevos", "tofu"],
                "whey protein": ["claras de huevo", "huevos", "tofu"],
                "proteína whey": ["claras de huevo", "huevos", "tofu"],
                "proteína de suero": ["claras de huevo", "huevos", "tofu"]
            }
            
            # Buscar la mejor sustitución basada en el alimento no deseado
            mejor_sustitucion = None
            for alimento, alternativas in sustituciones.items():
                if alimento.lower() in disliked_food_lower or disliked_food_lower in alimento.lower():
                    mejor_sustitucion = alternativas[0]  # Usar la primera alternativa
                    logger.info(f"✅ Encontrada sustitución: {alimento} → {mejor_sustitucion}")
                    break
            
            # Si no hay sustitución específica, usar genérica
            if not mejor_sustitucion:
                # Extraer el alimento base (sin cantidades)
                alimento_base = disliked_food_lower.split()[0] if disliked_food_lower.split() else disliked_food_lower
                mejor_sustitucion = f"alternativa de {alimento_base}"
                logger.info(f"⚠️ Usando sustitución genérica: {mejor_sustitucion}")
            
            # Buscar y sustituir en las comidas correspondientes
            total_sustituciones = 0
            meal_type_lower = meal_type.lower()
            
            for meal in meals:
                if not isinstance(meal, dict):
                    continue
                    
                meal_name = meal.get("nombre", "").lower()
                foods = meal.get("alimentos", [])
                
                # Verificar si debemos modificar esta comida
                if meal_type_lower != "todos" and meal_type_lower not in meal_name:
                    continue
                
                # Buscar el alimento a sustituir
                for i, food_item in enumerate(foods):
                    if isinstance(food_item, str):
                        food_item_lower = food_item.lower()
                        # Buscar coincidencias parciales
                        if disliked_food_lower in food_item_lower or any(
                            palabra in food_item_lower for palabra in disliked_food_lower.split()
                        ):
                            # Extraer cantidad del alimento original si existe
                            # Formato típico: "300ml leche - 150kcal" o "40g avena - 150kcal"
                            match = re.match(r'^(\d+(?:\.\d+)?)\s*(ml|g|kg)?\s*', food_item)
                            cantidad = ""
                            if match:
                                cantidad = match.group(0).strip()
                            
                            # Crear sustitución manteniendo cantidad si es posible
                            if cantidad:
                                nuevo_alimento = f"{cantidad} {mejor_sustitucion}"
                            else:
                                nuevo_alimento = mejor_sustitucion
                            
                            foods[i] = nuevo_alimento
                            total_sustituciones += 1
                            changes.append(f"Sustituido en {meal.get('nombre', '')}: {food_item} → {nuevo_alimento}")
                            logger.info(f"✅ Sustituido: {food_item} → {nuevo_alimento} en {meal.get('nombre', '')}")
            
            if total_sustituciones == 0:
                return {
                    "success": False,
                    "message": f"No se encontró '{disliked_food}' en tu dieta. Por favor, verifica el nombre del alimento.",
                    "changes": []
                }
            
            # Actualizar current_diet con sustituciones
            current_diet["meals"] = meals
            dieta_regenerada = None  # Marcamos que usamos fallback
        
        # ==========================================
        # ACTUALIZAR DIETA FINAL
        # ==========================================
        if dieta_regenerada:
            # Usar dieta regenerada por GPT
            logger.info(f"✅ Usando dieta regenerada por GPT")
            
            # Obtener macros y calorías objetivo de la dieta actual
            macros_actuales = current_diet.get("macros", {})
            total_kcal_actual = current_diet.get("total_kcal", 0)
            
            # Actualizar current_diet con dieta regenerada por GPT
            current_diet["meals"] = dieta_regenerada
            current_diet["total_kcal"] = total_kcal_actual  # Mantener calorías objetivo
            current_diet["macros"] = macros_actuales  # Mantener macros objetivo
            changes.append(f"Dieta regenerada por GPT excluyendo '{disliked_food}'")
        else:
            # Ya se actualizó current_diet en la estrategia 2
            logger.info(f"✅ Usando sustituciones de lista predefinida")
        
        # Actualizar versión y timestamp
        current_diet["version"] = increment_diet_version(old_diet_version)
        current_diet["updated_at"] = datetime.utcnow().isoformat()
        
        # Guardar cambios
        await db_service.update_user_data(user_id, {
            "current_diet": current_diet
        }, db)
        
        # Añadir a alimentos no deseados
        disliked_foods = user_data.get("disliked_foods", [])
        if disliked_food not in disliked_foods:
            disliked_foods.append(disliked_food)
            await db_service.update_user_data(user_id, {
                "disliked_foods": disliked_foods
        }, db)
        
        # Añadir registro de modificación
        replacement_info = "GPT regeneración completa" if dieta_regenerada else mejor_sustitucion
        await db_service.add_modification_record(
            user_id,
            "food_substitution",
            {
                "previous_diet": previous_diet,  # Snapshot para revertir cambios
                "disliked_food": disliked_food,
                "meal_type": meal_type,
                "replacement": replacement_info,
                "strategy": "GPT" if dieta_regenerada else "lista_predefinida",
                "changes": changes
            },
            f"Sustitución de {disliked_food}",
            db
        )
        
        # Mensaje final según estrategia usada
        if dieta_regenerada:
            mensaje = f"He regenerado tu dieta completa excluyendo '{disliked_food}'. La nueva dieta se ajusta a tus calorías y macros objetivo, sin incluir ese alimento."
        else:
            if mejor_sustitucion and total_sustituciones > 0:
                mensaje = f"He sustituido '{disliked_food}' por '{mejor_sustitucion}' en {total_sustituciones} lugar(es) de tu dieta. Los macros se mantienen similares."
            else:
                mensaje = f"No se encontró '{disliked_food}' en tu dieta. Por favor, verifica el nombre del alimento."
        
        return {
            "success": True,
            "message": mensaje,
            "changes": changes,
            "plan_updated": True
        }
        
    except Exception as e:
        logger.error(f"Error en handle_substitute_food: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error sustituyendo alimento: {str(e)}",
            "changes": []
        }


async def handle_generate_alternatives(
    user_id: int,
    meal_type: str,
    db: Session = None
) -> Dict[str, Any]:
    """
    Handler para generar alternativas de comidas completas - VERSIÓN CON GPT PRIORITARIO
    Flujo: 1) Intentar GPT (regenerar comida completa excluyendo alimentos de la comida actual), 2) Fallback a alternativas predefinidas
    """
    try:
        logger.info(f"🍽️ Generando alternativas para comida: {meal_type}")
        
        # Obtener datos del usuario
        user_data = await db_service.get_user_complete_data(user_id, db)
        current_diet = user_data["current_diet"]
        
        # Validar estructura de dieta
        if not isinstance(current_diet, dict) or "meals" not in current_diet:
            return {
                "success": False,
                "message": "Estructura de dieta inválida. No se puede modificar.",
                "changes": []
            }
        
        # Obtener usuario para verificar si es premium
        from app.models import Usuario, Plan
        usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not usuario:
            return {
                "success": False,
                "message": "Usuario no encontrado",
                "changes": []
            }
        
        is_premium = bool(usuario.is_premium) or (usuario.plan_type == "PREMIUM")
        logger.info(f"💎 Usuario premium: {is_premium}")
        
        # Guardar snapshot de dieta antes de modificar (para revertir cambios)
        previous_diet = json.loads(json.dumps(current_diet))
        
        # Buscar la comida actual
        meals = current_diet.get("meals", [])
        meal_type_lower = meal_type.lower()
        current_meal = None
        
        for meal in meals:
            if isinstance(meal, dict):
                meal_name = meal.get("nombre", "").lower()
                if meal_type_lower in meal_name or meal_name in meal_type_lower:
                    current_meal = meal
                    break
        
        if not current_meal:
            return {
                "success": False,
                "message": f"No se encontró la comida '{meal_type}' en tu dieta.",
                "changes": []
            }
        
        # Obtener calorías y macros objetivo de la comida actual
        meal_kcal = current_meal.get("kcal", 0)
        meal_macros = current_meal.get("macros", {})
        meal_alimentos = current_meal.get("alimentos", [])
        
        # Extraer alimentos de la comida actual para excluirlos
        alimentos_excluidos = []
        for alimento in meal_alimentos:
            if isinstance(alimento, str):
                # Extraer nombre del alimento (sin cantidades)
                alimento_limpio = alimento.split('-')[0].strip() if '-' in alimento else alimento.strip()
                # Eliminar números y unidades
                alimento_limpio = re.sub(r'^\d+(?:\.\d+)?\s*(ml|g|kg|unidad|unidades)?\s*', '', alimento_limpio, flags=re.IGNORECASE)
                if alimento_limpio:
                    alimentos_excluidos.append(alimento_limpio)
        
        logger.info(f"📋 Comida actual: {current_meal.get('nombre', '')}")
        logger.info(f"   Calorías: {meal_kcal} kcal")
        logger.info(f"   Macros: P={meal_macros.get('proteinas', 0)}g, C={meal_macros.get('carbohidratos', 0)}g, G={meal_macros.get('grasas', 0)}g")
        logger.info(f"   Alimentos a excluir: {alimentos_excluidos}")
        
        # Guardar versión antes de modificar
        old_diet_version = current_diet.get("version", "1.0.0")
        changes = []
        
        # ==========================================
        # ESTRATEGIA 1: GPT (Solo para premium)
        # ==========================================
        nueva_comida_gpt = None
        
        if is_premium:
            try:
                logger.info(f"🤖 ESTRATEGIA 1: Regenerando {meal_type} con GPT excluyendo alimentos actuales...")
                
                # Obtener plan actual para datos del usuario
                current_plan = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.id.desc()).first()
                if not current_plan:
                    logger.warning(f"⚠️ No se encontró plan para usuario {user_id}, usando fallback")
                else:
                    # Preparar datos para GPT - generar solo UNA comida
                    datos_usuario = {
                        'altura': int(current_plan.altura) if current_plan.altura else 175,
                        'peso': float(current_plan.peso.replace("kg", "").strip()) if current_plan.peso else 75.0,
                        'edad': int(current_plan.edad) if current_plan.edad else 25,
                        'sexo': current_plan.sexo or 'masculino',
                        'objetivo': current_plan.objetivo_gym or 'ganar_musculo',
                        'nutrition_goal': current_plan.objetivo_nutricional or 'mantenimiento',
                        'experiencia': current_plan.experiencia or 'intermedio',
                        'materiales': current_plan.materiales.split(", ") if current_plan.materiales else ['gym_completo'],
                        'tipo_cuerpo': current_plan.tipo_cuerpo or 'mesomorfo',
                        'alergias': current_plan.alergias or 'Ninguna',
                        'restricciones': current_plan.restricciones_dieta or 'Ninguna',
                        'lesiones': current_plan.lesiones or 'Ninguna',
                        'nivel_actividad': current_plan.nivel_actividad or 'moderado',
                        'training_frequency': 4,
                        'training_days': ['lunes', 'martes', 'jueves', 'viernes'],
                        # 🔧 CRÍTICO: Pasar alimentos excluidos de la comida actual
                        'excluded_foods': alimentos_excluidos,
                        # 🔧 CRÍTICO: Pasar parámetros de la comida específica
                        'generate_single_meal': True,
                        'meal_type': meal_type,
                        'meal_target_kcal': meal_kcal,
                        'meal_target_macros': meal_macros
                    }
                    
                    # Llamar a GPT con timeout
                    try:
                        from app.utils.gpt import generar_comida_personalizada
                        nueva_comida_gpt = await asyncio.wait_for(
                            generar_comida_personalizada(datos_usuario),
                            timeout=GPT_TIMEOUT_SECONDS
                        )
                        
                        if nueva_comida_gpt and isinstance(nueva_comida_gpt, dict):
                            # Validar estructura de la comida generada
                            alimentos_generados = nueva_comida_gpt.get("alimentos", [])
                            kcal_generadas = nueva_comida_gpt.get("kcal", 0)
                            macros_generados = nueva_comida_gpt.get("macros", {})
                            
                            logger.info(f"✅ ESTRATEGIA 1 EXITOSA: Comida regenerada con GPT")
                            logger.info(f"   Comida: {nueva_comida_gpt.get('nombre', meal_type)}")
                            logger.info(f"   Calorías generadas: {kcal_generadas} kcal (objetivo: {meal_kcal} kcal)")
                            logger.info(f"   Macros generados: P={macros_generados.get('proteinas', 0)}g, C={macros_generados.get('carbohidratos', 0)}g, G={macros_generados.get('grasas', 0)}g")
                            logger.info(f"   Alimentos generados: {alimentos_generados}")
                            logger.info(f"   Alimentos excluidos: {alimentos_excluidos}")
                            
                            # Verificar que no contiene alimentos excluidos
                            contiene_excluido = False
                            for alimento_generado in alimentos_generados:
                                if isinstance(alimento_generado, str):
                                    alimento_generado_lower = alimento_generado.lower()
                                    for alimento_excluido in alimentos_excluidos:
                                        if alimento_excluido.lower() in alimento_generado_lower:
                                            contiene_excluido = True
                                            logger.warning(f"⚠️ GPT incluyó alimento excluido: '{alimento_generado}' (excluido: '{alimento_excluido}')")
                                            break
                                    if contiene_excluido:
                                        break
                            
                            if contiene_excluido:
                                logger.warning(f"⚠️ GPT incluyó alimento excluido, usando estrategia 2...")
                                nueva_comida_gpt = None
                            else:
                                logger.info(f"✅ Verificado: GPT excluyó correctamente todos los alimentos excluidos")
                                changes.append(f"Comida regenerada por GPT excluyendo alimentos anteriores: {', '.join(alimentos_excluidos)}")
                        else:
                            logger.warning(f"⚠️ GPT devolvió respuesta inválida, usando estrategia 2...")
                            nueva_comida_gpt = None
                            
                    except asyncio.TimeoutError:
                        logger.warning(f"⏱️ GPT timeout después de {GPT_TIMEOUT_SECONDS}s, usando estrategia 2...")
                        nueva_comida_gpt = None
                    except Exception as e:
                        logger.error(f"❌ Error con GPT: {e}")
                        logger.warning(f"⚠️ Usando estrategia 2 (alternativas predefinidas)...")
                        nueva_comida_gpt = None
                        
            except Exception as e:
                logger.error(f"❌ Error preparando datos para GPT: {e}")
                nueva_comida_gpt = None
        
        # ==========================================
        # ESTRATEGIA 2: Alternativas predefinidas (Fallback)
        # ==========================================
        if nueva_comida_gpt is None:
            logger.info(f"📋 ESTRATEGIA 2: Usando alternativas predefinidas para {meal_type}...")
            
            # Diccionario de alternativas predefinidas por tipo de comida
            alternativas_predefinidas = {
                "desayuno": [
                    {
                        "nombre": "Desayuno",
                        "kcal": meal_kcal,
                        "macros": meal_macros,
                        "alimentos": ["2 huevos revueltos", "2 rebanadas pan integral", "1 aguacate", "300ml leche semidesnatada"]
                    },
                    {
                        "nombre": "Desayuno",
                        "kcal": meal_kcal,
                        "macros": meal_macros,
                        "alimentos": ["50g avena", "1 plátano", "30g frutos secos", "250ml yogur natural"]
                    },
                    {
                        "nombre": "Desayuno",
                        "kcal": meal_kcal,
                        "macros": meal_macros,
                        "alimentos": ["3 rebanadas pan integral", "100g queso fresco", "200g tomate", "200ml leche semidesnatada"]
                    }
                ],
                "almuerzo": [
                    {
                        "nombre": "Almuerzo",
                        "kcal": meal_kcal,
                        "macros": meal_macros,
                        "alimentos": ["150g pollo a la plancha", "150g arroz integral", "200g brócoli", "1 cucharada aceite oliva"]
                    },
                    {
                        "nombre": "Almuerzo",
                        "kcal": meal_kcal,
                        "macros": meal_macros,
                        "alimentos": ["200g salmón", "150g quinoa", "200g espinacas", "1 cucharada aceite oliva"]
                    },
                    {
                        "nombre": "Almuerzo",
                        "kcal": meal_kcal,
                        "macros": meal_macros,
                        "alimentos": ["150g ternera magra", "200g patata asada", "200g ensalada", "1 cucharada aceite oliva"]
                    }
                ],
                "comida": [
                    {
                        "nombre": "Comida",
                        "kcal": meal_kcal,
                        "macros": meal_macros,
                        "alimentos": ["150g pollo a la plancha", "150g arroz integral", "200g brócoli", "1 cucharada aceite oliva"]
                    },
                    {
                        "nombre": "Comida",
                        "kcal": meal_kcal,
                        "macros": meal_macros,
                        "alimentos": ["200g salmón", "150g quinoa", "200g espinacas", "1 cucharada aceite oliva"]
                    },
                    {
                        "nombre": "Comida",
                        "kcal": meal_kcal,
                        "macros": meal_macros,
                        "alimentos": ["150g ternera magra", "200g patata asada", "200g ensalada", "1 cucharada aceite oliva"]
                    }
                ],
                "merienda": [
                    {
                        "nombre": "Merienda",
                        "kcal": meal_kcal,
                        "macros": meal_macros,
                        "alimentos": ["200ml yogur natural", "30g frutos secos", "1 plátano"]
                    },
                    {
                        "nombre": "Merienda",
                        "kcal": meal_kcal,
                        "macros": meal_macros,
                        "alimentos": ["1 plátano", "20g mantequilla de almendras", "200ml leche semidesnatada"]
                    },
                    {
                        "nombre": "Merienda",
                        "kcal": meal_kcal,
                        "macros": meal_macros,
                        "alimentos": ["100g queso fresco", "200g frutos rojos", "30g frutos secos"]
                    }
                ],
                "cena": [
                    {
                        "nombre": "Cena",
                        "kcal": meal_kcal,
                        "macros": meal_macros,
                        "alimentos": ["200g pescado blanco", "200g verduras al vapor", "100g quinoa", "1 cucharada aceite oliva"]
                    },
                    {
                        "nombre": "Cena",
                        "kcal": meal_kcal,
                        "macros": meal_macros,
                        "alimentos": ["150g pollo a la plancha", "200g ensalada", "100g aguacate", "1 cucharada aceite oliva"]
                    },
                    {
                        "nombre": "Cena",
                        "kcal": meal_kcal,
                        "macros": meal_macros,
                        "alimentos": ["200g salmón", "200g espinacas", "150g arroz integral", "1 cucharada aceite oliva"]
                    }
                ],
                "snack": [
                    {
                        "nombre": "Snack",
                        "kcal": meal_kcal,
                        "macros": meal_macros,
                        "alimentos": ["200ml yogur natural", "30g frutos secos", "1 plátano"]
                    },
                    {
                        "nombre": "Snack",
                        "kcal": meal_kcal,
                        "macros": meal_macros,
                        "alimentos": ["1 plátano", "20g mantequilla de almendras", "200ml leche semidesnatada"]
                    },
                    {
                        "nombre": "Snack",
                        "kcal": meal_kcal,
                        "macros": meal_macros,
                        "alimentos": ["100g queso fresco", "200g frutos rojos", "30g frutos secos"]
                    }
                ]
            }
            
            # Obtener alternativas para el tipo de comida
            alternativas = alternativas_predefinidas.get(meal_type_lower, [])
            
            if not alternativas:
                # Si no hay alternativas específicas, usar las de "snack"
                alternativas = alternativas_predefinidas.get("snack", [])
            
            # Usar la primera alternativa
            nueva_comida_gpt = alternativas[0] if alternativas else None
            
            if nueva_comida_gpt:
                alimentos_fallback = nueva_comida_gpt.get('alimentos', [])
                logger.info(f"✅ Usando alternativa predefinida #1 para {meal_type}")
                logger.info(f"   Comida: {nueva_comida_gpt.get('nombre', meal_type)}")
                logger.info(f"   Calorías: {nueva_comida_gpt.get('kcal', 0)} kcal (objetivo: {meal_kcal} kcal)")
                logger.info(f"   Macros: P={nueva_comida_gpt.get('macros', {}).get('proteinas', 0)}g, C={nueva_comida_gpt.get('macros', {}).get('carbohidratos', 0)}g, G={nueva_comida_gpt.get('macros', {}).get('grasas', 0)}g")
                logger.info(f"   Alimentos: {alimentos_fallback}")
                changes.append(f"Comida reemplazada por alternativa predefinida: {', '.join(alimentos_fallback)}")
            else:
                return {
                    "success": False,
                    "message": f"No se encontraron alternativas predefinidas para '{meal_type}'.",
                    "changes": []
                }
        
        # ==========================================
        # ACTUALIZAR DIETA
        # ==========================================
        if nueva_comida_gpt:
            logger.info(f"🔄 Actualizando dieta con nueva comida para {meal_type}...")
            
            # Reemplazar la comida actual con la nueva
            comida_encontrada = False
            for i, meal in enumerate(meals):
                if isinstance(meal, dict):
                    meal_name = meal.get("nombre", "").lower()
                    if meal_type_lower in meal_name or meal_name in meal_type_lower:
                        # Mantener el nombre original de la comida
                        nombre_original = meal.get("nombre", meal_type.capitalize())
                        alimentos_anteriores = meal.get("alimentos", [])
                        
                        nueva_comida_gpt["nombre"] = nombre_original
                        meals[i] = nueva_comida_gpt
                        comida_encontrada = True
                        
                        logger.info(f"✅ Comida reemplazada en posición {i}")
                        logger.info(f"   Anterior: {nombre_original} - {', '.join(alimentos_anteriores[:3])}...")
                        logger.info(f"   Nueva: {nueva_comida_gpt.get('nombre')} - {', '.join(nueva_comida_gpt.get('alimentos', [])[:3])}...")
                        break
            
            if not comida_encontrada:
                logger.warning(f"⚠️ No se encontró la comida '{meal_type}' en meals para reemplazar")
                return {
                    "success": False,
                    "message": f"No se encontró la comida '{meal_type}' para actualizar.",
                    "changes": []
                }
            
            # Actualizar current_diet
            current_diet["meals"] = meals
            current_diet["version"] = increment_diet_version(old_diet_version)
            current_diet["updated_at"] = datetime.utcnow().isoformat()
            
            logger.info(f"💾 Guardando cambios en base de datos...")
            logger.info(f"   Versión anterior: {old_diet_version}")
            logger.info(f"   Versión nueva: {current_diet['version']}")
            logger.info(f"   Timestamp: {current_diet['updated_at']}")
            
            # Guardar cambios
            await db_service.update_user_data(user_id, {
                "current_diet": current_diet
            }, db)
            
            logger.info(f"✅ Cambios guardados exitosamente en base de datos")
            
            # Añadir registro de modificación
            await db_service.add_modification_record(
                user_id,
                "meal_alternatives_generated",
                {
                    "previous_diet": previous_diet,  # Snapshot para revertir cambios
                    "meal_type": meal_type,
                    "strategy": "GPT" if nueva_comida_gpt and "GPT" in str(changes) else "predefinida",
                    "changes": changes
                },
                f"Alternativa generada para {meal_type}",
                db
            )
            
            # Mensaje final
            if "GPT" in str(changes):
                mensaje = f"He regenerado tu {meal_type} completamente con GPT, excluyendo los alimentos anteriores. La nueva comida se ajusta a tus calorías y macros objetivo."
            else:
                mensaje = f"He reemplazado tu {meal_type} por una alternativa predefinida que se ajusta a tus calorías y macros objetivo."
            
            return {
                "success": True,
                "message": mensaje,
                "changes": changes,
                "plan_updated": True
            }
        else:
            return {
                "success": False,
                "message": f"No se pudo generar una alternativa para '{meal_type}'.",
                "changes": []
            }
        
    except Exception as e:
        logger.error(f"Error en handle_generate_alternatives: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error generando alternativas: {str(e)}",
            "changes": []
        }


async def handle_simplify_diet(
    user_id: int,
    complexity_level: str,
    db: Session
) -> Dict[str, Any]:
    """
    Handler para simplificar dieta
    """
    return {
        "success": False,
        "message": "Función de simplificación de dieta no implementada aún",
        "changes": []
    }


async def handle_adjust_menstrual_cycle(
    user_id: int,
    cycle_phase: str,
    db: Session
) -> Dict[str, Any]:
    """
    Handler para ajuste del ciclo menstrual
    """
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
    Sustituye un ejercicio específico por otro alternativo - VERSIÓN CORREGIDA
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
        
        # Guardar snapshot de rutina antes de modificar (para revertir cambios)
        previous_routine = json.loads(json.dumps(current_routine))
        
        # 🔧 FIX: Guardar versión antes de modificar
        old_routine_version = current_routine.get("version", "1.0.0")
        
        changes = []
        exercises = current_routine.get("exercises", [])
        
        # Mapeo de ejercicios alternativos por grupo muscular
        exercise_alternatives = {
            "pecho": {
                "peso_libre": ["Press de pecho con mancuernas", "Aperturas con mancuernas", "Press inclinado con mancuernas"],
                "cuerpo_libre": ["Flexiones", "Flexiones inclinadas", "Flexiones diamante"],
                "maquinas": ["Press de pecho en máquina", "Aperturas en máquina"],
                "bandas": ["Press de pecho con bandas", "Cruces con bandas"]
            },
            "espalda": {
                "peso_libre": ["Remo con mancuerna", "Peso muerto rumano", "Dominadas asistidas"],
                "cuerpo_libre": ["Dominadas", "Remo invertido", "Superman"],
                "maquinas": ["Remo en máquina", "Jalón al pecho"],
                "bandas": ["Remo con bandas", "Jalón con bandas"]
            },
            "hombros": {
                "peso_libre": ["Elevaciones laterales", "Press militar con mancuernas"],
                "cuerpo_libre": ["Flexiones pike", "Handstand push-ups"],
                "maquinas": ["Press de hombros en máquina"],
                "bandas": ["Elevaciones con bandas"]
            },
            "piernas": {
                "peso_libre": ["Sentadillas con mancuernas", "Zancadas", "Peso muerto"],
                "cuerpo_libre": ["Sentadillas", "Zancadas", "Puente de glúteos"],
                "maquinas": ["Prensa de piernas", "Extensión de cuádriceps"],
                "bandas": ["Sentadillas con bandas"]
            },
            "brazos": {
                "peso_libre": ["Curl de bíceps", "Extensiones de tríceps", "Martillo"],
                "cuerpo_libre": ["Flexiones diamante", "Dips"],
                "maquinas": ["Curl en máquina"],
                "bandas": ["Curl con bandas"]
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
                    # Buscar en cualquier equipamiento
                    for eq_alternatives in exercise_alternatives.get(target_muscles, {}).values():
                        alternatives.extend(eq_alternatives)
                
                if alternatives:
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
                else:
                    changes.append(f"No se encontraron alternativas para {exercise_name}")
        
        if not exercise_found:
            changes.append(f"No se encontró el ejercicio '{exercise_to_replace}' en la rutina")
        
        # Actualizar versión y timestamp
        current_routine["version"] = increment_routine_version(old_routine_version)  # 🔧 FIX
        current_routine["updated_at"] = datetime.utcnow().isoformat()
        
        # Guardar cambios
        await db_service.update_user_data(user_id, {
            "current_routine": current_routine
        }, db)
        
        await db_service.add_modification_record(
            user_id,
            "exercise_substitution",
            {
                "previous_routine": previous_routine,  # Snapshot para revertir cambios
                "exercise_to_replace": exercise_to_replace,
                "replacement_reason": replacement_reason,
                "changes": changes
            },
            f"Sustitución de ejercicio: {exercise_to_replace}",
            db
        )
        
        return {
            "success": True,
            "message": f"Ejercicio sustituido correctamente",
            "changes": changes
        }
        
    except Exception as e:
        logger.error(f"Error en handle_substitute_exercise: {e}", exc_info=True)
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
    Adapta la rutina cuando falta equipamiento específico - VERSIÓN CON GPT
    🔧 NUEVO: Ahora GPT genera una rutina completamente nueva evitando el equipamiento faltante
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
        
        # 🔧 FIX: Guardar versión ANTES de modificar
        previous_routine = json.loads(json.dumps(current_routine))
        old_routine_version = current_routine.get("version", "1.0.0")
        
        # Mapear equipamiento faltante a descripción legible
        equipment_mapping = {
            "press_banca": "banco de press",
            "sentadilla_rack": "rack de sentadillas",
            "pesas_libres": "pesas libres",
            "maquinas": "máquinas",
            "cables": "poleas y cables",
            "poleas": "poleas y cables",
            "smith_machine": "máquina Smith",
            "rack_multiuso": "rack multipropósito",
            "barras": "barras olímpicas",
            "discos": "discos de peso",
            "mancuernas": "mancuernas",
            "kettlebells": "kettlebells",
            "bandas_elasticas": "bandas elásticas",
            "step": "step o plataforma",
            "banco": "banco de ejercicios",
            "colchoneta": "colchoneta"
        }
        
        # Mapear equipamiento disponible a descripción legible
        available_mapping = {
            "peso_libre": "peso libre (mancuernas, barras si están disponibles)",
            "cuerpo_libre": "solo peso corporal",
            "bandas": "bandas elásticas",
            "kettlebell": "kettlebells",
            "maquinas_basicas": "máquinas básicas",
            "cables": "poleas y cables",
            "step": "step o plataforma",
            "banco": "banco de ejercicios",
            "colchoneta": "colchoneta",
            "cualquiera": "cualquier equipamiento disponible"
        }
        
        missing_equipment_readable = equipment_mapping.get(missing_equipment, missing_equipment)
        available_equipment_readable = available_mapping.get(available_equipment, available_equipment)
        
        logger.info(f"🏋️ GENERANDO RUTINA CON GPT PARA EQUIPAMIENTO:")
        logger.info(f"   Equipamiento faltante: {missing_equipment_readable}")
        logger.info(f"   Equipamiento disponible: {available_equipment_readable}")
        logger.info(f"   Ejercicios afectados: {affected_exercises or 'todos los que requieran el equipamiento faltante'}")
        
        # Obtener datos del Plan para pasar a GPT
        from app.models import Plan
        plan_actual = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.id.desc()).first()
        
        if not plan_actual:
            logger.error(f"❌ No se encontró Plan para usuario {user_id}")
            return {
                "success": False,
                "message": "No se encontró plan del usuario. Completa el onboarding primero.",
                "changes": []
            }
        
        # Preparar materiales actualizados (sin el faltante, con el disponible)
        materiales_originales = plan_actual.materiales or 'gym_completo'
        # Si materiales_originales es una lista, convertirla a string
        if isinstance(materiales_originales, list):
            materiales_originales = ', '.join(materiales_originales)
        
        # Mapeo de equipamiento faltante a palabras clave para filtrar
        equipment_keywords_remove = {
            "press_banca": ["banco", "press banca", "bench"],
            "sentadilla_rack": ["rack", "sentadilla rack"],
            "barras": ["barra", "bar"],
            "mancuernas": ["mancuernas", "dumbbells"],
            "maquinas": ["máquina", "machine", "maquinas"],
            "cables": ["cable", "polea", "cables"],
            "kettlebells": ["kettlebell", "kettlebells"],
            "bandas_elasticas": ["bandas", "elasticas"],
            "smith_machine": ["smith", "smith machine"],
            "rack_multiuso": ["rack", "multiuso"]
        }
        
        # Filtrar el equipamiento faltante del string de materiales
        materiales_actualizados = materiales_originales.lower()
        
        # Remover palabras clave relacionadas con el equipamiento faltante
        keywords_to_remove = equipment_keywords_remove.get(missing_equipment, [missing_equipment.lower()])
        for keyword in keywords_to_remove:
            materiales_actualizados = materiales_actualizados.replace(keyword, '').replace(',,', ',').strip()
        
        # Limpiar espacios y comas dobles
        materiales_actualizados = materiales_actualizados.replace('  ', ' ').replace(', ,', ',').strip(', ')
        
        # Si quedó vacío o es muy corto, usar el equipamiento disponible como base
        if not materiales_actualizados or len(materiales_actualizados) < 3:
            materiales_actualizados = available_equipment_readable
        else:
            # Añadir el equipamiento disponible si no está ya presente
            if available_equipment_readable.lower() not in materiales_actualizados.lower():
                materiales_actualizados = f"{materiales_actualizados}, {available_equipment_readable}"
        
        logger.info(f"📦 Materiales actualizados: '{materiales_originales}' → '{materiales_actualizados}'")
        
        # Preparar datos para GPT con información del equipamiento
        datos_gpt = {
            'altura': plan_actual.altura or 175,
            'peso': float(plan_actual.peso) if plan_actual.peso else 75.0,
            'edad': plan_actual.edad or 25,
            'sexo': plan_actual.sexo or 'masculino',
            'objetivo': plan_actual.objetivo_gym or (plan_actual.objetivo or 'ganar_musculo'),
            'gym_goal': plan_actual.objetivo_gym or 'ganar_musculo',
            'nutrition_goal': plan_actual.objetivo_nutricional or (plan_actual.objetivo_dieta or 'mantenimiento'),
            'experiencia': plan_actual.experiencia or 'principiante',
            'materiales': materiales_actualizados,  # 🔧 NUEVO: Materiales actualizados sin el faltante
            'tipo_cuerpo': plan_actual.tipo_cuerpo or 'mesomorfo',
            'alergias': plan_actual.alergias or 'Ninguna',
            'restricciones': plan_actual.restricciones_dieta or 'Ninguna',
            'lesiones': plan_actual.lesiones or 'Ninguna',
            'nivel_actividad': plan_actual.nivel_actividad or 'moderado',
            'training_frequency': 4,
            'training_days': ['lunes', 'martes', 'jueves', 'viernes'],
            # 🔧 NUEVO: Información específica del equipamiento
            'missing_equipment': missing_equipment_readable,
            'available_equipment': available_equipment_readable,
            'affected_exercises': affected_exercises or f"Ejercicios que requieren {missing_equipment_readable}"
        }
        
        # Llamar a GPT para generar rutina nueva sin el equipamiento faltante
        from app.utils.gpt import generar_plan_personalizado
        
        exercises_nuevos = None  # Variable para controlar si GPT funcionó
        
        try:
            logger.info(f"🤖 Generando rutina con GPT evitando {missing_equipment_readable}...")
            plan_generado = await generar_plan_personalizado(datos_gpt)
            
            # Extraer solo la rutina (no necesitamos regenerar dieta)
            rutina_gpt = plan_generado.get("rutina", {})
            dias_rutina = rutina_gpt.get("dias", [])
            
            if not dias_rutina:
                raise ValueError("GPT no generó rutina válida")
            
            # Convertir formato de "dias" a "exercises" (formato que usa current_routine)
            exercises_nuevos = []
            ejercicios_rechazados = []
            
            # Keywords a evitar según el equipamiento faltante
            equipment_keywords_to_avoid = {
                "press_banca": ["press banca", "bench press", "press con barra"],
                "sentadilla_rack": ["sentadilla con barra", "squat con barra", "rack"],
                "barras": ["barra", "bar", "press con barra", "remo con barra", "curl con barra", "dominadas", "pull ups"],
                "mancuernas": ["mancuernas", "dumbbells", "press con mancuernas", "remo con mancuernas"],
                "maquinas": ["máquina", "machine", "prensa", "extensión de cuádriceps"],
                "cables": ["cable", "polea", "cruce de cables"],
                "kettlebells": ["kettlebell", "kettle bell"]
            }
            
            keywords_to_avoid = equipment_keywords_to_avoid.get(missing_equipment, [missing_equipment_readable.lower()])
            
            for dia in dias_rutina:
                nombre_dia = dia.get("dia", "")
                grupos_musculares = dia.get("grupos_musculares", "")
                ejercicios_dia = dia.get("ejercicios", [])
                
                for ejercicio in ejercicios_dia:
                    nombre_ejercicio = ejercicio.get("nombre", "")
                    nombre_ejercicio_lower = nombre_ejercicio.lower()
                    
                    # Validar que el ejercicio NO requiera el equipamiento faltante
                    requires_missing_equipment = any(kw in nombre_ejercicio_lower for kw in keywords_to_avoid)
                    
                    if requires_missing_equipment:
                        ejercicios_rechazados.append(nombre_ejercicio)
                        logger.warning(f"⚠️ GPT generó ejercicio que requiere {missing_equipment_readable}: {nombre_ejercicio} - Omitiendo")
                        continue  # Omitir este ejercicio
                    
                    exercises_nuevos.append({
                        "name": nombre_ejercicio,
                        "sets": ejercicio.get("series", 3),
                        "reps": ejercicio.get("repeticiones", "10-12"),
                        "weight": "moderado",
                        "day": nombre_dia
                    })
            
            if ejercicios_rechazados:
                logger.warning(f"⚠️ Se omitieron {len(ejercicios_rechazados)} ejercicios que requerían {missing_equipment_readable}: {ejercicios_rechazados}")
            
            if not exercises_nuevos or len(exercises_nuevos) < 10:
                logger.warning(f"⚠️ Rutina generada tiene muy pocos ejercicios ({len(exercises_nuevos)}), forzando fallback...")
                raise ValueError(f"Rutina generada tiene muy pocos ejercicios ({len(exercises_nuevos)})")
            
            logger.info(f"✅ Rutina generada con GPT evitando {missing_equipment_readable}: {len(exercises_nuevos)} ejercicios válidos")
            
            # Preparar cambios para el registro
            changes = [
                f"Rutina regenerada con GPT evitando {missing_equipment_readable}",
                f"Equipamiento disponible: {available_equipment_readable}",
                f"Total ejercicios: {len(exercises_nuevos)}"
            ]
            
        except Exception as e_gpt:
            logger.error(f"❌ Error generando rutina con GPT: {e_gpt}")
            logger.warning(f"⚠️ Fallando a método tradicional de filtrado...")
            exercises_nuevos = None  # GPT falló, usar fallback
        
        # FALLBACK: Si GPT falló, usar método tradicional de filtrado
        if exercises_nuevos is None:
            logger.info(f"📋 Usando método tradicional de filtrado...")
            changes = []
            exercises = current_routine.get("exercises", [])
            
            # Mapeo de equipamiento faltante a keywords de ejercicios a evitar
            equipment_keywords_to_avoid = {
                "press_banca": ["press banca", "bench press", "press con barra"],
                "sentadilla_rack": ["sentadilla con barra", "squat con barra", "rack"],
                "barras": ["barra", "bar", "press con barra", "remo con barra", "curl con barra"],
                "mancuernas": ["mancuernas", "dumbbells", "press con mancuernas", "remo con mancuernas"],
                "maquinas": ["máquina", "machine", "prensa", "extensión de cuádriceps"],
                "cables": ["cable", "polea", "cruce de cables"],
                "kettlebells": ["kettlebell", "kettle bell"]
            }
            
            # Alternativas básicas por equipamiento disponible
            equipment_alternatives = {
                "cuerpo_libre": ["Flexiones", "Sentadillas", "Dominadas", "Fondos", "Plancha"],
                "bandas": ["Curl con bandas", "Remo con bandas", "Press con bandas"],
                "mancuernas": ["Press con mancuernas", "Curl con mancuernas", "Remo con mancuernas"]
            }
            
            keywords_to_avoid = equipment_keywords_to_avoid.get(missing_equipment, [])
            alternatives = equipment_alternatives.get(available_equipment, [])
            
            ejercicios_filtrados = []
            ejercicios_eliminados = []
            
            # Filtrar ejercicios que requieren el equipamiento faltante
            for ejercicio in exercises:
                if isinstance(ejercicio, dict):
                    exercise_name = ejercicio.get("name", "")
                else:
                    exercise_name = str(ejercicio)
                
                exercise_name_lower = exercise_name.lower()
                needs_removal = any(kw in exercise_name_lower for kw in keywords_to_avoid)
                
                if needs_removal:
                    ejercicios_eliminados.append(exercise_name)
                    changes.append(f"Eliminado: {exercise_name} (requiere {missing_equipment_readable})")
                else:
                    ejercicios_filtrados.append(ejercicio)
            
            # Añadir alternativas si se eliminaron ejercicios
            if ejercicios_eliminados and alternatives:
                for alt in alternatives[:min(len(ejercicios_eliminados), 3)]:
                    ejercicios_filtrados.append({
                        "name": alt,
                        "sets": 3,
                        "reps": "10-12",
                        "weight": "moderado",
                        "notes": f"Alternativa usando {available_equipment_readable}"
                    })
                    changes.append(f"Añadido: {alt}")
            
            exercises_nuevos = ejercicios_filtrados
        
        # Actualizar rutina con el método que funcionó
        if exercises_nuevos is not None:
            current_routine["exercises"] = exercises_nuevos
        
        current_routine["version"] = increment_routine_version(old_routine_version)
        current_routine["updated_at"] = datetime.utcnow().isoformat()
        
        # Guardar cambios
        await db_service.update_user_data(user_id, {
            "current_routine": current_routine
        }, db)
        
        # Añadir registro de modificación
        await db_service.add_modification_record(
            user_id,
            "equipment_adaptation",
            {
                "missing_equipment": missing_equipment,
                "available_equipment": available_equipment,
                "affected_exercises": affected_exercises,
                "previous_routine": previous_routine,
                "changes": changes
            },
            f"Adaptación por equipamiento: {missing_equipment_readable}",
            db
        )
        
        return {
            "success": True,
            "message": f"Rutina regenerada evitando {missing_equipment_readable}",
            "changes": changes
        }
        
    except Exception as e:
        logger.error(f"Error en handle_modify_routine_equipment: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error adaptando rutina: {str(e)}",
            "changes": []
        }


# ==================== FIN DEL ARCHIVO COMPLETO ====================