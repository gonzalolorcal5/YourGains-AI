# app/routes/articles.py
"""Endpoint para artículos científicos de fitness/nutrición."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Usuario

router = APIRouter()


def _build_articles(is_premium: bool) -> list:
    """Construye la lista de 15 artículos. Los primeros 3 son gratuitos, del 4 al 15 requieren premium."""
    return [
        {
            "id": 1,
            "title": "Hipertrofia Muscular: Más Allá del 'Levantar Peso'",
            "category": "Entrenamiento",
            "is_accessible": True,
            "content": [
                "¿Por qué tus músculos crecen? No es solo 'levantar peso'. La hipertrofia responde a tres mecanismos científicos: tensión mecánica (la carga que levantas), daño muscular (microlesiones que se reparan más grandes) y estrés metabólico (acumulación de lactato que activa señales anabólicas). Entender esto te permite entrenar de forma inteligente, no solo intensa.",
                "Volumen e Intensidad: Los Factores Decisivos. La ciencia es clara: necesitas 10-20 series semanales por grupo muscular para maximizar hipertrofia. Menos de 10 deja ganancias sobre la mesa, más de 20 puede sobreentrenarte. Y no todas las repeticiones cuentan igual: solo las últimas 5 reps de cada serie (cerca del fallo muscular) generan el estímulo real. Por eso trabajar a RIR 1-3 (dejar 1-3 reps en el tanque) es la estrategia óptima: suficiente intensidad sin fatiga excesiva.",
                "Aplicación Práctica. Acumula 10-20 series por músculo/semana, entrena cada grupo 2-3 veces/semana, termina series a RIR 1-3, y combina rangos: 6-8 reps para tensión mecánica, 10-15 para volumen, 15-20 para estrés metabólico. Estos son los fundamentos no negociables del crecimiento muscular.",
            ],
            "references": [
                {"title": "The mechanisms of muscle hypertrophy and their application to resistance training", "pmid": "20847704"},
                {"title": "Dose-response relationship between weekly resistance training volume and increases in muscle mass", "pmid": "28834797"},
            ],
            "tags": ["Hipertrofia", "Volumen", "Intensidad"],
        },
        {
            "id": 2,
            "title": "Timing de Proteínas: ¿Mito o Realidad?",
            "category": "Nutrición",
            "is_accessible": True,
            "content": [
                "La 'ventana anabólica' de 30 minutos post-entreno es uno de los mitos más extendidos del fitness. La ciencia actual muestra que esta ventana es mucho más amplia: hasta 4-6 horas. Lo que realmente importa es tu ingesta total de proteína al día (1.6-2.2g/kg de peso corporal) distribuida en 3-5 comidas.",
                "Sin embargo, el timing SÍ importa en casos específicos: si entrenas en ayunas, consumir proteína post-entreno acelera la recuperación. Si tu última comida fue hace más de 4 horas, también es importante. Para el resto, la prioridad es cumplir tu meta diaria de proteína, no obsesionarte con el reloj.",
            ],
            "references": [
                {"title": "International Society of Sports Nutrition position stand: nutrient timing", "pmid": "29368182"},
            ],
            "tags": ["Proteína", "Timing", "Nutrición Deportiva"],
        },
        {
            "id": 3,
            "title": "Frecuencia de Entrenamiento Óptima",
            "category": "Entrenamiento",
            "is_accessible": True,
            "content": [
                "¿Entrenar cada músculo 1, 2 o 3 veces por semana? La investigación muestra que frecuencias de 2-3x/semana producen mayores ganancias que 1x/semana cuando el volumen total se iguala. Esto se debe a que la síntesis proteica muscular (MPS) se eleva solo 24-48h después del entrenamiento. Esperar 7 días entre sesiones deja 3-4 días sin estímulo anabólico.",
                "Aplicación: Si haces 15 series semanales de pecho, mejor dividirlas en 3 sesiones de 5 series cada una que hacer 15 series en un solo día. Esto permite mayor calidad de ejecución y mejor recuperación entre series.",
            ],
            "references": [
                {"title": "Effects of Resistance Training Frequency on Measures of Muscle Hypertrophy", "pmid": "27102172"},
            ],
            "tags": ["Frecuencia", "Split", "Programación"],
        },
        {
            "id": 4,
            "title": "El Rol del Sueño en la Composición Corporal",
            "category": "Recuperación",
            "is_accessible": is_premium,
            "content": [
                "Dormir menos de 7 horas puede reducir hasta un 60% la pérdida de grasa en una dieta hipocalórica, mientras aumenta la pérdida de masa muscular. Durante el sueño profundo se libera el 95% de la hormona de crecimiento diaria.",
                "Optimización: 7-9 horas, oscuridad total, temperatura 18-20°C, evitar pantallas 1h antes.",
            ],
            "references": [
                {"title": "Insufficient sleep undermines dietary efforts to reduce adiposity", "pmid": "20921542"},
            ],
            "tags": ["Sueño", "Hormonas", "Recuperación"],
        },
        {
            "id": 5,
            "title": "Síntesis Proteica y Dosis de Leucina",
            "category": "Nutrición",
            "is_accessible": is_premium,
            "content": [
                "La leucina es el aminoácido clave que 'enciende' la síntesis proteica muscular. Estudios muestran que 2.5-3g de leucina por comida es el umbral para maximizar la respuesta. Esto equivale a ~25-30g de proteína de alta calidad (whey, huevo, carne) por comida.",
                "Para veganos: combinar legumbres con cereales o añadir suplementación de leucina puede ayudar a alcanzar el umbral anabólico.",
            ],
            "references": [
                {"title": "Evaluating the Leucine Trigger Hypothesis", "pmid": "33133112"},
            ],
            "tags": ["Leucina", "MPS", "Proteína"],
        },
        {
            "id": 6,
            "title": "Deloads y Periodización del Volumen",
            "category": "Entrenamiento",
            "is_accessible": is_premium,
            "content": [
                "Incluir una semana de deload (50-60% volumen/intensidad) cada 4-6 semanas permite recuperación del sistema nervioso y reduce riesgo de sobreentrenamiento. La fatiga se acumula más rápido de lo que la percibes.",
                "Señales de que necesitas un deload: estancamiento en progresión, sueño alterado, irritabilidad, menor motivación.",
            ],
            "references": [
                {"title": "Recovery and fatigue in sport", "pmid": "29105705"},
            ],
            "tags": ["Deload", "Periodización", "Recuperación"],
        },
        {
            "id": 7,
            "title": "Superávit Calórico Óptimo para Ganancia Muscular",
            "category": "Nutrición",
            "is_accessible": is_premium,
            "content": [
                "Un superávit de 300-500 kcal/día maximiza ganancia muscular minimizando acumulación de grasa. Superávits mayores a 500 kcal aumentan desproporcionadamente la ganancia de grasa sin beneficios adicionales de músculo.",
                "Los principiantes pueden ganar músculo en mantenimiento o ligero déficit. Los avanzados necesitan superávit controlado para progresar.",
            ],
            "references": [
                {"title": "A systematic review of dietary protein during caloric restriction", "pmid": "29466592"},
            ],
            "tags": ["Superávit", "Volumen", "Nutrición"],
        },
        {
            "id": 8,
            "title": "Selección de Ejercicios para Hipertrofia",
            "category": "Entrenamiento",
            "is_accessible": is_premium,
            "content": [
                "Prioriza ejercicios compuestos que involucren múltiples articulaciones: sentadillas, peso muerto, press banca, remos, presses. Añade aislamientos para grupos rezagados o estética.",
                "La variabilidad moderada (cambiar ejercicios cada 6-8 semanas) puede ayudar a superar mesetas, pero la consistencia en los patrones de movimiento es clave.",
            ],
            "references": [
                {"title": "Exercise selection and muscle hypertrophy", "pmid": "29271849"},
            ],
            "tags": ["Ejercicios", "Hipertrofia", "Selección"],
        },
        {
            "id": 9,
            "title": "Carbohidratos y Rendimiento",
            "category": "Nutrición",
            "is_accessible": is_premium,
            "content": [
                "Los carbohidratos reponen glucógeno muscular y mejoran el rendimiento en entrenamientos de fuerza. 4-6g/kg/día es adecuado para atletas de fuerza activos.",
                "Timing: consumir la mayor parte de tus carbs alrededor del entrenamiento (pre y post) puede optimizar rendimiento y recuperación.",
            ],
            "references": [
                {"title": "Carbohydrates and exercise performance", "pmid": "22150460"},
            ],
            "tags": ["Carbohidratos", "Glucógeno", "Rendimiento"],
        },
        {
            "id": 10,
            "title": "RIR y Fallo Muscular",
            "category": "Entrenamiento",
            "is_accessible": is_premium,
            "content": [
                "RIR (Reps in Reserve) indica cuántas repeticiones te quedan en el tanque. Entrenar a RIR 1-3 (1-3 reps antes del fallo) maximiza hipertrofia sin la fatiga excesiva del fallo total.",
                "Llegar al fallo en cada serie no es necesario y puede aumentar el tiempo de recuperación. Úsalo solo en la última serie de ejercicios de aislamiento.",
            ],
            "references": [
                {"title": "Proximity to failure and muscular adaptations", "pmid": "33555822"},
            ],
            "tags": ["RIR", "Fallo", "Intensidad"],
        },
        {
            "id": 11,
            "title": "Grasas y Salud Hormonal",
            "category": "Nutrición",
            "is_accessible": is_premium,
            "content": [
                "Las grasas dietéticas son esenciales para la producción de hormonas como testosterona. Un mínimo de 0.5-0.7g/kg de grasas saludables (monoinsaturadas, omega-3) es recomendable.",
                "Evitar dietas extremadamente bajas en grasa (<15% calorías) puede afectar función hormonal y recuperación.",
            ],
            "references": [
                {"title": "Dietary fat and testosterone", "pmid": "29466592"},
            ],
            "tags": ["Grasas", "Hormonas", "Testosterona"],
        },
        {
            "id": 12,
            "title": "Cardio e Hipertrofia",
            "category": "Entrenamiento",
            "is_accessible": is_premium,
            "content": [
                "El cardio moderado no interfiere con la hipertrofia si el volumen total de entrenamiento se gestiona. Separa el cardio de las sesiones de fuerza por al menos 6 horas cuando sea posible.",
                "Para minimizar interferencia: prioriza cardio de baja intensidad (LISS) o HIIT en días de descanso de fuerza.",
            ],
            "references": [
                {"title": "Concurrent training and muscle hypertrophy", "pmid": "31230101"},
            ],
            "tags": ["Cardio", "Hipertrofia", "Concurrent training"],
        },
        {
            "id": 13,
            "title": "Suplementación Basada en Evidencia",
            "category": "Nutrición",
            "is_accessible": is_premium,
            "content": [
                "Los suplementos con evidencia sólida: creatina monohidrato (5g/día), proteína en polvo (si no alcanzas 1.6g/kg), cafeína pre-entreno, vitamina D si hay déficit.",
                "Evita suplementos con claims exagerados. La base es entrenamiento, nutrición y sueño. Los suplementos son el último 5%.",
            ],
            "references": [
                {"title": "ISSN position stand on protein", "pmid": "28642676"},
            ],
            "tags": ["Suplementos", "Creatina", "Evidencia"],
        },
        {
            "id": 14,
            "title": "Movilidad y Prevención de Lesiones",
            "category": "Recuperación",
            "is_accessible": is_premium,
            "content": [
                "La movilidad articular adecuada permite rangos de movimiento completos y reduce riesgo de lesión. Prioriza movilidad de cadera, hombros y columna torácica.",
                "Incluir 5-10 min de movilidad dinámica pre-entreno y estiramientos estáticos post-entreno (o en días de descanso) mejora la longevidad deportiva.",
            ],
            "references": [
                {"title": "Flexibility and injury risk", "pmid": "31931735"},
            ],
            "tags": ["Movilidad", "Lesiones", "Flexibilidad"],
        },
        {
            "id": 15,
            "title": "Diferencias Mujeres vs Hombres en Hipertrofia",
            "category": "Entrenamiento",
            "is_accessible": is_premium,
            "content": [
                "Las mujeres tienen la misma capacidad relativa de ganar músculo que los hombres (por unidad de masa magra). Las diferencias en masa absoluta se deben principalmente a tamaño corporal y niveles hormonales base.",
                "Las mujeres pueden tolerar mayor volumen de entrenamiento y recuperan más rápido entre sesiones. No necesitan programas 'especiales', sino los mismos principios aplicados a sus circunstancias.",
            ],
            "references": [
                {"title": "Sex differences in muscle hypertrophy", "pmid": "30734357"},
            ],
            "tags": ["Mujeres", "Hipertrofia", "Diferencias"],
        },
    ]


@router.get("/articles")
async def get_articles(
    user_id: int = Query(..., description="ID del usuario para verificar estado premium"),
    db: Session = Depends(get_db),
):
    """
    Devuelve la lista de 15 artículos científicos.
    Los primeros 3 son gratuitos, del 4 al 15 requieren premium.
    """
    is_premium = False
    if user_id:
        try:
            usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
            if usuario:
                is_premium = bool(usuario.is_premium) or (usuario.plan_type or "").upper() == "PREMIUM"
        except Exception:
            pass

    all_articles = _build_articles(is_premium)
    return {"articles": all_articles, "is_premium": is_premium}
