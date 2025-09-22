import os
import json
import regex as re
from dotenv import load_dotenv
from app.schemas import PlanRequest
from openai import OpenAI

# Cargar .env desde la raíz del proyecto Backend
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generar_plan_personalizado(datos):
    if datos.sexo.lower() in ["hombre", "masculino", "male"]:
        tmb = 10 * datos.peso + 6.25 * datos.altura - 5 * datos.edad + 5
    else:
        tmb = 10 * datos.peso + 6.25 * datos.altura - 5 * datos.edad - 161

    mantenimiento = round(tmb * 1.55)
    if "def" in datos.objetivo.lower():
        ajuste_kcal = -300
    elif "vol" in datos.objetivo.lower() or "gan" in datos.objetivo.lower():
        ajuste_kcal = +300
    else:
        ajuste_kcal = 0
    kcal_objetivo = mantenimiento + ajuste_kcal

    idioma = datos.idioma.lower()

    texto_dieta = f"""
Quiero que ahora generes una dieta hiperpersonalizada. Comienza explicando:

1. La Tasa Metabólica Basal calculada es: {round(tmb)} kcal/día.
2. Las calorías de mantenimiento aproximadas son: {mantenimiento} kcal/día.
3. Como el objetivo del usuario es {datos.objetivo}, se ajustarán las kcal a: {kcal_objetivo} kcal/día.

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
- Edad: {datos.edad}
- Altura: {datos.altura} cm
- Peso: {datos.peso} kg
- Sexo: {datos.sexo}
- Nivel: {datos.experiencia}
- Objetivo: {datos.objetivo}
- Tipo de cuerpo: {datos.tipo_cuerpo or "ninguno"}
- Puntos fuertes: {datos.puntos_fuertes or "ninguno"}
- Puntos débiles: {datos.puntos_debiles or "ninguno"}
- Lesiones: {datos.lesiones or "ninguna"}
- Intensidad deseada: {datos.entrenar_fuerte or "media"}
- Materiales disponibles: {datos.materiales}
- Alergias: {datos.alergias or "ninguna"}
- Restricciones dieta: {datos.restricciones_dieta or "ninguna"}
- Idioma: {idioma}

{texto_dieta}
{texto_rutina}

IMPORTANTE: Devuelve únicamente un JSON válido, con esta estructura exacta:

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

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.85
    )

    contenido = response.choices[0].message.content
    print("Respuesta cruda de GPT:", contenido)

    # Buscar el primer bloque JSON que aparezca en la respuesta
    json_match = re.search(r'\{[\s\S]*\}', contenido)
    if not json_match:
        raise ValueError("No se encontró un JSON válido en la respuesta de GPT")

    data = json.loads(json_match.group(0))

    return {
        "rutina": data["rutina"],
        "dieta": data["dieta"],
        "motivacion": data["motivacion"]
    }
