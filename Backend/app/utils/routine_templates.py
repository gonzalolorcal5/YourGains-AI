"""
Templates de rutinas y dietas genéricas para usuarios FREE
"""

import logging
logger = logging.getLogger(__name__)

def get_generic_plan(user_data):
    """
    Devuelve plan genérico con cálculos nutricionales idénticos al plan premium.
    """
    # Extraer datos del usuario
    genero = "hombre" if user_data.get('sexo', '').lower() in ['masculino', 'hombre', 'm'] else "mujer"
    altura_raw = user_data.get('altura', 175)
    
    # Manejar altura (puede venir en cm o metros)
    if altura_raw > 10:  # Si es mayor que 10, asumir que está en cm
        altura_cm = int(altura_raw)
        altura_m = altura_cm / 100
    else:  # Si es menor que 10, asumir que está en metros
        altura_m = float(altura_raw)
        altura_cm = int(altura_m * 100)
    
    peso = float(user_data.get('peso', 75))
    edad = int(user_data.get('edad', 25))
    objetivo = user_data.get('objetivo', 'ganar músculo')
    nivel_actividad = user_data.get('nivel_actividad', 'moderado')
    
    # ════════════════════════════════════════════════════════════
    # CÁLCULOS NUTRICIONALES IDÉNTICOS AL PLAN PREMIUM
    # ════════════════════════════════════════════════════════════
    
    # Calcular TMB con Mifflin-St Jeor (mismo que premium)
    if genero == "hombre":
        tmb = (10 * peso) + (6.25 * altura_cm) - (5 * edad) + 5
    else:
        tmb = (10 * peso) + (6.25 * altura_cm) - (5 * edad) - 161
    
    logger.info(f"📊 TMB calculada: {tmb} kcal/día (peso={peso}kg, altura={altura_cm}cm, edad={edad}, sexo={genero})")
    
    # Factor de actividad (mismo que premium)
    factores_actividad = {
        'sedentario': 1.2,
        'ligero': 1.375,
        'moderado': 1.55,
        'activo': 1.725,
        'muy_activo': 1.9
    }
    
    factor = factores_actividad.get(nivel_actividad.lower(), 1.55)
    tdee = tmb * factor
    
    logger.info(f"🏃 Nivel actividad: {nivel_actividad} → Factor: {factor}x")
    logger.info(f"🔢 TDEE = TMB ({tmb}) × {factor} = {tdee} kcal/día")
    logger.info(f"⚖️ TDEE (calorías de mantenimiento): {tdee} kcal/día")
    
    # Ajuste según objetivo nutricional (mismo que premium)
    # Extraer objetivo nutricional del objetivo combinado
    objetivo_nutricional = "mantenimiento"  # Por defecto
    if "definicion" in objetivo.lower() or "definir" in objetivo.lower() or "perder" in objetivo.lower():
        objetivo_nutricional = "definicion"
    elif "volumen" in objetivo.lower() or "ganar" in objetivo.lower():
        objetivo_nutricional = "volumen"
    
    ajustes_objetivo = {
        'definicion': -300,
        'perder_peso': -300,
        'mantenimiento': 0,
        'volumen': 300,
        'ganar_musculo': 300
    }
    
    ajuste = ajustes_objetivo.get(objetivo_nutricional.lower(), 0)
    calorias_objetivo = tdee + ajuste
    
    logger.info(f"🎯 Objetivo nutricional detectado: {objetivo_nutricional}")
    logger.info(f"📊 Ajuste calórico: {ajuste:+d} kcal")
    logger.info(f"🎯 Calorías objetivo ({objetivo_nutricional}): {calorias_objetivo} kcal/día")
    
    # Calcular macros objetivo (mismo que premium)
    proteinas_objetivo = int(peso * 2.0)  # 2g por kg de peso
    carbohidratos_objetivo = int((calorias_objetivo - (proteinas_objetivo * 4)) * 0.5 / 4)  # 50% de calorías restantes
    grasas_objetivo = int((calorias_objetivo - (proteinas_objetivo * 4) - (carbohidratos_objetivo * 4)) / 9)  # Resto en grasas
    
    logger.info(f"📊 Macros objetivo: P={proteinas_objetivo}g, C={carbohidratos_objetivo}g, G={grasas_objetivo}g")
    
    # RUTINA GENÉRICA (siempre la misma)
    rutina = {
        "titulo": f"Plan personalizado para {genero} de {edad} años, {altura_cm}cm, {peso}kg - Objetivo: {objetivo}",
        "dias": [
            {
                "dia": "Lunes - Pecho y Tríceps",
                "ejercicios": [
                    {"nombre": "Press banca", "series": 4, "reps": "8-10", "peso": "Moderado-Alto"},
                    {"nombre": "Press inclinado con mancuernas", "series": 3, "reps": "10-12", "peso": "Moderado"},
                    {"nombre": "Aperturas con mancuernas", "series": 3, "reps": "12-15", "peso": "Moderado"},
                    {"nombre": "Fondos en paralelas", "series": 3, "reps": "8-12", "peso": "Corporal"},
                    {"nombre": "Press francés", "series": 3, "reps": "10-12", "peso": "Moderado"},
                    {"nombre": "Extensiones en polea", "series": 3, "reps": "12-15", "peso": "Moderado"}
                ]
            },
            {
                "dia": "Martes - Espalda y Bíceps",
                "ejercicios": [
                    {"nombre": "Dominadas", "series": 4, "reps": "6-10", "peso": "Corporal"},
                    {"nombre": "Remo con barra", "series": 4, "reps": "8-10", "peso": "Moderado-Alto"},
                    {"nombre": "Jalón al pecho", "series": 3, "reps": "10-12", "peso": "Moderado"},
                    {"nombre": "Remo con mancuernas", "series": 3, "reps": "10-12", "peso": "Moderado"},
                    {"nombre": "Curl con barra", "series": 3, "reps": "10-12", "peso": "Moderado"},
                    {"nombre": "Curl martillo", "series": 3, "reps": "12-15", "peso": "Moderado"}
                ]
            },
            {
                "dia": "Miércoles - Descanso"
            },
            {
                "dia": "Jueves - Piernas",
                "ejercicios": [
                    {"nombre": "Sentadillas", "series": 4, "reps": "8-10", "peso": "Moderado-Alto"},
                    {"nombre": "Prensa de piernas", "series": 4, "reps": "10-12", "peso": "Alto"},
                    {"nombre": "Zancadas", "series": 3, "reps": "12-15 por pierna", "peso": "Moderado"},
                    {"nombre": "Curl femoral", "series": 3, "reps": "10-12", "peso": "Moderado"},
                    {"nombre": "Extensiones de cuádriceps", "series": 3, "reps": "12-15", "peso": "Moderado"},
                    {"nombre": "Elevaciones de gemelos", "series": 4, "reps": "15-20", "peso": "Moderado"}
                ]
            },
            {
                "dia": "Viernes - Hombros y Core",
                "ejercicios": [
                    {"nombre": "Press militar", "series": 4, "reps": "8-10", "peso": "Moderado"},
                    {"nombre": "Elevaciones laterales", "series": 3, "reps": "12-15", "peso": "Moderado"},
                    {"nombre": "Elevaciones frontales", "series": 3, "reps": "12-15", "peso": "Moderado"},
                    {"nombre": "Pájaros", "series": 3, "reps": "12-15", "peso": "Ligero"},
                    {"nombre": "Planchas", "series": 3, "reps": "30-60s", "peso": "Corporal"},
                    {"nombre": "Abdominales", "series": 3, "reps": "15-20", "peso": "Moderado"}
                ]
            },
            {
                "dia": "Sábado y Domingo - Descanso"
            }
        ]
    }
    
    # ════════════════════════════════════════════════════════════
    # DIETA GENÉRICA CON CALORÍAS CALCULADAS DINÁMICAMENTE
    # ════════════════════════════════════════════════════════════
    
    # Calcular distribución de calorías por comida (mismo que premium)
    calorias_por_comida = [
        int(calorias_objetivo * 0.20),  # Desayuno: 20%
        int(calorias_objetivo * 0.10),  # Media mañana: 10%
        int(calorias_objetivo * 0.30),  # Comida: 30%
        int(calorias_objetivo * 0.15),  # Merienda: 15%
        int(calorias_objetivo * 0.25)   # Cena: 25%
    ]
    
    # Ajustar la última comida para que sume exactamente las calorías objetivo
    calorias_por_comida[4] = calorias_objetivo - sum(calorias_por_comida[:4])
    
    logger.info(f"📊 Distribución de calorías por comida: {calorias_por_comida}")
    logger.info(f"📊 Total calculado: {sum(calorias_por_comida)} kcal (objetivo: {calorias_objetivo})")
    
    # DIETA GENÉRICA CON CALORÍAS DINÁMICAS
    dieta = {
        "resumen": f"Plan nutricional para {genero} de {edad} años, {peso}kg - Objetivo: {objetivo_nutricional} ({calorias_objetivo} kcal/día)",
        "comidas": [
            {
                "nombre": "Desayuno",
                "kcal": calorias_por_comida[0],
                "macros": {"proteinas": int(proteinas_objetivo * 0.25), "hidratos": int(carbohidratos_objetivo * 0.25), "grasas": int(grasas_objetivo * 0.25)},
                "alimentos": [
                    f"Avena 60g - {int(calorias_por_comida[0] * 0.4)}kcal",
                    f"Plátano 1 unidad - {int(calorias_por_comida[0] * 0.2)}kcal",
                    f"Proteína en polvo 30g - {int(calorias_por_comida[0] * 0.25)}kcal",
                    f"Almendras 20g - {int(calorias_por_comida[0] * 0.15)}kcal"
                ],
                "alternativas": ["Yogur griego + frutos secos", "Tostadas integrales + aguacate"]
            },
            {
                "nombre": "Media mañana",
                "kcal": calorias_por_comida[1],
                "macros": {"proteinas": int(proteinas_objetivo * 0.1), "hidratos": int(carbohidratos_objetivo * 0.1), "grasas": int(grasas_objetivo * 0.1)},
                "alimentos": [
                    f"Yogur griego 200g - {int(calorias_por_comida[1] * 0.8)}kcal",
                    f"Arándanos 50g - {int(calorias_por_comida[1] * 0.2)}kcal"
                ],
                "alternativas": ["Fruta + frutos secos", "Batido de proteínas"]
            },
            {
                "nombre": "Comida",
                "kcal": calorias_por_comida[2],
                "macros": {"proteinas": int(proteinas_objetivo * 0.35), "hidratos": int(carbohidratos_objetivo * 0.35), "grasas": int(grasas_objetivo * 0.35)},
                "alimentos": [
                    f"Pechuga de pollo 180g - {int(calorias_por_comida[2] * 0.4)}kcal",
                    f"Arroz integral 80g - {int(calorias_por_comida[2] * 0.4)}kcal",
                    f"Brócoli 150g - {int(calorias_por_comida[2] * 0.1)}kcal",
                    f"Aceite de oliva 10ml - {int(calorias_por_comida[2] * 0.1)}kcal"
                ],
                "alternativas": ["Salmón + quinoa + verduras", "Ternera + patata + ensalada"]
            },
            {
                "nombre": "Merienda",
                "kcal": calorias_por_comida[3],
                "macros": {"proteinas": int(proteinas_objetivo * 0.15), "hidratos": int(carbohidratos_objetivo * 0.15), "grasas": int(grasas_objetivo * 0.15)},
                "alimentos": [
                    f"Pan integral 2 rebanadas - {int(calorias_por_comida[3] * 0.4)}kcal",
                    f"Atún 80g - {int(calorias_por_comida[3] * 0.3)}kcal",
                    f"Aguacate 1/2 unidad - {int(calorias_por_comida[3] * 0.3)}kcal"
                ],
                "alternativas": ["Frutos secos + fruta", "Yogur + miel + nueces"]
            },
            {
                "nombre": "Cena",
                "kcal": calorias_por_comida[4],
                "macros": {"proteinas": int(proteinas_objetivo * 0.15), "hidratos": int(carbohidratos_objetivo * 0.15), "grasas": int(grasas_objetivo * 0.15)},
                "alimentos": [
                    f"Salmón 150g - {int(calorias_por_comida[4] * 0.6)}kcal",
                    f"Patata cocida 150g - {int(calorias_por_comida[4] * 0.3)}kcal",
                    f"Espárragos 150g - {int(calorias_por_comida[4] * 0.1)}kcal"
                ],
                "alternativas": ["Pollo + quinoa + verduras", "Tofu + boniato + ensalada"]
            }
        ],
        "consejos_finales": [
            "Beber al menos 3L de agua al día.",
            "Añade una pizca de sal a las comidas. Si sudas mucho, repón electrolitos.",
            "La comida preentreno debe incluir hidratos rápidos como dátiles, plátano o pan.",
            "La comida postentreno debe incluir hidratos + proteínas.",
            "Si tienes proteína en polvo, úsala para cuadrar macros y facilitar el aporte proteico."
        ],
        "metadata": {
            "nutrition_goal": objetivo_nutricional,
            "tmb": int(tmb),
            "tdee": int(tdee),
            "calorias_objetivo": calorias_objetivo,
            "macros_objetivo": {
                "proteina": proteinas_objetivo,
                "carbohidratos": carbohidratos_objetivo,
                "grasas": grasas_objetivo
            },
            "nivel_actividad": nivel_actividad,
            "metodo_calculo": "Mifflin-St Jeor",
            "diferencia_mantenimiento": ajuste
        }
    }
    
    # Sumar macros totales de todas las comidas y guardar en dieta["macros"]
    try:
        comidas = dieta.get("comidas", [])
        prot_total = sum(int(c.get("macros", {}).get("proteinas", 0) or 0) for c in comidas)
        carb_total = sum(int(c.get("macros", {}).get("hidratos", 0) or 0) for c in comidas)
        gras_total = sum(int(c.get("macros", {}).get("grasas", 0) or 0) for c in comidas)
        dieta["macros"] = {
            "proteina": round(prot_total, 1),
            "carbohidratos": round(carb_total, 1),
            "grasas": round(gras_total, 1)
        }
    except Exception:
        # Si falla, dejar macros vacíos pero no romper generación
        dieta.setdefault("macros", {"proteina": 0, "carbohidratos": 0, "grasas": 0})
    
    # 🔧 FIX: Añadir motivacion para compatibilidad con onboarding
    motivacion = f"¡Vamos a por ello! Con constancia y dedicación alcanzarás tu objetivo de {objetivo}. Recuerda que cada entrenamiento te acerca más a tu meta."
    
    return {
        "rutina": rutina,
        "dieta": dieta,
        "motivacion": motivacion
    }
