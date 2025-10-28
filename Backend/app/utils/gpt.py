import os
import json
import regex as re
import asyncio
from dotenv import load_dotenv
from app.schemas import PlanRequest
from openai import AsyncOpenAI
import logging
from app.utils.nutrition_calculator import get_complete_nutrition_plan
from fastapi import HTTPException

# Cargar .env desde la raíz del proyecto Backend
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

# Cliente OpenAI con timeout configurado
client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=120.0,  # 2 minutos para todas las llamadas
    max_retries=2    # Reintentar 2 veces automáticamente
)

# 💰 MODELO DINÁMICO: Usar modelo barato en desarrollo, caro en producción
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

if ENVIRONMENT == 'production':
    MODEL = "gpt-4o"  # Para usuarios reales
    print("🚀 [ONBOARDING] Usando GPT-4o para PRODUCCIÓN")
else:
    MODEL = "gpt-3.5-turbo"  # Para testing (20x más barato)
    print("💡 [ONBOARDING] Usando GPT-3.5 Turbo para DESARROLLO (20x más barato)")
    
# 🛡️ FORZAR GPT-3.5 EN DESARROLLO
if ENVIRONMENT != 'production':
    MODEL = "gpt-3.5-turbo"
    print("🔒 FORZANDO GPT-3.5 Turbo para desarrollo")

async def generar_plan_safe(user_data, user_id):
    """Genera plan con GPT, con fallback a plan genérico"""
    
    try:
        # Intentar con GPT
        logger.info(f"🤖 Intentando generar plan con GPT para usuario {user_id}")
        
        plan_data = await generar_plan_personalizado(user_data)
        
        logger.info(f"✅ Plan GPT generado exitosamente")
        return plan_data
        
    except (asyncio.CancelledError, asyncio.TimeoutError) as e:
        # Si falla GPT, usar plan genérico
        logger.warning(f"⚠️ GPT falló ({type(e).__name__}), usando plan genérico")
        
        from app.utils.routine_templates import get_generic_plan
        plan_data = get_generic_plan(user_data)
        
        logger.info(f"✅ Plan genérico generado como fallback")
        return plan_data
        
    except Exception as e:
        # Para otros errores, también usar plan genérico
        logger.error(f"❌ Error inesperado: {str(e)}, usando plan genérico")
        logger.exception(e)
        
        from app.utils.routine_templates import get_generic_plan
        plan_data = get_generic_plan(user_data)
        
        return plan_data

logger = logging.getLogger(__name__)

