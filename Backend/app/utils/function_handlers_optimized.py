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
    food_to_replace: str,
    replacement_food: str,
    db: Session
) -> Dict[str, Any]:
    """
    Handler para sustitución de alimentos con validación de alergias - VERSIÓN CORREGIDA
    """
    try:
        logger.info(f"Sustituyendo alimento: {food_to_replace} → {replacement_food}")
        
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
        
        # 🔧 FIX: Guardar versión antes de modificar
        old_diet_version = current_diet.get("version", "1.0.0")
        
        changes = []
        meals = current_diet.get("meals", [])
        
        # Buscar y sustituir el alimento en todas las comidas
        for meal in meals:
            if isinstance(meal, dict):
                meal_name = meal.get("nombre", "")
                foods = meal.get("alimentos", [])
                
                # Buscar el alimento a sustituir
                for i, food_item in enumerate(foods):
                    if isinstance(food_item, str) and food_to_replace.lower() in food_item.lower():
                        # Sustituir el alimento manteniendo formato de cantidad si existe
                        foods[i] = replacement_food
                        changes.append(f"Sustituido en {meal_name}: {food_to_replace} → {replacement_food}")
        
        # Actualizar versión y timestamp
        current_diet["version"] = increment_diet_version(old_diet_version)  # 🔧 FIX
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
            "message": f"Alimento sustituido correctamente",
            "changes": changes
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
    db: Session
) -> Dict[str, Any]:
    """
    Handler para generar alternativas de comidas
    """
    return {
        "success": False,
        "message": "Función de alternativas de comidas no implementada aún",
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