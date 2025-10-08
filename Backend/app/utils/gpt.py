import os
import json
import regex as re
from dotenv import load_dotenv
from app.schemas import PlanRequest
from openai import OpenAI
import logging

# Cargar .env desde la raíz del proyecto Backend
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

logger = logging.getLogger(__name__)

def generar_plan_personalizado(datos):
    if datos['sexo'].lower() in ["hombre", "masculino", "male"]:
        tmb = 10 * datos['peso'] + 6.25 * datos['altura'] - 5 * datos['edad'] + 5
    else:
        tmb = 10 * datos['peso'] + 6.25 * datos['altura'] - 5 * datos['edad'] - 161

    mantenimiento = round(tmb * 1.55)
    if "def" in datos['objetivo'].lower():
        ajuste_kcal = -300
    elif "vol" in datos['objetivo'].lower() or "gan" in datos['objetivo'].lower():
        ajuste_kcal = +300
    else:
        ajuste_kcal = 0
    kcal_objetivo = mantenimiento + ajuste_kcal

    idioma = datos.get('idioma', 'es').lower()

    texto_dieta = f"""
Quiero que ahora generes una dieta hiperpersonalizada. Comienza explicando:

1. La Tasa Metabólica Basal calculada es: {round(tmb)} kcal/día.
2. Las calorías de mantenimiento aproximadas son: {mantenimiento} kcal/día.
3. Como el objetivo del usuario es {datos['objetivo']}, se ajustarán las kcal a: {kcal_objetivo} kcal/día.

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
Eres un entrenador profesional de fuerza y nutrición. Genera un plan completo.

Perfil del usuario:
- Edad: {datos['edad']}
- Altura: {datos['altura']} cm
- Peso: {datos['peso']} kg
- Sexo: {datos['sexo']}
- Nivel: {datos['experiencia']}
- Objetivo: {datos['objetivo']}
- Tipo de cuerpo: {datos.get('tipo_cuerpo', 'ninguno')}
- Puntos fuertes: {datos.get('puntos_fuertes', 'ninguno')}
- Puntos débiles: {datos.get('puntos_debiles', 'ninguno')}
- Lesiones: {datos.get('lesiones', 'ninguna')}
- Intensidad deseada: {datos.get('entrenar_fuerte', 'media')}
- Materiales disponibles: {datos['materiales']}
- Alergias: {datos.get('alergias', 'ninguna')}
- Restricciones dieta: {datos.get('restricciones', 'ninguna')}
- Idioma: {idioma}

{texto_dieta}
{texto_rutina}

IMPORTANTE: 
1. Genera una rutina COMPLETA con al menos 4 días de entrenamiento
2. Cada día debe tener al menos 4-6 ejercicios diferentes
3. Genera una dieta COMPLETA con exactamente 5 comidas al día
4. Devuelve únicamente un JSON válido, con esta estructura exacta:

{{
  "rutina": {{
    "dias": [
      {{
        "dia": "Lunes",
        "ejercicios": [
          {{
            "nombre": "Sentadillas",
            "series": 4,
            "repeticiones": "8-10",
            "descanso": "90 segundos"
          }}
        ]
      }}
    ],
    "consejos": ["Consejo 1", "Consejo 2"]
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
    "consejos_finales": ["Consejo 1", "Consejo 2"]
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
        response = client.chat.completions.create(
            model=MODEL,  # ✅ Usa modelo dinámico según ambiente
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,
            max_tokens=2500,  # 🛡️ Limitar tokens para evitar excesos
            timeout=30  # 🛡️ Timeout para evitar cuelgues
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
        
    except Exception as e:
        logger.error(f"❌ Error generando plan: {e}")
        raise

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

    return {
        "rutina": data["rutina"],
        "dieta": data["dieta"],
        "motivacion": data["motivacion"]
    }