async def generar_plan_personalizado(datos):
    # ═══════════════════════════════════════════════════════
    # CALCULAR NUTRICIÓN CIENTÍFICAMENTE CON TMB/TDEE
    # ═══════════════════════════════════════════════════════
    
    nutrition_goal = datos.get('nutrition_goal', 'mantenimiento')
    
    logger.info("=" * 70)
    logger.info("🧮 CALCULANDO PLAN NUTRICIONAL CIENTÍFICO")
    logger.info("=" * 70)
    logger.info(f"📊 Objetivo nutricional: {nutrition_goal}")
    
    # Calcular plan nutricional con función científica (TMB + TDEE)
    nutrition_plan = get_complete_nutrition_plan(datos, nutrition_goal)
    
    tmb = nutrition_plan['tmb']
    tdee = nutrition_plan['tdee']
    kcal_objetivo = nutrition_plan['calorias_objetivo']
    macros = nutrition_plan['macros']
    
    # Calcular diferencia vs mantenimiento para logging
    diferencia_mantenimiento = kcal_objetivo - tdee
    
    logger.info("✅ RESULTADOS DEL CÁLCULO CIENTÍFICO:")
    logger.info(f"   🔥 TMB (Metabolismo Basal): {tmb} kcal/día")
    logger.info(f"   ⚖️ TDEE (Mantenimiento): {tdee} kcal/día")
    logger.info(f"   🎯 Calorías objetivo ({nutrition_goal}): {kcal_objetivo} kcal/día")
    logger.info(f"   📊 Diferencia vs mantenimiento: {diferencia_mantenimiento:+d} kcal")
    logger.info(f"   🥩 Macros objetivo:")
    logger.info(f"      - Proteína: {macros['proteina']}g/día")
    logger.info(f"      - Carbohidratos: {macros['carbohidratos']}g/día")
    logger.info(f"      - Grasas: {macros['grasas']}g/día")
    logger.info("=" * 70)
    
    # Mantener compatibilidad con código antiguo
    mantenimiento = tdee

    idioma = datos.get('idioma', 'es').lower()

    # Obtener objetivos separados
    gym_goal = datos.get('gym_goal', 'ganar_musculo')
    nutrition_goal = datos.get('nutrition_goal', 'mantenimiento')
    training_frequency = datos.get('training_frequency', 4)
    training_days = datos.get('training_days', ['lunes', 'martes', 'jueves', 'viernes'])
    
    texto_dieta = f"""
Quiero que ahora generes una dieta hiperpersonalizada basada en cálculos científicos (fórmula Mifflin-St Jeor).

CÁLCULOS NUTRICIONALES CIENTÍFICOS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. TMB (Tasa Metabólica Basal): {tmb} kcal/día
   - Calorías que el cuerpo necesita en reposo absoluto
   
2. TDEE (Gasto Energético Total Diario): {tdee} kcal/día
   - Calorías de mantenimiento (TMB × factor actividad)
   - Nivel de actividad: {datos.get('nivel_actividad', 'moderado')}
   
3. Calorías objetivo ({nutrition_goal}): {kcal_objetivo} kcal/día
   - Ajuste: {diferencia_mantenimiento:+d} kcal vs mantenimiento

MACRONUTRIENTES OBJETIVO (CALCULADOS CIENTÍFICAMENTE):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Proteína: {macros['proteina']}g/día ({macros['proteina'] * 4} kcal)
- Carbohidratos: {macros['carbohidratos']}g/día ({macros['carbohidratos'] * 4} kcal)
- Grasas: {macros['grasas']}g/día ({macros['grasas'] * 9} kcal)

INSTRUCCIONES CRÍTICAS PARA LA DIETA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. La dieta DEBE cumplir EXACTAMENTE con {kcal_objetivo} kcal/día total
2. Los macros deben aproximarse lo máximo posible a los valores calculados arriba
3. Distribuir en 5 comidas balanceadas al día
4. Cada comida debe especificar cantidades exactas en gramos/ml
5. Los macros totales deben sumar aproximadamente los valores objetivo

Ahora, crea una dieta estructurada en 5 comidas al día. Usa los siguientes alimentos de preferencia:
- Frutas: dátiles (preentreno), sandía, plátano, manzana.
- Verduras: brócoli, coliflor, lechuga, tomate, aguacate.
- Proteínas: leche, yogur, frutos secos, mantequilla de cacahuete, atún, pollo, ternera, pescado, queso, fuet, proteína en polvo (si el usuario la tiene).
- Hidratos: arroz, avena (gachas en desayuno), pan, patata, ñoquis, cereales tipo cornflakes.
- Grasas: aceite de oliva, frutos secos, aguacate.

Formato obligatorio de salida en JSON:

"dieta": {{
  "resumen": "Explicación de TMB y ajuste calórico",
  "comidas": [
    {{
      "nombre": "Desayuno",
      "kcal": 500,
      "macros": {{
        "proteinas": 35,
        "hidratos": 50,
        "grasas": 15
      }},
      "alimentos": [
        "300ml leche semidesnatada - 150kcal",
        "40g avena - 150kcal",
        "1 plátano - 100kcal",
        "15g mantequilla de cacahuete - 100kcal"
      ],
      "alternativas": [
        "200ml yogur natural + 10g nueces",
        "1 manzana + 2 tostadas con aguacate"
      ]
    }}
  ],
  "consejos_finales": [
    "Beber al menos 3L de agua al día.",
    "Añade una pizca de sal a las comidas. Si sudas mucho, repón electrolitos.",
    "La comida preentreno debe incluir hidratos rápidos como dátiles, plátano o pan.",
    "La comida postentreno debe incluir hidratos + proteínas. Si solo comes proteínas, se produce gluconeogénesis y se pierde su función de recuperación muscular.",
    "Si tienes proteína en polvo, úsala para cuadrar macros y facilitar el aporte proteico."
  ]
}}
"""

    texto_rutina = """
Genera también una rutina personalizada según el perfil. Formato obligatorio:

"rutina": {
  "dias": [
    {
      "dia": "Lunes",
      "ejercicios": [
        {
          "nombre": "Sentadillas",
          "series": 4,
          "repeticiones": "8-10",
          "descanso": "90 segundos"
        }
      ]
    }
  ],
  "consejos": [
    "Calienta bien antes de cada sesión",
    "Estira al finalizar cada rutina"
  ]
}

IMPORTANTE: Las repeticiones deben ser strings como "8-10", "12-15", etc. NO números.
"""

    prompt = f"""
Eres un entrenador profesional de fuerza y nutrición. Genera un plan completo y personalizado.

═══════════════════════════════════════════════
PERFIL DEL USUARIO:
═══════════════════════════════════════════════
- Edad: {datos['edad']} años
- Altura: {datos['altura']} cm
- Peso: {datos['peso']} kg
- Sexo: {datos['sexo']}
- Nivel de experiencia: {datos['experiencia']}
- Tipo de cuerpo: {datos.get('tipo_cuerpo', 'ninguno')}
- Puntos fuertes: {datos.get('puntos_fuertes', 'ninguno')}
- Puntos débiles: {datos.get('puntos_debiles', 'ninguno')}
- Lesiones: {datos.get('lesiones', 'ninguna')}
- Intensidad deseada: {datos.get('entrenar_fuerte', 'media')}

═══════════════════════════════════════════════
OBJETIVOS SEPARADOS:
═══════════════════════════════════════════════
🏋️ OBJETIVO DE GIMNASIO: {gym_goal}
   (Enfoca los ejercicios, volumen y estructura de la rutina hacia este objetivo)

🍎 OBJETIVO NUTRICIONAL: {nutrition_goal}
   (Ajusta las calorías y distribución de macros según este objetivo)

═══════════════════════════════════════════════
DISPONIBILIDAD Y EQUIPAMIENTO:
═══════════════════════════════════════════════
- Días disponibles: {training_frequency} días/semana
- Días específicos: {', '.join(training_days)}
- Equipamiento disponible: {', '.join(datos['materiales'])}

═══════════════════════════════════════════════
RESTRICCIONES:
═══════════════════════════════════════════════
- Alergias: {datos.get('alergias', 'ninguna')}
- Restricciones dietéticas: {datos.get('restricciones', 'ninguna')}
- Idioma: {idioma}

{texto_dieta}
{texto_rutina}

INSTRUCCIONES CRÍTICAS:

1. RUTINA DE ENTRENAMIENTO:
   - Diseña la rutina para EXACTAMENTE {training_frequency} días
   - Distribuye los entrenamientos en los días: {', '.join(training_days)}
   - Cada día debe tener su nombre específico (ej: "Lunes - Pecho y Tríceps")
   - Ajusta los ejercicios y volumen según el objetivo de gym: {gym_goal}
     * Si es "ganar_musculo": Hipertrofia - 8-12 reps, 3-4 series, descansos 60-90s
     * Si es "ganar_fuerza": Fuerza - 4-6 reps, 4-5 series, descansos 2-3min
   - Considera el equipamiento disponible
   - Cada día debe tener 4-6 ejercicios diferentes

2. PLAN NUTRICIONAL:
   - Calcula calorías según objetivo nutricional: {nutrition_goal}
     * Si "volumen": Superávit de ~300 kcal → {kcal_objetivo} kcal/día
     * Si "definicion": Déficit de ~300 kcal → {kcal_objetivo} kcal/día
     * Si "mantenimiento": Calorías de mantenimiento → {kcal_objetivo} kcal/día
   
   - Distribución de macros:
     * Proteína: 1.8-2.2g por kg de peso corporal
     * Ajustar carbohidratos y grasas según objetivo
   
   - Respetar restricciones: {datos.get('restricciones', 'ninguna')}
   - Evitar alergias: {datos.get('alergias', 'ninguna')}
   - Generar exactamente 5 comidas al día

3. FORMATO DE RESPUESTA:
   Devuelve únicamente un JSON válido, con esta estructura exacta:

{{
  "rutina": {{
    "dias": [
      {{
        "dia": "Lunes",
        "grupos_musculares": "Pecho y Tríceps",
        "ejercicios": [
          {{
            "nombre": "Press banca",
            "series": 4,
            "repeticiones": "8-10",
            "descanso": "90 segundos"
          }}
        ]
      }}
    ],
    "consejos": ["Consejo 1", "Consejo 2"],
    "metadata": {{
      "gym_goal": "{gym_goal}",
      "training_frequency": {training_frequency},
      "training_days": {json.dumps(training_days)}
    }}
  }},
  "dieta": {{
    "resumen": "Explicación de TMB y ajuste calórico",
    "comidas": [
      {{
        "nombre": "Desayuno",
        "kcal": 500,
        "macros": {{
          "proteinas": 35,
          "hidratos": 50,
          "grasas": 15
        }},
        "alimentos": ["alimento 1", "alimento 2"],
        "alternativas": ["alternativa 1", "alternativa 2"]
      }}
    ],
    "consejos_finales": ["Consejo 1", "Consejo 2"],
    "metadata": {{
      "nutrition_goal": "{nutrition_goal}"
    }}
  }},
  "motivacion": "Frase motivacional breve y personalizada para el usuario"
}}

REGLAS CRÍTICAS:
1. Las repeticiones SIEMPRE deben ser strings: "8-10", "12-15", etc.
2. NO uses números para rangos de repeticiones
3. NO escribas nada fuera del JSON
4. NO des explicaciones antes ni después
5. Solo responde con ese objeto JSON válido
"""

    # 🛡️ PROTECCIÓN: Logging antes de generar plan
    logger.info(f"🔄 Generando plan personalizado para usuario (modelo: {MODEL})")
    
    try:
        response = await client.chat.completions.create(
            model=MODEL,  # ✅ Usa modelo dinámico según ambiente
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,
            max_tokens=2500,  # 🛡️ Limitar tokens para evitar excesos
            timeout=120.0  # 🛡️ Timeout aumentado a 2 minutos
        )
        
        # 📊 Logging de tokens usados
        if hasattr(response, 'usage') and response.usage:
            tokens_used = response.usage.total_tokens
            logger.info(f"📊 Tokens usados en onboarding: {tokens_used}")
            if tokens_used > 3000:
                logger.warning(f"⚠️ Onboarding usando muchos tokens: {tokens_used}")
        
        contenido = response.choices[0].message.content
        logger.info(f"✅ Plan generado exitosamente (modelo: {MODEL})")
        print("Respuesta cruda de GPT:", contenido[:200] + "...")  # Solo mostrar primeros 200 chars
        
    except asyncio.TimeoutError:
        logger.error("❌ GPT timeout después de 120s")
        raise HTTPException(
            status_code=504,
            detail="La generación del plan tardó demasiado. Intenta de nuevo."
        )
        
    except asyncio.CancelledError:
        logger.warning("⚠️ Generación de plan cancelada por el cliente")
        raise HTTPException(
            status_code=499,  # Client Closed Request
            detail="Generación cancelada por el cliente"
        )
        
    except Exception as e:
        logger.error(f"❌ Error generando plan: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar plan: {str(e)}"
        )

    # 🧹 LIMPIAR MARKDOWN SI EXISTE
    response_text = contenido.strip()
    
    # Si viene con markdown ```json, limpiarlo
    if response_text.startswith('```'):
        logger.info("🧹 Limpiando markdown de respuesta...")
        # Extraer JSON entre ```json y ```
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            # Si solo tiene ``` sin json
            parts = response_text.split('```')
            if len(parts) >= 2:
                response_text = parts[1].strip()
    
    logger.info(f"📄 Texto limpio para parsear: {response_text[:100]}...")
    
    # Buscar el primer bloque JSON que aparezca en la respuesta
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    if not json_match:
        logger.error(f"❌ No se encontró JSON válido en: {response_text[:500]}")
        raise ValueError("No se encontró un JSON válido en la respuesta de GPT")

    json_str = json_match.group(0)
    logger.info(f"✅ JSON extraído, parseando...")
    
    try:
        data = json.loads(json_str)
        logger.info(f"✅ JSON parseado exitosamente")
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error parseando JSON: {e}")
        logger.error(f"JSON problemático: {json_str[:500]}")
        raise

    # ═══════════════════════════════════════════════════════
    # AÑADIR METADATOS CIENTÍFICOS A LA DIETA
    # ═══════════════════════════════════════════════════════
    
    from datetime import datetime
    
    # Asegurar que la dieta tenga metadata
    if 'metadata' not in data['dieta']:
        data['dieta']['metadata'] = {}
    
    # Añadir valores calculados científicamente
    data['dieta']['metadata'].update({
        'tmb': tmb,
        'tdee': tdee,
        'calorias_objetivo': kcal_objetivo,
        'macros_objetivo': macros,
        'fecha_calculo': datetime.now().isoformat(),
        'nivel_actividad': datos.get('nivel_actividad', 'moderado'),
        'metodo_calculo': 'Mifflin-St Jeor',
        'diferencia_mantenimiento': diferencia_mantenimiento
    })
    
    logger.info("📦 Metadatos científicos añadidos a la dieta:")
    logger.info(f"   TMB: {tmb} kcal/día")
    logger.info(f"   TDEE: {tdee} kcal/día")
    logger.info(f"   Calorías objetivo: {kcal_objetivo} kcal/día")
    logger.info(f"   Método: Mifflin-St Jeor")

    return {
        "rutina": data["rutina"],
        "dieta": data["dieta"],
        "motivacion": data["motivacion"]
    }
