"""
Calculadora de nutrición: TMB, TDEE y macronutrientes

Este módulo proporciona funciones para calcular:
- TMB (Tasa Metabólica Basal) usando la fórmula de Mifflin-St Jeor
- TDEE (Total Daily Energy Expenditure) = calorías de mantenimiento
- Distribución de macronutrientes según objetivo

Autor: YourGains AI
Fecha: 2025-10-21
"""

from typing import Dict, Tuple
import logging
import re

logger = logging.getLogger(__name__)


def parse_peso(peso_str: str) -> float:
    """
    Extrae el número del string de peso
    
    Ejemplos:
        - "75kg" → 75.0
        - "75" → 75.0
        - "75.5 kg" → 75.5
        - "175.5" → 175.5
        
    Args:
        peso_str: String con el peso (puede incluir unidades)
        
    Returns:
        Peso en kg como float
    """
    try:
        # Extraer números (incluyendo decimales) del string
        match = re.search(r'(\d+\.?\d*)', str(peso_str))
        if match:
            peso = float(match.group(1))
            logger.debug(f"✅ Peso parseado: '{peso_str}' → {peso}kg")
            return peso
        logger.warning(f"⚠️ No se pudo parsear peso '{peso_str}', usando 75kg por defecto")
        return 75.0  # Valor por defecto
    except Exception as e:
        logger.warning(f"❌ Error parseando peso '{peso_str}': {e}. Usando 75kg por defecto")
        return 75.0


def calculate_tmb(peso: float, altura: int, edad: int, sexo: str) -> float:
    """
    Calcula la Tasa Metabólica Basal usando la fórmula de Mifflin-St Jeor
    
    La TMB es la cantidad de calorías que tu cuerpo necesita en reposo absoluto
    para mantener las funciones vitales (respiración, circulación, etc.)
    
    Fórmula de Mifflin-St Jeor (más precisa que Harris-Benedict):
    - Hombres: TMB = (10 × peso_kg) + (6.25 × altura_cm) - (5 × edad) + 5
    - Mujeres: TMB = (10 × peso_kg) + (6.25 × altura_cm) - (5 × edad) - 161
    
    Args:
        peso: Peso en kg (float)
        altura: Altura en cm (int)
        edad: Edad en años (int)
        sexo: "masculino" o "femenino"
        
    Returns:
        TMB en kcal/día (float)
    """
    try:
        sexo_lower = sexo.lower()
        
        if sexo_lower in ["masculino", "hombre", "male", "m"]:
            tmb = (10 * peso) + (6.25 * altura) - (5 * edad) + 5
            logger.debug(f"🔢 TMB (masculino) = (10 × {peso}) + (6.25 × {altura}) - (5 × {edad}) + 5")
        elif sexo_lower in ["femenino", "mujer", "female", "f"]:
            tmb = (10 * peso) + (6.25 * altura) - (5 * edad) - 161
            logger.debug(f"🔢 TMB (femenino) = (10 × {peso}) + (6.25 × {altura}) - (5 × {edad}) - 161")
        else:
            logger.warning(f"⚠️ Sexo no reconocido '{sexo}', usando fórmula masculina")
            tmb = (10 * peso) + (6.25 * altura) - (5 * edad) + 5
        
        logger.info(f"🔥 TMB calculada: {int(tmb)} kcal/día (peso={peso}kg, altura={altura}cm, edad={edad}, sexo={sexo})")
        return tmb
        
    except Exception as e:
        logger.error(f"❌ Error calculando TMB: {e}")
        return 1800.0  # Valor por defecto razonable


