"""
Templates de rutinas y dietas genéricas para usuarios FREE
"""

def get_generic_plan(user_data):
    """
    Devuelve plan genérico con SOLO el título personalizado.
    La rutina y dieta son siempre las mismas.
    """
    # Extraer datos del usuario
    genero = "hombre" if user_data.get('sexo', '').lower() in ['masculino', 'hombre', 'm'] else "mujer"
    altura = float(user_data.get('altura', 1.75))
    peso = float(user_data.get('peso', 75))
    edad = int(user_data.get('edad', 25))
    objetivo = user_data.get('objetivo', 'ganar músculo')
    
    # Calcular TMB (solo para mostrarlo)
    altura_cm = altura * 100
    tmb = 10 * peso + 6.25 * altura_cm - 5 * edad
    if genero == "hombre":
        tmb += 5
    else:
        tmb -= 161
    tmb = int(tmb)
    
    # RUTINA GENÉRICA (siempre la misma)
    rutina = {
        "titulo": f"Plan personalizado para {genero} de {edad} años, {altura}m, {peso}kg - Objetivo: {objetivo}",
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
    
    # DIETA GENÉRICA (siempre la misma)
    dieta = {
        "titulo": f"Plan personalizado para {genero} de {edad} años, {altura}m, {peso}kg - TMB: {tmb} kcal",
        "tmb": tmb,
        "descripcion": "Plan nutricional balanceado para entrenamiento",
        "comidas": [
            {
                "tipo": "Desayuno (7:00-8:00)",
                "alimentos": [
                    {"nombre": "Avena", "cantidad": "60g", "calorias": 225},
                    {"nombre": "Plátano", "cantidad": "1 unidad", "calorias": 105},
                    {"nombre": "Proteína en polvo", "cantidad": "30g", "calorias": 120},
                    {"nombre": "Almendras", "cantidad": "20g", "calorias": 120}
                ],
                "total": "470 kcal"
            },
            {
                "tipo": "Media mañana (10:30)",
                "alimentos": [
                    {"nombre": "Yogur griego", "cantidad": "200g", "calorias": 130},
                    {"nombre": "Arándanos", "cantidad": "50g", "calorias": 30}
                ],
                "total": "160 kcal"
            },
            {
                "tipo": "Comida (13:30-14:30)",
                "alimentos": [
                    {"nombre": "Pechuga de pollo", "cantidad": "180g", "calorias": 300},
                    {"nombre": "Arroz integral", "cantidad": "80g en crudo", "calorias": 280},
                    {"nombre": "Brócoli", "cantidad": "150g", "calorias": 50},
                    {"nombre": "Aceite de oliva", "cantidad": "10ml", "calorias": 90}
                ],
                "total": "720 kcal"
            },
            {
                "tipo": "Merienda (17:00)",
                "alimentos": [
                    {"nombre": "Pan integral", "cantidad": "2 rebanadas", "calorias": 160},
                    {"nombre": "Atún", "cantidad": "80g", "calorias": 120},
                    {"nombre": "Aguacate", "cantidad": "1/2 unidad", "calorias": 120}
                ],
                "total": "400 kcal"
            },
            {
                "tipo": "Cena (20:30-21:00)",
                "alimentos": [
                    {"nombre": "Salmón", "cantidad": "150g", "calorias": 300},
                    {"nombre": "Patata cocida", "cantidad": "150g", "calorias": 135},
                    {"nombre": "Espárragos", "cantidad": "150g", "calorias": 30}
                ],
                "total": "465 kcal"
            }
        ],
        "total_calorias": "~2,215 kcal"
    }
    
    return {
        "rutina": rutina,
        "dieta": dieta
    }
