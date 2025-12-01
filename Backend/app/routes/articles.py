from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Usuario
from typing import List, Dict, Any
from pydantic import BaseModel

router = APIRouter()


class ArticleReference(BaseModel):
    title: str
    pmid: str


class Article(BaseModel):
    id: int
    title: str
    category: str  # "Entrenamiento" o "Nutrición"
    content: List[str]  # Lista de párrafos
    references: List[ArticleReference]
    tags: List[str]
    is_accessible: bool  # Si el usuario puede ver el contenido completo


class ArticlesResponse(BaseModel):
    articles: List[Article]
    is_premium: bool


# Base de datos de artículos (por ahora en memoria, luego se puede mover a BD o archivos)
ARTICLES_DB = []


def initialize_articles():
    """Inicializa los artículos estáticos para la sección Consejos y Estudios.

    Importante: el orden en esta lista define qué artículos son free (1-2) y
    cuáles quedan bloqueados para usuarios FREE (3-15).
    """
    global ARTICLES_DB

    ARTICLES_DB = [
        {
            "title": "¿Por qué crecen tus músculos?",
            "category": "Entrenamiento",
            "content": [
                "¿Por qué tus músculos crecen? No es solo 'levantar peso'. La hipertrofia responde a tres mecanismos científicos: tensión mecánica (la carga que levantas), daño muscular (microlesiones que se reparan más grandes) y estrés metabólico (acumulación de lactato que activa señales anabólicas). Entender esto te permite entrenar de forma inteligente, no solo intensa.",
                "Volumen e Intensidad: Los Factores Decisivos. La ciencia es clara: necesitas 10-20 series semanales por grupo muscular para maximizar hipertrofia. Menos de 10 deja ganancias sobre la mesa, más de 20 puede sobreentrenarte. Y no todas las repeticiones cuentan igual: solo las últimas 5 reps de cada serie (cerca del fallo muscular) generan el estímulo real. Por eso trabajar a RIR 1-3 (dejar 1-3 reps en el tanque) es la estrategia óptima: suficiente intensidad sin fatiga excesiva.",
                "Aplicación Práctica. Acumula 10-20 series por músculo/semana, entrena cada grupo 2-3 veces/semana, termina series a RIR 1-3, y combina rangos: 6-8 reps para tensión mecánica, 10-15 para volumen, 15-20 para estrés metabólico. Estos son los fundamentos no negociables del crecimiento muscular."
            ],
            "references": [
                {
                    "title": "The mechanisms of muscle hypertrophy and their application to resistance training",
                    "pmid": "20847704",
                },
                {
                    "title": "Dose-response relationship between weekly resistance training volume and increases in muscle mass",
                    "pmid": "28834797",
                },
            ],
            "tags": ["hipertrofia", "volumen", "intensidad", "tensión mecánica", "RIR"],
        },
        {
            "title": "Por qué es un error tomar solo proteína después de entrenar",
            "category": "Nutrición",
            "content": [
                "Durante el entrenamiento vacías poco a poco tus depósitos de glucógeno muscular, que son tu principal fuente de energía. Al terminar, el cuerpo tiene una prioridad clara: rellenar ese combustible lo antes posible para poder rendir bien en la siguiente sesión.",
                "Si después de entrenar tomas solo proteína, tu cuerpo activa la gluconeogénesis: convierte parte de esos aminoácidos en glucosa para reponer glucógeno. En la práctica, estás usando la proteína como energía en lugar de destinarla a lo que realmente te interesa: reparar y construir músculo.",
                "La estrategia ganadora es combinar carbohidratos + proteína en la ventana post-entreno. Los carbohidratos recargan rápido el glucógeno y la proteína se dedica casi al 100% a la síntesis muscular. Una referencia práctica: 20-40\u00a0g de proteína + 40-80\u00a0g de carbohidratos (por ejemplo, batido con plátano y avena, arroz con pollo o patata con atún)."
            ],
            "references": [
                {
                    "title": "Carbohydrate and protein co-ingestion augments skeletal muscle glycogen synthesis",
                    "pmid": "33507402",
                },
                {
                    "title": "Impact of Muscle Glycogen Availability on the Capacity for Repeated Exercise in Man",
                    "pmid": "29519691",
                },
                {
                    "title": "Biochemistry, Gluconeogenesis",
                    "pmid": "31082163",
                },
            ],
            "tags": ["gluconeogénesis", "post-entreno", "glucógeno", "carbohidratos", "timing nutricional"],
        },
        {
            "title": "Proteína recomendada para maximizar las ganancias musculares",
            "category": "Nutrición",
            "content": [
                "¿Cuánta proteína necesitas realmente? Si entrenas para hipertrofia, el meta-análisis de Morton (2018) establece el rango óptimo en 1.6-2.2\u00a0g/kg/día. De 0.8 a 1.5\u00a0g/kg ves mejoras significativas, de 1.5 a 2.0\u00a0g/kg las mejoras son pequeñas pero presentes, y más allá de 2.2\u00a0g/kg no hay beneficios adicionales. Si eres principiante o intermedio, 1.6\u00a0g/kg es tu objetivo. En déficit calórico aumenta a 2.0-2.4\u00a0g/kg para preservar músculo mientras pierdes grasa.",
                "La distribución: menos importante de lo que piensas. Durante años se repitió el dogma de 4-5 comidas con 25-40\u00a0g cada una. La ciencia moderna lo ha matizado: equiparando la proteína total, no hay diferencias significativas entre distribuciones convencionales versus concentradas. Estudios con ayuno intermitente 16/8 donde sujetos consumieron 1.6\u00a0g/kg en ventanas de 8 horas mostraron ganancias equivalentes a distribuciones de 4-5 comidas. Lo determinante es la proteína total diaria, no el número de comidas.",
                "Desmentido: el mito de solo absorbes 30\u00a0g por comida. Este es uno de los mitos más extendidos y completamente falso. Estudios compararon 25\u00a0g versus 100\u00a0g de proteína midiendo durante 12 horas: el cuerpo sí absorbe y utiliza los 100\u00a0g. La distinción clave: el cuerpo absorbe prácticamente toda la proteína que consumes. La leucina es el aminoácido que activa mTOR y dispara la construcción muscular: necesitas 2-3\u00a0g de leucina por comida (equivalente a 20-30\u00a0g de proteína de calidad) para maximizar cada estímulo anabólico."
            ],
            "references": [
                {
                    "title": "A systematic review, meta-analysis and meta-regression of the effect of protein supplementation on resistance training-induced gains in muscle mass and strength",
                    "pmid": "28698222",
                },
                {
                    "title": "Evidence-based recommendations for natural bodybuilding contest preparation: nutrition and supplementation",
                    "pmid": "24864135",
                },
                {
                    "title": "How much protein can the body use in a single meal for muscle-building?",
                    "pmid": "29497353",
                },
            ],
            "tags": ["proteína", "leucina", "mTOR", "distribución", "absorción"],
        },
        {
            "title": "Volumen de entrenamiento en superávit vs en déficit",
            "category": "Entrenamiento",
            "content": [
                "El volumen de entrenamiento (series efectivas por músculo/semana) es el factor más importante para la hipertrofia después de la intensidad. La ciencia muestra una relación dosis-respuesta: más volumen produce más músculo, pero solo hasta un punto. El meta-análisis de Schoenfeld (2017) establece el rango óptimo en 12-20 series semanales por grupo muscular. Menos de 12 deja ganancias sobre la mesa, más de 20 no produce beneficio adicional. Una serie solo es efectiva si alcanzas suficiente esfuerzo: RIR 3 o menos (dejar máximo 3 reps en el tanque).",
                "La clave está en tu estado nutricional. En superávit calórico (volumen), tu cuerpo tiene exceso de energía para recuperarse, puedes operar en el rango alto: 16-20 series semanales. En déficit calórico (definición), tu capacidad de recuperación está comprometida, debes reducir volumen al rango bajo: 10-14 series semanales para evitar sobreentrenamiento. La estrategia ganadora: mantén la intensidad alta (RIR 1-3 y cargas pesadas) pero ajusta el número total de series según tu estado calórico.",
                "Aplicación práctica. Principiantes (0-12 meses): 6-12 series/semana. Intermedios/Avanzados (12+ meses): 12-20 series/semana en superávit, 10-14 series/semana en déficit. Entrena cada músculo 2 veces/semana distribuyendo 6-10 series por sesión. Una vez alcances tu rango óptimo, progresa aumentando carga (más peso) y esfuerzo (RIR más bajo), no añadiendo más series indefinidamente."
            ],
            "references": [
                {
                    "title": "Dose-response relationship between weekly resistance training volume and increases in muscle mass",
                    "pmid": "27433992",
                },
                {
                    "title": "A Systematic Review of The Effects of Different Resistance Training Volumes on Muscle Hypertrophy",
                    "pmid": "35291645",
                },
                {
                    "title": "Training volume increases or maintenance: effects on muscular adaptations",
                    "pmid": "38970765",
                },
                {
                    "title": "Resistance Training Volume Enhances Muscle Hypertrophy but Not Strength in Trained Men",
                    "pmid": "30153194",
                },
            ],
            "tags": ["volumen", "series", "MAV", "RIR", "hipertrofia"],
        },
        {
            "title": "Frecuencia 1 vs frecuencia 2",
            "category": "Entrenamiento",
            "content": [
                "La variable que realmente impulsa la hipertrofia es el volumen semanal total (aprox. 12-20 series efectivas por grupo muscular). La frecuencia (cuántas veces entrenas ese músculo a la semana) es la herramienta para repartir bien ese volumen. La evidencia muestra que entrenar un músculo 2 veces por semana suele generar más hipertrofia que solo 1 vez cuando el volumen es el mismo.",
                "El problema de la frecuencia 1 es que intentas meter todo el volumen en una sola sesión: por ejemplo, 18-20 series en un día. Las primeras 8-10 series son de calidad, pero a partir de la serie 12 la fatiga hace que bajes carga, técnica y esfuerzo real, y muchas series se convierten en volumen basura. En cambio, con frecuencia 2 puedes hacer 2 sesiones de 9-10 series cada una: llegas más fresco, mantienes RIR 1-3 en casi todas las series y aprovechas mejor cada serie.",
                "Recomendación práctica: siempre que tu agenda lo permita, apunta a frecuencia 2. Si tu objetivo son 16-20 series semanales para un músculo, es mucho más eficiente hacer 2 sesiones de 8-10 series intensas que una sola maratón de 20. La clave no es entrenar más días por obsesión, sino repartir el volumen para que casi todas tus series sean buenas de verdad."
            ],
            "references": [
                {
                    "title": "Effects of Resistance Training Frequency on Measures of Muscle Hypertrophy: A Systematic Review and Meta-Analysis",
                    "pmid": "27102172",
                },
                {
                    "title": "How many times per week should a muscle be trained to maximize muscle hypertrophy?",
                    "pmid": "30558493",
                },
                {
                    "title": "Dose-response relationship between weekly resistance training volume and increases in muscle mass",
                    "pmid": "27433992",
                },
            ],
            "tags": ["frecuencia", "volumen", "fullbody", "split", "PPL", "upper lower"],
        },
        {
            "title": "¿Por qué se recomienda siempre 12 repeticiones?",
            "category": "Entrenamiento",
            "content": [
                "Durante décadas se ha repetido el dogma de que 1-5 reps son para fuerza, 6-12 para hipertrofia y 15+ para resistencia. La investigación moderna lo ha desacreditado. Meta-análisis como el de Schoenfeld (2021) y estudios como el de Campos (2002) muestran que rangos de 3-30 repeticiones producen hipertrofia prácticamente idéntica cuando el volumen total y la proximidad al fallo son iguales. En el estudio de Campos, grupos que entrenaron con 2-4, 8-12 y 25-35 repeticiones obtuvieron crecimientos musculares del 11.9%, 12.2% y 11.4% respectivamente: diferencias mínimas y no significativas.",
                "Lo que realmente importa no es si haces 8, 12 o 20 repeticiones, sino cuán cerca llegas del fallo (RIR) y cuántas series efectivas acumulas a la semana. Series a RIR 0-1 producen el estímulo máximo, RIR 2-3 sigue siendo casi igual de efectivo, y por encima de 4 RIR el estímulo cae mucho, independientemente del rango de reps. Además, necesitas unas 12-20 series efectivas por músculo y semana para maximizar hipertrofia, uses el rango que uses.",
                "Entonces, ¿por qué se recomiendan siempre 10-12 reps? Porque es un rango muy práctico, no porque sea mágico. Con 8-12 repeticiones consigues buen equilibrio entre tensión mecánica, estrés metabólico y tiempo bajo tensión, puedes acumular volumen en 5-10 series por músculo sin que la sesión se alargue demasiado, la técnica se mantiene estable y el riesgo de lesión es bajo. Pero puedes ganar el mismo músculo entrenando pesado (3-8 reps) o con más reps (15-20) si ajustas el número de series y te mantienes en RIR 1-3."
            ],
            "references": [
                {
                    "title": "A Re-Examination of the Repetition Continuum",
                    "pmid": "",
                },
                {
                    "title": "Muscular adaptations in response to three different resistance-training regimens",
                    "pmid": "12436270",
                },
                {
                    "title": "Neither load nor systemic hormones determine resistance training-mediated hypertrophy",
                    "pmid": "27928218",
                },
                {
                    "title": "Effects of Low- vs. High-Load Resistance Training on Muscle Strength and Hypertrophy",
                    "pmid": "25530577",
                },
            ],
            "tags": ["rango repeticiones", "continuum", "RIR", "proximidad fallo", "hipertrofia"],
        },
        {
            "title": "Déficit calórico óptimo: perder grasa sin perder músculo",
            "category": "Nutrición",
            "content": [
                "El error más común en definición es pensar que perder grasa es simplemente comer menos. Los estudios revelan algo crítico: cuando creas el déficit solo reduciendo calorías, pierdes aproximadamente 24-28% del peso total en forma de músculo. Si pierdes 10 kg solo con dieta estricta, 2.5-3 kg serán músculo. En contraste, cuando combinas déficit moderado por dieta más ejercicio, solo pierdes ~13% en músculo (casi la mitad). En la misma pérdida de 10 kg, solo 1.3 kg serían músculo.",
                "La estrategia óptima es un déficit mixto donde comes prácticamente tus calorías de mantenimiento y el déficit viene sobre todo del movimiento. En lugar de recortar 500 kcal de golpe en la dieta, mantén tu ingesta cercana a lo que deberías consumir y genera ese déficit con 200-400 kcal diarias de cardio o actividad extra (caminar más, subir escaleras, etc.). Así pasas menos hambre, rindes mejor entrenando y tu metabolismo se resiente mucho menos.",
                "Implementación práctica. Calcula aproximadamente tus calorías de mantenimiento, mantén tu ingesta muy cerca de ese valor y añade 2-4 sesiones semanales de cardio moderado (30-45 min) o más pasos diarios para crear el déficit. CRÍTICO: mantén o aumenta el volumen de entrenamiento de fuerza. El entrenamiento pesado con 12-16 series semanales por músculo a RIR 1-3 es la señal que le dice a tu cuerpo que necesitas ese músculo. Aumenta proteína a 2.0-2.4 g/kg. Monitorea peso semanalmente: si pierdes más de 0.7%/semana, come un poco más; si menos de 0.5%/semana, añade algo más de actividad."
            ],
            "references": [
                {
                    "title": "Exercise-training enhances fat-free mass preservation during diet-induced weight loss",
                    "pmid": "8130813",
                },
                {
                    "title": "Effects of Weight Loss on Lean Mass, Strength, Bone, and Aerobic Capacity",
                    "pmid": "27580151",
                },
                {
                    "title": "Effect of two different weight-loss rates on body composition and strength in elite athletes",
                    "pmid": "21558571",
                },
            ],
            "tags": ["déficit calórico", "pérdida de grasa", "preservación muscular", "cardio", "definición"],
        },
        {
            "title": "RIR y fallo muscular: la verdad que necesitas saber",
            "category": "Entrenamiento",
            "content": [
                "¿Qué es el fallo muscular? Es el punto donde no puedes completar otra repetición con buena técnica aunque aprietes al máximo y la barra se mueva lenta. Justo en esas últimas repeticiones, cuando notas la máxima quemazón, es donde se concentra la mayor tensión mecánica y el daño muscular que dispara la hipertrofia. RIR (Repeticiones en Reserva) mide cuántas reps más podrías hacer: RIR 0 = fallo absoluto, RIR 1 = podrías hacer 1 más, RIR 2-3 = margen pequeño pero aún efectivo.",
                "Los meta-análisis recientes son claros: cuando igualas el volumen, entrenar al fallo (RIR 0) no genera más músculo que quedarte muy cerca (RIR 1-3). La gran desventaja del fallo es la fatiga desproporcionada: destroza tu sistema nervioso, empeora tu rendimiento en las series siguientes y reduce el volumen total que puedes hacer. Por eso, en ejercicios compuestos pesados (sentadilla, press banca, peso muerto) lo inteligente es quedarse en RIR 2-3, y reservar el fallo o casi fallo (RIR 0-1) para aislamientos y máquinas, donde la fatiga es local y el riesgo es muy bajo.",
                "Estrategia práctica: en un ejercicio haz las primeras series a RIR 1-2 y, como mucho, solo la última al fallo técnico (RIR 0). A lo largo del mesociclo puedes empezar en RIR 2-3 y acercarte progresivamente a RIR 1-2, tocando el fallo solo en las últimas semanas antes de descargar. Si eres principiante, ni siquiera necesitas fallo: trabaja cómodo en RIR 3-5, centrado en aprender técnica y en acumular buen volumen."
            ],
            "references": [
                {
                    "title": "Effects of Resistance Training Performed to Failure or Not to Failure on Muscle Strength, Hypertrophy, and Power Output",
                    "pmid": "33555822",
                },
                {
                    "title": "Exploring the Dose-Response Relationship Between Estimated Resistance Training Proximity to Failure",
                    "pmid": "38970765",
                },
            ],
            "tags": ["RIR", "fallo muscular", "autoregulación", "fatiga", "compuestos", "aislamientos"],
        },
        {
            "title": "Selección de ejercicios: la combinación ganadora para hipertrofia",
            "category": "Entrenamiento",
            "content": [
                "No es compuestos o aislamientos, es compuestos y aislamientos. Los ejercicios multiarticulares (sentadilla, press banca, dominadas, peso muerto) son la base porque permiten usar más carga, desarrollan fuerza global y son muy eficientes en tiempo. Los ejercicios analíticos (curl de bíceps, aperturas, extensiones de tríceps, elevaciones laterales) son el complemento que te permite añadir volumen extra con poca fatiga sistémica y atacar músculos rezagados. La evidencia muestra que añadir aislamientos a un programa de solo compuestos produce ganancias adicionales de masa muscular.",
                "El orden importa: primero compuestos, luego aislamientos. Al inicio de la sesión estás fresco y es cuando debes hacer los movimientos pesados y técnicamente exigentes (sentadilla, press banca, remos, presses por encima de la cabeza). Deja los ejercicios analíticos y las máquinas para el final, cuando ya estás más fatigado pero puedes seguir exprimiendo al músculo con movimientos simples y seguros. Para hipertrofia pura, pesos libres y máquinas funcionan igual de bien si equiparas volumen e intensidad, pero las máquinas son oro para entrenar al fallo con seguridad y para aislar mejor sin que fallen los estabilizadores.",
                "Aplicación práctica: para cada músculo combina 1-2 compuestos y 1-2 analíticos en rango completo de movimiento. Por ejemplo, pectoral: press inclinado + press horizontal + aperturas; espalda: dominadas o jalón + remo; piernas: una dominante de rodilla (sentadilla o hack) + una dominante de cadera (peso muerto rumano) + extensiones o curls; hombros: press militar + elevaciones laterales + pájaros. Con 12-20 series semanales por músculo, usando esta combinación y ROM completo, cubres tanto la base de fuerza como el volumen fino que marca la diferencia estética."
            ],
            "references": [
                {
                    "title": "Resistance Training with Single vs. Multi-joint Exercises at Equal Total Load Volume",
                    "pmid": "",
                },
                {
                    "title": "Effects of Adding Single Joint Exercises to a Resistance Training Programme in Trained Women",
                    "pmid": "",
                },
                {
                    "title": "The effects of pre-exhaustion, exercise order, and rest intervals in a full-body resistance training",
                    "pmid": "",
                },
                {
                    "title": "Effects of range of motion on muscle development during resistance training interventions",
                    "pmid": "PMC6977096",
                },
            ],
            "tags": ["selección ejercicios", "compuestos", "aislamientos", "peso libre", "máquinas", "ROM"],
        },
        {
            "title": "Sobrecarga progresiva: el factor más importante para crecer",
            "category": "Entrenamiento",
            "content": [
                "Si repites exactamente el mismo peso y las mismas repeticiones semana tras semana, tu cuerpo no tiene motivo para construir más músculo. La sobrecarga progresiva es el principio que explica por qué ganas masa: obligas al cuerpo a adaptarse aumentando poco a poco el estrés que recibe el músculo (más peso, más repeticiones o mejor ejecución). Sin progresión, solo estás manteniendo.",
                "La forma más sencilla y efectiva de aplicar este principio es la doble progresión. Elige un rango de repeticiones, por ejemplo 8-12. Mantén el peso fijo y trata de ir sumando repeticiones sesión a sesión. Cuando seas capaz de hacer 12 o más repeticiones en todas tus series con buena técnica (por ejemplo 3×12), sube un poco el peso y vuelve a caer a 8-10 reps. Después de unas cuantas sesiones, cuando vuelvas a alcanzar 12 o más reps, vuelves a subir el peso. Círculo cerrado: siempre que completes el rango alto, aumentas carga.",
                "En la práctica: empieza con un peso que te permita 8-10 reps buenas. Anota peso y repeticiones en cada sesión. Tu objetivo es que, con el tiempo, veas cómo las mismas cargas se mueven con más repeticiones, y que esas cargas también suben cuando llegas al tope del rango. No hace falta añadir 5 kg cada semana: a veces progresar 1-2 reps o subir 1-2 kg tras varias semanas ya es una gran victoria. Lo importante es que, mes a mes, tu registro muestre una tendencia clara de mejora."
            ],
            "references": [
                {
                    "title": "Effects of Resistance Training Overload Progression Protocols on Strength and Muscle Mass",
                    "pmid": "38286426",
                },
                {
                    "title": "Progressive overload without progressing load? The effects of progressing load vs. repetitions",
                    "pmid": "PMC9528903",
                },
            ],
            "tags": ["sobrecarga progresiva", "progresión", "doble progresión", "plateau", "hipertrofia"],
        },
        {
            "title": "Si no duermes no te puedes poner fuerte",
            "category": "Entrenamiento",
            "content": [
                "Puedes clavar el entrenamiento y la dieta, pero si duermes mal tus resultados se hunden. El músculo no crece en el gimnasio: el entreno solo da el estímulo; la construcción real ocurre mientras duermes, cuando el cuerpo repara fibras y consolida adaptaciones. Dormir poco eleva el cortisol, reduce la testosterona y corta la liberación de hormona de crecimiento, creando un entorno catabólico donde te cuesta ganar músculo y pierdes más en cada definición.",
                "La mayor parte de la síntesis proteica y de la reparación muscular se concentra en las horas posteriores al entrenamiento y, sobre todo, durante el sueño profundo. Dormir 7-9 horas por noche no es un lujo, es un requisito básico para progresar de forma constante. Un hábito práctico muy útil es tomar 20-30 g de proteína lenta (por ejemplo caseína o yogur griego) 30-60 minutos antes de acostarte, para darle al músculo aminoácidos durante la noche mientras el cuerpo hace el trabajo de reparación.",
                "Si arrastras semanas de sueño corto, lo notarás en todo: fuerzas estancadas, más fatiga, peor concentración y más facilidad para lesionarte. Antes de complicarte con detalles avanzados, asegúrate de cumplir esta jerarquía: entrenar duro, comer lo suficiente con buena proteína y, sobre todo, dormir 7-9 horas de calidad cada noche. Sin eso, literalmente estás entrenando con el freno de mano puesto."
            ],
            "references": [
                {
                    "title": "Sleep quality and muscular strength in college students",
                    "pmid": "28490639",
                },
                {
                    "title": "The effects of protein supplementation before sleep on muscle mass and strength",
                    "pmid": "",
                },
            ],
            "tags": ["sueño", "recuperación", "testosterona", "cortisol", "GH", "MPS"],
        },
        {
            "title": "Adaptaciones musculares: por qué ganas fuerza tan rápido al principio",
            "category": "Entrenamiento",
            "content": [
                "Por qué doblas tu fuerza en 6 semanas sin crecer músculo. El músculo NO crece las primeras 4-6 semanas de entrenamiento, pero tu fuerza puede duplicarse o triplicarse. Este fenómeno se llama newbie gains y tiene una explicación clara: adaptaciones neurales. Durante las primeras semanas, tu cerebro aprende a reclutar unidades motoras que antes estaban dormidas, aumenta la frecuencia de disparo neural, mejora la coordinación y reduce la inhibición del Golgi. Pasas de 40 kg a 80 kg en press banca en 6 semanas sin que tus brazos crezcan. Toda esa fuerza viene del sistema nervioso, no del músculo.",
                "Timeline: cuándo cambia el sistema nervioso vs el músculo. Semanas 1-4: adaptaciones neurales dominan completamente. Tu cerebro aprende el movimiento, activa más fibras, mejora coordinación. Fuerza sube rápido, músculo no crece. Semanas 4-6: adaptaciones neurales continúan, hipertrofia empieza pero aún no es medible. Semanas 6-8+: la hipertrofia estructural se vuelve medible. A partir de aquí, ganancias de fuerza vienen principalmente de más músculo. Si llevas 2-3 semanas y no ves músculo, es NORMAL. El músculo viene después.",
                "Principiantes vs avanzados: por qué el progreso se ralentiza. Principiantes (0-12 meses) pueden añadir 2.5-5 kg semanal y ganan 20-40% de fuerza en 8-12 semanas porque tienen margen enorme de adaptación neural. Avanzados (3+ años) ya agotaron adaptaciones neurales y solo tienen pequeñas ganancias estructurales, tal vez 5-15% en 12 semanas. Si entrenaste años, paraste 6 meses y perdiste músculo, recuperarás todo mucho más rápido gracias a la memoria muscular: los mionúcleos adicionales permanecen años después de atrofia y permiten síntesis proteica explosivamente más rápida al reentrenar."
            ],
            "references": [
                {
                    "title": "The Mechanisms of Muscle Hypertrophy and Their Application to Resistance Training",
                    "pmid": "20847704",
                },
                {
                    "title": "Neural adaptations to resistance training: Mechanisms and recommendations",
                    "pmid": "",
                },
            ],
            "tags": ["adaptaciones neurales", "newbie gains", "fuerza", "hipertrofia", "memoria muscular"],
        },
        {
            "title": "Síntesis proteica: cómo se construye músculo a nivel biológico",
            "category": "Nutrición",
            "content": [
                "El músculo crece cuando la Síntesis de Proteínas Musculares (MPS) supera la Degradación (MPB). Balance proteico neto = MPS - MPB. Si MPS > MPB, ganas músculo. La MPS puede aumentar 400-500% tras entrenamiento más proteína, y es el driver principal de hipertrofia. Solo la síntesis miofibrilar (actina/miosina) correlaciona con hipertrofia funcional y fuerza real. Cuando entrenas y comes proteína, maximizas esta síntesis específicamente: esto es construcción muscular a nivel molecular.",
                "El complejo mTORC1 es el interruptor que decide si construyes músculo. Para encenderlo necesitas 2 señales: tensión mecánica (entrenamiento) y leucina suficiente. La leucina es la señal maestra anabólica, no calorías ni insulina. Umbral crítico: 2-3 g de leucina por comida (equivalente a 20-30 g de proteína de calidad) para maximizar mTORC1. Sin leucina, no hay mTORC1. Sin mTORC1, no hay músculo. Una vez activado, mTORC1 incrementa la velocidad de síntesis miofibrilar.",
                "Aplicación práctica. La jerarquía es: 1) Ingesta total 1.6-2.2 g/kg/día, 2) Distribución en 3-5 comidas con 20-40 g de proteína cada una, 3) Timing peri-entreno (post-entreno 30-40 g whey, pre-sueño 30-50 g caseína para MPS nocturna). Novatos tienen ventana anabólica amplia (24-48 h), así que el timing es más flexible. Avanzados tienen ventana más corta (12-24 h), así que el timing peri-entreno es más crítico. La regla de oro: MPS > MPB = músculo. Leucina activa mTORC1. Entrenamiento más proteína = construcción muscular real."
            ],
            "references": [
                {
                    "title": "The anabolic response to protein ingestion has no upper limit in vivo in humans",
                    "pmid": "38118410",
                },
                {
                    "title": "A review of resistance training-induced changes in skeletal muscle protein synthesis",
                    "pmid": "25739559",
                },
                {
                    "title": "Evaluating the Leucine Trigger Hypothesis for Post-prandial Regulation of Muscle Protein Synthesis",
                    "pmid": "",
                },
            ],
            "tags": ["síntesis proteica", "MPS", "mTORC1", "leucina", "hipertrofia", "construcción muscular"],
        },
        {
            "title": "Tipos de fibras musculares: cómo entrenar cada una para máxima hipertrofia",
            "category": "Entrenamiento",
            "content": [
                "Tu músculo tiene 3 tipos de fibras con propiedades diferentes. TIPO I (lentas/rojas): alta resistencia, queman grasa, se activan primero, representan ~45-55% en sedentarios. TIPO IIa (rápidas versátiles): LAS MÁS IMPORTANTES PARA HIPERTROFIA, metabolismo dual, velocidad intermedia, son las más plásticas y pueden hipertrofiarse masivamente. Dominan (60-80% del área) en culturistas. TIPO IIx (explosivas puras): velocidad máxima, se agotan en 5-10 s, representan solo ~10-15% en sedentarios. Para hipertrofia máxima, las fibras IIa son tu prioridad porque son las que más crecen y representan la mayor parte del músculo en personas entrenadas.",
                "Cómo entrenar cada tipo. Las fibras Tipo I responden mejor a cargas ligeras (40-50% 1RM) con tensión continua. Las fibras Tipo IIa, que son las más importantes para hipertrofia, responden mejor a cargas moderadas-altas (70-85% 1RM) con 6-12 repeticiones. Las fibras Tipo IIx requieren cargas muy pesadas (85-95% 1RM) con 1-5 reps, pero entrenar al fallo las elimina. Para la mayoría de personas que buscan hipertrofia, el protocolo clásico de 6-12 repeticiones con cargas 70-85% 1RM es el óptimo porque maximiza el crecimiento de las fibras IIa, que son las que más crecen y representan la mayor parte del músculo."
            ],
            "references": [
                {
                    "title": "Human Skeletal Muscle Fiber Type Classifications",
                    "pmid": "",
                },
                {
                    "title": "Type 1 Muscle Fiber Hypertrophy after Blood Flow-restricted Training in Powerlifters",
                    "pmid": "",
                },
                {
                    "title": "Effects of velocity loss during resistance training on athletic performance",
                    "pmid": "",
                },
            ],
            "tags": ["tipos de fibra", "hipertrofia", "VBT", "BFR", "fibras rápidas", "fibras lentas"],
        },
        {
            "title": "Prevención de lesiones típicas: cómo entrenar sin lesionarte",
            "category": "Entrenamiento",
            "content": [
                "Las lesiones más comunes en el gimnasio son prevenibles. Las zonas que más sufren son: hombro (tendinitis del manguito rotador, muy común en press de banca frecuente), espalda lumbar (esguinces y distensiones por mala técnica en peso muerto o sentadillas), y rodilla (condromalacia rotuliana por desequilibrios musculares o técnica deficiente). Más de la mitad de las lesiones son distensiones musculares y esguinces, muchas veces causadas por no calentar o por mala forma al entrenar.",
                "Las causas principales son: no calentar (saltar el calentamiento eleva riesgo de lesión en un 30%), técnica incorrecta (la mayoría de lesiones ocurren por ejecución deficiente: espalda redondeada, rodillas colapsando, codos mal posicionados), sobrecarga y progresión brusca (aumentar peso o volumen demasiado rápido sin respetar adaptación), y falta de descanso (no recuperar entre sesiones acumula fatiga y predispone a lesiones).",
                "Cómo prevenirlas. Calienta siempre: 5-10 minutos de actividad ligera (caminar, trote suave) más calentamiento específico del grupo muscular que entrenarás (series ligeras con 50% del peso de trabajo). Prioriza técnica sobre peso: nunca sacrifiques la forma correcta por levantar más. Progresión gradual: aumenta solo una variable a la vez (peso, volumen o frecuencia). Fortalece estabilizadores: manguito rotador para hombros, core para espalda, glúteos para rodillas. Si sientes dolor agudo, detente inmediatamente. Más vale perder una serie que semanas de entrenamiento."
            ],
            "references": [
                {
                    "title": "Cómo evitar lesiones relacionadas con el ejercicio",
                    "pmid": "",
                },
                {
                    "title": "Injury Prevention in the Gym: How To Safely Maximize Your Workouts",
                    "pmid": "",
                },
            ],
            "tags": ["prevención lesiones", "calentamiento", "técnica", "manguito rotador", "lesiones comunes"],
        },
    ]