def calculate_tdee(tmb: float, nivel_actividad: str) -> int:
    """
    Calcula el TDEE (Total Daily Energy Expenditure) = calorías de mantenimiento
    
    El TDEE es la cantidad total de calorías que quemas en un día incluyendo
    actividad física, digestión, etc.
    
    TDEE = TMB × factor_actividad
    
    Factores de actividad (basados en investigación científica):
    - sedentario: 1.2 (poco o ningún ejercicio)
    - ligero: 1.375 (ejercicio ligero 1-3 días/semana)
    - moderado: 1.55 (ejercicio moderado 3-5 días/semana)
    - activo: 1.725 (ejercicio intenso 6-7 días/semana)
    - muy_activo: 1.9 (ejercicio muy intenso + trabajo físico)
    
    Args:
        tmb: Tasa Metabólica Basal en kcal/día
        nivel_actividad: Nivel de actividad física diaria
        
    Returns:
        TDEE en kcal/día (int)
    """
    factores_actividad = {
        "sedentario": 1.2,
        "ligero": 1.375,
        "moderado": 1.55,
        "activo": 1.725,
        "muy_activo": 1.9
    }
    
    nivel_lower = nivel_actividad.lower().replace(" ", "_")
    factor = factores_actividad.get(nivel_lower, 1.55)
    tdee = int(tmb * factor)
    
    logger.info(f"🏃 Nivel actividad: {nivel_actividad} → Factor: {factor}x")
    logger.info(f"🔢 TDEE = TMB ({int(tmb)}) × {factor} = {tdee} kcal/día")
    logger.info(f"⚖️ TDEE (calorías de mantenimiento): {tdee} kcal/día")
    
    return tdee


def calculate_maintenance_calories(user_data: Dict) -> int:
    """
    Función principal: calcula las calorías de mantenimiento del usuario
    
    Este es el número de calorías que el usuario necesita consumir para
    mantener su peso actual con su nivel de actividad.
    
    Args:
        user_data: Diccionario con datos del usuario:
            - peso: str (ej: "75kg") o float
            - altura: int (ej: 175)
            - edad: int (ej: 25)
            - sexo: str (ej: "masculino")
            - nivel_actividad: str (ej: "moderado")
            
    Returns:
        Calorías de mantenimiento (TDEE) en kcal/día
    """
    try:
        # Extraer y parsear datos
        peso_str = user_data.get("peso", "75")
        peso_kg = parse_peso(peso_str)
        altura_cm = int(user_data.get("altura", 175))
        edad_años = int(user_data.get("edad", 25))
        sexo = user_data.get("sexo", "masculino")
        nivel_actividad = user_data.get("nivel_actividad", "moderado")
        
        logger.info("=" * 60)
        logger.info("📊 CALCULANDO CALORÍAS DE MANTENIMIENTO")
        logger.info("=" * 60)
        logger.info(f"👤 Perfil del usuario:")
        logger.info(f"   • Peso: {peso_kg}kg")
        logger.info(f"   • Altura: {altura_cm}cm")
        logger.info(f"   • Edad: {edad_años} años")
        logger.info(f"   • Sexo: {sexo}")
        logger.info(f"   • Nivel actividad: {nivel_actividad}")
        logger.info("-" * 60)
        
        # Paso 1: Calcular TMB
        tmb = calculate_tmb(peso_kg, altura_cm, edad_años, sexo)
        
        # Paso 2: Calcular TDEE
        tdee = calculate_tdee(tmb, nivel_actividad)
        
        logger.info("=" * 60)
        logger.info(f"✅ RESULTADO: {tdee} kcal/día (mantenimiento)")
        logger.info("=" * 60)
        
        return tdee
        
    except Exception as e:
        logger.error(f"❌ Error calculando calorías de mantenimiento: {e}")
        logger.error(f"   user_data recibido: {user_data}")
        logger.warning("⚠️ Usando valor por defecto: 2500 kcal/día")
        return 2500  # Valor por defecto razonable


def calculate_calories_for_goal(tdee: int, goal: str) -> int:
    """
    Calcula las calorías objetivo según el goal nutricional
    
    Args:
        tdee: Calorías de mantenimiento (TDEE)
        goal: Objetivo nutricional ("volumen", "definicion", "mantenimiento", etc.)
        
    Returns:
        Calorías objetivo en kcal/día
    """
    ajustes_por_objetivo = {
        "volumen": 300,          # Superávit para ganar masa muscular
        "definicion": -300,      # Déficit para perder grasa
        "definición": -300,      # Variante con tilde
        "mantenimiento": 0,      # Mantener peso actual
        "fuerza": 200,          # Superávit moderado para fuerza
        "resistencia": -100      # Déficit ligero para resistencia
    }
    
    goal_lower = goal.lower() if goal else "mantenimiento"
    ajuste = ajustes_por_objetivo.get(goal_lower, 0)
    calorias_objetivo = tdee + ajuste
    
    logger.info("-" * 60)
    logger.info(f"🎯 Objetivo nutricional: {goal}")
    logger.info(f"⚖️ TDEE (mantenimiento): {tdee} kcal/día")
    logger.info(f"📊 Ajuste: {ajuste:+d} kcal")
    logger.info(f"📈 Calorías objetivo: {calorias_objetivo} kcal/día")
    logger.info("-" * 60)
    
    return calorias_objetivo


def calculate_macros_distribution(calorias_totales: int, peso_kg: float, goal: str) -> Dict[str, int]:
    """
    Calcula la distribución de macronutrientes según el objetivo
    
    La distribución se basa en investigaciones científicas sobre
    composición corporal y rendimiento deportivo.
    
    Args:
        calorias_totales: Calorías totales diarias objetivo
        peso_kg: Peso del usuario en kg
        goal: Objetivo nutricional
        
    Returns:
        Dict con gramos de cada macro: {"proteina": X, "carbohidratos": Y, "grasas": Z}
    """
    goal_lower = goal.lower() if goal else "mantenimiento"
    
    # Proteína: gramos por kg de peso corporal según objetivo
    if goal_lower in ["volumen", "fuerza"]:
        proteina_g_por_kg = 2.0      # Más proteína para construcción muscular
        grasa_porcentaje = 0.25      # 25% de calorías de grasas
    elif goal_lower in ["definicion", "definición"]:
        proteina_g_por_kg = 2.2      # Más proteína para preservar músculo en déficit
        grasa_porcentaje = 0.30      # 30% de calorías de grasas
    else:  # mantenimiento, resistencia, etc.
        proteina_g_por_kg = 1.8      # Proteína estándar
        grasa_porcentaje = 0.28      # 28% de calorías de grasas
    
    # Calcular proteína
    proteina_g = int(peso_kg * proteina_g_por_kg)
    proteina_kcal = proteina_g * 4  # 4 kcal por gramo de proteína
    
    # Calcular grasas
    grasa_kcal = int(calorias_totales * grasa_porcentaje)
    grasa_g = int(grasa_kcal / 9)  # 9 kcal por gramo de grasa
    
    # Calcular carbohidratos (resto de calorías)
    carbos_kcal = calorias_totales - proteina_kcal - grasa_kcal
    carbos_g = int(carbos_kcal / 4)  # 4 kcal por gramo de carbohidrato
    
    logger.info("📊 DISTRIBUCIÓN DE MACRONUTRIENTES:")
    logger.info(f"   🥩 Proteína: {proteina_g}g ({proteina_kcal} kcal, {proteina_g_por_kg}g/kg)")
    logger.info(f"   🍚 Carbohidratos: {carbos_g}g ({carbos_kcal} kcal)")
    logger.info(f"   🥑 Grasas: {grasa_g}g ({grasa_kcal} kcal, {int(grasa_porcentaje*100)}%)")
    logger.info(f"   📊 Total: {proteina_kcal + carbos_kcal + grasa_kcal} kcal")
    
    return {
        "proteina": proteina_g,
        "carbohidratos": carbos_g,
        "grasas": grasa_g
    }