@router.get("/api/articles", response_model=ArticlesResponse)
def get_articles(
    user_id: int = Query(..., description="ID del usuario"),
    db: Session = Depends(get_db)
):
    """
    Devuelve los artículos con flags de acceso según el plan del usuario.
    - Usuarios FREE: Solo pueden ver los 3 primeros artículos completos
    - Usuarios PREMIUM: Ven todos los 15 artículos completos
    """
    try:
        # Obtener usuario
        user = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Verificar estado premium
        is_premium = (user.plan_type == "PREMIUM") or bool(user.is_premium)
        
        # Inicializar artículos si están vacíos
        if not ARTICLES_DB:
            initialize_articles()
        
        # Preparar respuesta con flags de acceso
        articles_response = []
        for idx, article_data in enumerate(ARTICLES_DB, start=1):
            # Artículos 1, 2 y 3: Acceso libre para todos
            # Artículos 4-15: Solo accesibles para Premium
            is_accessible = (idx <= 3) or is_premium
            
            article = Article(
                id=idx,
                title=article_data.get("title", ""),
                category=article_data.get("category", ""),
                content=article_data.get("content", []) if is_accessible else [],
                references=article_data.get("references", []) if is_accessible else [],
                tags=article_data.get("tags", []),
                is_accessible=is_accessible
            )
            articles_response.append(article)
        
        return ArticlesResponse(
            articles=articles_response,
            is_premium=is_premium
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo artículos: {str(e)}")


def add_article(article_data: Dict[str, Any]):
    """Función auxiliar para añadir un artículo a la base de datos."""
    global ARTICLES_DB
    ARTICLES_DB.append(article_data)