def get_complete_nutrition_plan(user_data: Dict, goal: str) -> Dict:
    """
    Función completa: calcula plan nutricional completo para el usuario
    
    Esta es la función principal que debe usarse desde otros módulos.
    
    Args:
        user_data: Datos del usuario (peso, altura, edad, sexo, nivel_actividad)
        goal: Objetivo nutricional (volumen, definicion, mantenimiento, etc.)
        
    Returns:
        Dict con:
            - tdee: Calorías de mantenimiento
            - calorias_objetivo: Calorías según objetivo
            - macros: Dict con proteína, carbos y grasas en gramos
            - tmb: Tasa Metabólica Basal (para referencia)
    """
    try:
        logger.info("🎯 GENERANDO PLAN NUTRICIONAL COMPLETO")
        logger.info("=" * 60)
        
        # 1. Calcular TDEE (mantenimiento)
        tdee = calculate_maintenance_calories(user_data)
        
        # 2. Calcular calorías según objetivo
        calorias_objetivo = calculate_calories_for_goal(tdee, goal)
        
        # 3. Calcular distribución de macros
        peso_str = user_data.get("peso", "75")
        peso_kg = parse_peso(peso_str)
        macros = calculate_macros_distribution(calorias_objetivo, peso_kg, goal)
        
        # 4. Calcular TMB para referencia
        altura = int(user_data.get("altura", 175))
        edad = int(user_data.get("edad", 25))
        sexo = user_data.get("sexo", "masculino")
        tmb = calculate_tmb(peso_kg, altura, edad, sexo)
        
        resultado = {
            "tdee": tdee,
            "calorias_objetivo": calorias_objetivo,
            "macros": macros,
            "tmb": int(tmb)
        }
        
        logger.info("=" * 60)
        logger.info("✅ PLAN NUTRICIONAL GENERADO EXITOSAMENTE")
        logger.info(f"   TMB: {int(tmb)} kcal/día")
        logger.info(f"   TDEE: {tdee} kcal/día")
        logger.info(f"   Objetivo: {calorias_objetivo} kcal/día")
        logger.info(f"   Macros: P={macros['proteina']}g C={macros['carbohidratos']}g G={macros['grasas']}g")
        logger.info("=" * 60)
        
        return resultado
        
    except Exception as e:
        logger.error(f"❌ Error generando plan nutricional: {e}")
        return {
            "tdee": 2500,
            "calorias_objetivo": 2500,
            "macros": {"proteina": 150, "carbohidratos": 300, "grasas": 70},
            "tmb": 1800
        }


# ==================== TESTING ====================

if __name__ == "__main__":
    """
    Tests básicos para validar las funciones
    """
    print("\n" + "=" * 70)
    print("🧪 TESTING NUTRITION CALCULATOR")
    print("=" * 70)
    
    # Test 1: Usuario masculino moderadamente activo
    print("\n📋 TEST 1: Hombre 25 años, 75kg, 175cm, moderado")
    print("-" * 70)
    test_user_1 = {
        "peso": "75kg",
        "altura": 175,
        "edad": 25,
        "sexo": "masculino",
        "nivel_actividad": "moderado"
    }
    
    plan_1 = get_complete_nutrition_plan(test_user_1, "volumen")
    print(f"\n✅ RESULTADO:")
    print(f"   TMB: {plan_1['tmb']} kcal/día")
    print(f"   TDEE: {plan_1['tdee']} kcal/día")
    print(f"   Objetivo (volumen): {plan_1['calorias_objetivo']} kcal/día")
    print(f"   Macros: P={plan_1['macros']['proteina']}g, C={plan_1['macros']['carbohidratos']}g, G={plan_1['macros']['grasas']}g")
    
    # Test 2: Usuario femenino ligera actividad
    print("\n" + "=" * 70)
    print("📋 TEST 2: Mujer 30 años, 60kg, 165cm, ligera")
    print("-" * 70)
    test_user_2 = {
        "peso": "60",
        "altura": 165,
        "edad": 30,
        "sexo": "femenino",
        "nivel_actividad": "ligero"
    }
    
    plan_2 = get_complete_nutrition_plan(test_user_2, "definicion")
    print(f"\n✅ RESULTADO:")
    print(f"   TMB: {plan_2['tmb']} kcal/día")
    print(f"   TDEE: {plan_2['tdee']} kcal/día")
    print(f"   Objetivo (definición): {plan_2['calorias_objetivo']} kcal/día")
    print(f"   Macros: P={plan_2['macros']['proteina']}g, C={plan_2['macros']['carbohidratos']}g, G={plan_2['macros']['grasas']}g")
    
    # Test 3: Parse peso
    print("\n" + "=" * 70)
    print("📋 TEST 3: Parse peso")
    print("-" * 70)
    test_pesos = ["75kg", "75.5", "80 kg", "65.2kg", "70"]
    for peso in test_pesos:
        parsed = parse_peso(peso)
        print(f"   '{peso}' → {parsed}kg")
    
    print("\n" + "=" * 70)
    print("✅ TODOS LOS TESTS COMPLETADOS")
    print("=" * 70 + "\n")

