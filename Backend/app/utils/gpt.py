import os
import json
import regex as re
import asyncio
from typing import Dict, Any, List
from dotenv import load_dotenv
from app.schemas import PlanRequest
from openai import AsyncOpenAI
from openai import RateLimitError, APIError
import logging
from app.utils.nutrition_calculator import get_complete_nutrition_plan
from fastapi import HTTPException

# ═══════════════════════════════════════════════════════
# 🔥 NUEVO: Importar sistema RAG
# ═══════════════════════════════════════════════════════
from app.utils.vectorstore import KnowledgeStore

# Cargar .env desde la raíz del proyecto Backend
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

# ═══════════════════════════════════════════════════════
# 🚀 CONFIGURACIÓN DE MODELO GPT-4o CON RAG
# ═══════════════════════════════════════════════════════

logger = logging.getLogger(__name__)

# 🎯 MODELO PRINCIPAL: GPT-4o para aprovechar sistema RAG completo
# Permite override con variable de entorno OPENAI_MODEL si es necesario
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Validar que la API key existe ANTES de crear el cliente
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    error_msg = "❌ OPENAI_API_KEY no encontrada en .env. Configura OPENAI_API_KEY en .env"
    print(error_msg)  # Usar print porque logger podría no estar configurado aún
    raise ValueError("API key de OpenAI requerida. Configura OPENAI_API_KEY en .env")

# Cliente OpenAI con timeout configurado (después de validar API key)
client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    timeout=120.0,  # 2 minutos para todas las llamadas
    max_retries=2    # Reintentar 2 veces automáticamente
)

# Logging de configuración
logger.info("=" * 80)
logger.info("🚀 CONFIGURACIÓN DE MODELO GPT")
logger.info("=" * 80)
logger.info(f"📦 Modelo seleccionado: {MODEL}")
logger.info(f"📚 Sistema RAG: 46 documentos científicos activos")
logger.info(f"💰 Costo estimado por plan: ~$0.015-0.025 (depende de tokens)")
logger.info(f"🔑 API Key: {'✅ Configurada' if OPENAI_API_KEY else '❌ No encontrada'}")
logger.info("=" * 80)


# ═══════════════════════════════════════════════════════
# 🔥 NUEVA FUNCIÓN: Generar embedding de texto
# ═══════════════════════════════════════════════════════
async def generate_embedding(text: str) -> List[float]:
    """
    Genera embedding de un texto usando OpenAI.
    
    Args:
        text: Texto a convertir en embedding
        
    Returns:
        Vector de embeddings (lista de floats)
    """
    try:
        response = await client.embeddings.create(
            model="text-embedding-3-small",  # Modelo de embeddings de OpenAI
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"❌ Error generando embedding: {e}")
        return []


# ═══════════════════════════════════════════════════════
# 🔥 NUEVA FUNCIÓN: Obtener contexto RAG para el chat
# ═══════════════════════════════════════════════════════
async def get_rag_context_for_chat(user_message: str) -> str:
    """
    Recupera contexto científico del RAG basado en el mensaje del usuario.
    
    Analiza el mensaje y busca documentos relevantes en la base de conocimiento.
    
    Args:
        user_message: Mensaje del usuario en el chat
        
    Returns:
        String con contexto científico formateado para inyectar en el prompt
    """
    
    logger.info("🔍 Recuperando contexto científico del RAG para chat...")
    
    # Generar embedding del mensaje del usuario
    query_embedding = await generate_embedding(user_message)
    
    if not query_embedding:
        logger.warning("⚠️ No se pudo generar embedding para el mensaje del chat")
        return ""
    
    # Buscar documentos relevantes
    try:
        results = KnowledgeStore.search(
            query_embedding=query_embedding,
            k=5,  # Top 5 documentos más relevantes
            language='es'
        )
        
        if not results:
            logger.info("⚠️ No se encontraron documentos relevantes en RAG")
            return ""
        
        # Ordenar por similitud (ya vienen ordenados)
        results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        
        # Tomar top 3 documentos únicos
        unique_docs = []
        seen_titles = set()
        
        for doc in results:
            title = doc.get('title', '')
            if title not in seen_titles:
                unique_docs.append(doc)
                seen_titles.add(title)
            
            if len(unique_docs) >= 3:
                break
        
        # Formatear contexto de manera más concisa para el chat
        context_parts = []
        context_parts.append("═" * 60)
        context_parts.append("📚 CONTEXTO CIENTÍFICO RELEVANTE")
        context_parts.append("═" * 60)
        context_parts.append("")
        context_parts.append("⚠️ INSTRUCCIÓN: Usa esta información científica para responder.")
        context_parts.append("Basate en estudios peer-reviewed. Si no hay información relevante, responde con tu conocimiento general.")
        context_parts.append("")
        
        for i, doc in enumerate(unique_docs, 1):
            title = doc.get('title', 'Sin título')
            content = doc.get('content', '')
            source = doc.get('source', '')
            similarity = doc.get('similarity', 0)
            
            # Limitar contenido a 500 caracteres para no sobrecargar el prompt
            content_short = content[:500] + "..." if len(content) > 500 else content
            
            context_parts.append(f"📄 {i}. {title}")
            context_parts.append(f"   Fuente: {source}")
            context_parts.append(f"   Relevancia: {similarity:.3f}")
            context_parts.append(f"   {content_short}")
            context_parts.append("")
        
        context_parts.append("═" * 60)
        context_parts.append("")
        
        final_context = "\n".join(context_parts)
        
        logger.info(f"✅ Contexto RAG generado para chat: {len(unique_docs)} documentos")
        
        return final_context
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo contexto RAG para chat: {e}")
        return ""


# ═══════════════════════════════════════════════════════
# 🔥 NUEVA FUNCIÓN: Obtener contexto RAG para el plan
# ═══════════════════════════════════════════════════════
async def get_rag_context_for_plan(datos: Dict[str, Any]) -> str:
    """
    Recupera contexto científico del RAG según el perfil del usuario.
    
    Hace queries específicas para:
    - Rutina de entrenamiento (según gym_goal y experiencia)
    - Plan nutricional (según nutrition_goal)
    - Recuperación y consejos avanzados
    
    Args:
        datos: Diccionario con datos del usuario
        
    Returns:
        String con contexto científico formateado para inyectar en el prompt
    """
    
    logger.info("🔍 Recuperando contexto científico del RAG...")
    
    # Extraer datos del usuario
    gym_goal = datos.get('gym_goal', 'ganar_musculo')
    nutrition_goal = datos.get('nutrition_goal', 'mantenimiento')
    experiencia = datos.get('experiencia', 'principiante')
    training_frequency = datos.get('training_frequency', 4)
    
    # Mapear objetivos a goals del RAG
    goal_mapping = {
        'ganar_musculo': 'hipertrofia',
        'ganar_fuerza': 'fuerza',
        'perder_grasa': 'perdida_grasa',
        'mantenimiento': 'definicion'
    }
    
    gym_goal_rag = goal_mapping.get(gym_goal, 'hipertrofia')
    nutrition_goal_rag = goal_mapping.get(nutrition_goal, 'definicion')
    
    # ═══════════════════════════════════════════════════════
    # CONSTRUIR QUERIES ESPECÍFICAS
    # ═══════════════════════════════════════════════════════
    
    queries = []
    
    # 1️⃣ QUERY PARA RUTINA - Hipertrofia/Fuerza según objetivo
    if gym_goal == 'ganar_musculo':
        queries.append({
            'text': f'entrenamiento hipertrofia muscular {experiencia} series repeticiones volumen óptimo',
            'category': 'training_knowledge',
            'goal': 'hipertrofia',
            'weight': 1.5  # Mayor peso para queries de rutina
        })
    elif gym_goal == 'ganar_fuerza':
        queries.append({
            'text': f'entrenamiento fuerza powerlifting {experiencia} series repeticiones descanso',
            'category': 'training_knowledge',
            'goal': 'fuerza',
            'weight': 1.5
        })
    
    # 2️⃣ QUERY PARA FRECUENCIA - Según días disponibles
    queries.append({
        'text': f'frecuencia entrenamiento óptima {training_frequency} días semana {gym_goal_rag}',
        'category': 'training_knowledge',
        'goal': gym_goal_rag,
        'weight': 1.2
    })
    
    # 3️⃣ QUERY PARA NUTRICIÓN - Según objetivo nutricional
    if nutrition_goal == 'volumen':
        queries.append({
            'text': 'superávit calórico volumen muscular macronutrientes distribución proteína',
            'category': 'nutrition_knowledge',
            'goal': 'volumen',
            'weight': 1.5
        })
    elif nutrition_goal == 'definicion':
        queries.append({
            'text': 'déficit calórico definición muscular macronutrientes proteína preservar masa',
            'category': 'nutrition_knowledge',
            'goal': 'perdida_grasa',
            'weight': 1.5
        })
    else:  # mantenimiento
        queries.append({
            'text': 'mantenimiento calórico macronutrientes distribución óptima',
            'category': 'nutrition_knowledge',
            'goal': 'definicion',
            'weight': 1.0
        })
    
    # 4️⃣ QUERY PARA MACROS - Distribución específica
    queries.append({
        'text': f'distribución macronutrientes {nutrition_goal_rag} proteína carbohidratos grasas',
        'category': 'nutrition_knowledge',
        'goal': nutrition_goal_rag,
        'weight': 1.3
    })
    
    # 5️⃣ QUERY PARA RECUPERACIÓN
    queries.append({
        'text': 'recuperación muscular descanso sueño hipertrofia',
        'category': 'training_knowledge',
        'goal': gym_goal_rag,
        'weight': 0.8
    })
    
    # ═══════════════════════════════════════════════════════
    # 🔥 NUEVO: QUERIES ESPECÍFICAS PARA MODIFICACIONES
    # ═══════════════════════════════════════════════════════
    
    # 6️⃣ QUERY PARA LESIONES (si hay información de lesión específica)
    lesiones = datos.get('lesiones', '')
    if lesiones and lesiones.lower() != 'ninguna' and len(lesiones) > 20:
        # Detectar parte del cuerpo lesionada
        body_parts = ['hombro', 'rodilla', 'espalda', 'codo', 'muñeca', 'tobillo', 'cadera', 'cuello', 'muñeca']
        detected_part = None
        for part in body_parts:
            if part in lesiones.lower():
                detected_part = part
                break
        
        if detected_part and ('evitar' in lesiones.lower() or 'lesión' in lesiones.lower() or 'dolor' in lesiones.lower()):
            queries.append({
                'text': f'lesión {detected_part} ejercicios alternativos entrenamiento seguro evitar',
                'category': 'training_knowledge',
                'goal': gym_goal_rag,
                'weight': 2.0  # Mayor peso porque es crítico para seguridad
            })
            queries.append({
                'text': f'adaptación rutina {detected_part} lesión ejercicios sustitutos',
                'category': 'training_knowledge',
                'goal': gym_goal_rag,
                'weight': 1.8
            })
            logger.info(f"🏥 Añadidas queries RAG para lesión: {detected_part}")
    
    # 7️⃣ QUERY PARA ALERGIAS ALIMENTARIAS (si hay alergias específicas)
    alergias = datos.get('alergias', '')
    if alergias and alergias.lower() != 'ninguna' and len(alergias) > 5:
        alergias_lower = alergias.lower()
        
        # Detectar tipo de alergia
        if 'lactosa' in alergias_lower or 'lácteo' in alergias_lower:
            queries.append({
                'text': 'dieta sin lactosa proteínas alternativas lácteos fitness',
                'category': 'nutrition_knowledge',
                'goal': nutrition_goal_rag,
                'weight': 2.0  # Crítico para salud
            })
            logger.info("🥛 Añadida query RAG para alergia a lactosa")
        
        if 'gluten' in alergias_lower or 'celíaco' in alergias_lower or 'celiaco' in alergias_lower:
            queries.append({
                'text': 'dieta celíaco sin gluten carbohidratos fitness',
                'category': 'nutrition_knowledge',
                'goal': nutrition_goal_rag,
                'weight': 2.0  # Crítico para salud
            })
            logger.info("🌾 Añadida query RAG para celiaquía")
        
        if 'frutos secos' in alergias_lower or 'fruto seco' in alergias_lower:
            queries.append({
                'text': 'proteínas alternativas frutos secos alergia dieta fitness',
                'category': 'nutrition_knowledge',
                'goal': nutrition_goal_rag,
                'weight': 2.0  # Crítico para salud
            })
            logger.info("🥜 Añadida query RAG para alergia a frutos secos")
        
        if 'huevo' in alergias_lower or 'huevos' in alergias_lower:
            queries.append({
                'text': 'proteínas alternativas huevo dieta fitness aminoácidos',
                'category': 'nutrition_knowledge',
                'goal': nutrition_goal_rag,
                'weight': 2.0  # Crítico para salud
            })
            logger.info("🥚 Añadida query RAG para alergia a huevo")
    
    # 8️⃣ QUERY PARA MATERIALES NO DISPONIBLES (si hay restricción de equipamiento)
    missing_equipment = datos.get('missing_equipment', '')
    if missing_equipment and missing_equipment.lower() != 'ninguno' and len(missing_equipment) > 3:
        missing_lower = missing_equipment.lower()
        
        if 'barra' in missing_lower or 'barra olímpica' in missing_lower:
            queries.append({
                'text': 'entrenamiento sin barra olímpica mancuernas alternativas ejercicios compuestos',
                'category': 'training_knowledge',
                'goal': gym_goal_rag,
                'weight': 1.8
            })
            logger.info("🏋️ Añadida query RAG para falta de barra olímpica")
        
        if 'banco' in missing_lower or 'banco press' in missing_lower:
            queries.append({
                'text': 'entrenamiento pecho sin banco flexiones variaciones peso corporal',
                'category': 'training_knowledge',
                'goal': gym_goal_rag,
                'weight': 1.8
            })
            logger.info("🪑 Añadida query RAG para falta de banco de press")
        
        if 'rack' in missing_lower or 'soporte' in missing_lower:
            queries.append({
                'text': 'sentadillas alternativas sin rack prensa máquina ejercicios piernas',
                'category': 'training_knowledge',
                'goal': gym_goal_rag,
                'weight': 1.8
            })
            logger.info("🏋️ Añadida query RAG para falta de rack")
    
    # 9️⃣ QUERY PARA ENFOQUE EN ÁREAS (si hay focus_area)
    focus_area = datos.get('focus_area')
    if focus_area:
        # Normalizar nombre del área
        area_mapping = {
            'brazos': 'brazos',
            'biceps': 'brazos',
            'triceps': 'brazos',
            'pecho': 'pecho',
            'pectoral': 'pecho',
            'piernas': 'piernas',
            'cuadriceps': 'piernas',
            'cuádriceps': 'piernas',
            'gluteos': 'glúteos',
            'glúteos': 'glúteos',
            'espalda': 'espalda',
            'dorsales': 'espalda',
            'hombros': 'hombros',
            'deltoides': 'hombros'
        }
        mapped_area = area_mapping.get(focus_area.lower(), focus_area.lower())
        
        queries.append({
            'text': f'hipertrofia {mapped_area} volumen óptimo series repeticiones frecuencia',
            'category': 'training_knowledge',
            'goal': 'hipertrofia',  # Siempre hipertrofia para enfoque
            'weight': 1.8
        })
        queries.append({
            'text': f'entrenamiento {mapped_area} frecuencia semanal volumen máximo',
            'category': 'training_knowledge',
            'goal': 'hipertrofia',
            'weight': 1.5
        })
        logger.info(f"🎯 Añadidas queries RAG para enfoque en: {mapped_area}")
    
    # 🔟 QUERY PARA RESTRICCIONES DIETÉTICAS (si hay restricciones específicas)
    restricciones = datos.get('restricciones', '') or datos.get('restricciones_dieta', '')
    if restricciones and restricciones.lower() != 'ninguna' and len(restricciones) > 5:
        restricciones_lower = restricciones.lower()
        
        if 'vegetariano' in restricciones_lower or 'vegetariana' in restricciones_lower:
            queries.append({
                'text': 'dieta vegetariana fitness proteínas completas combinaciones',
                'category': 'nutrition_knowledge',
                'goal': nutrition_goal_rag,
                'weight': 1.8
            })
            logger.info("🌱 Añadida query RAG para dieta vegetariana")
        
        if 'vegano' in restricciones_lower or 'vegana' in restricciones_lower:
            queries.append({
                'text': 'dieta vegana fitness proteínas completas B12 creatina',
                'category': 'nutrition_knowledge',
                'goal': nutrition_goal_rag,
                'weight': 1.8
            })
            logger.info("🌿 Añadida query RAG para dieta vegana")
        
        if 'halal' in restricciones_lower:
            queries.append({
                'text': 'dieta halal fitness proteínas permitidas nutrición deportiva',
                'category': 'nutrition_knowledge',
                'goal': nutrition_goal_rag,
                'weight': 1.8
            })
            logger.info("🕌 Añadida query RAG para dieta halal")
    
    # ═══════════════════════════════════════════════════════
    # EJECUTAR QUERIES RAG EN PARALELO (OPTIMIZACIÓN)
    # ═══════════════════════════════════════════════════════
    
    # Contador global para tokens de embeddings (para calcular costo)
    embedding_tokens_total = [0]  # Usar lista para modificar desde función anidada
    
    async def execute_query(query_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ejecuta una query RAG individual"""
        try:
            # Generar embedding de la query
            query_embedding_response = await client.embeddings.create(
                model="text-embedding-3-small",
                input=query_data['text']
            )
            
            # Obtener tokens reales de la respuesta (si está disponible)
            if hasattr(query_embedding_response, 'usage') and query_embedding_response.usage:
                tokens = getattr(query_embedding_response.usage, 'total_tokens', 0)
                embedding_tokens_total[0] += tokens
            
            query_embedding = query_embedding_response.data[0].embedding
            
            if not query_embedding:
                logger.warning(f"⚠️ No se pudo generar embedding para query: {query_data['text'][:50]}")
                return []
            
            # Buscar en RAG con filtros (reducido para evitar exceso de tokens)
            results = KnowledgeStore.search(
                query_embedding=query_embedding,
                k=1,  # Top 1 documento por query (reducido de 2 para optimizar tokens)
                language='es',
                category=query_data.get('category')
            )
            
            # Añadir peso a los resultados
            for result in results:
                result['query_weight'] = query_data.get('weight', 1.0)
            
            logger.info(f"✅ Query RAG: '{query_data['text'][:40]}...' → {len(results)} docs")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en query RAG: {e}")
            return []
    
    # Ejecutar todas las queries en paralelo para reducir latencia
    logger.info(f"🚀 Ejecutando {len(queries)} queries RAG en paralelo...")
    embedding_tokens_total[0] = 0  # Resetear contador
    query_tasks = [execute_query(query_data) for query_data in queries]
    query_results = await asyncio.gather(*query_tasks, return_exceptions=True)
    
    # Calcular costo de embeddings (text-embedding-3-small: $0.02 por 1M tokens)
    if embedding_tokens_total[0] > 0:
        embedding_cost = (embedding_tokens_total[0] / 1_000_000) * 0.02
        logger.info(f"📊 Embeddings RAG: {embedding_tokens_total[0]} tokens (costo: ${embedding_cost:.6f})")
    else:
        # Fallback: estimación conservadora si no se pudieron contar tokens
        estimated_tokens = len(queries) * 15  # ~15 tokens por query promedio
        embedding_cost = (estimated_tokens / 1_000_000) * 0.02
        logger.info(f"📊 Embeddings RAG: ~{estimated_tokens} tokens estimados (costo: ${embedding_cost:.6f})")
    
    # Consolidar resultados
    all_results = []
    for results in query_results:
        if isinstance(results, Exception):
            logger.error(f"❌ Error en query: {results}")
            continue
        if isinstance(results, list):
            all_results.extend(results)
    
    # ═══════════════════════════════════════════════════════
    # FORMATEAR CONTEXTO PARA EL PROMPT
    # ═══════════════════════════════════════════════════════
    
    if not all_results:
        logger.warning("⚠️ No se recuperaron documentos del RAG, continuando sin contexto")
        return ""
    
    # Ordenar por similitud (ya vienen ordenados) y peso
    all_results.sort(key=lambda x: x.get('similarity', 0) * x.get('query_weight', 1.0), reverse=True)
    
    # Tomar top 6 documentos únicos (optimizado: balance entre contexto científico y costo)
    unique_docs = []
    seen_titles = set()
    
    for doc in all_results:
        title = doc.get('title', '')
        if title not in seen_titles:
            unique_docs.append(doc)
            seen_titles.add(title)
        
        if len(unique_docs) >= 6:  # Aumentado a 6 documentos para mejor contexto científico
            break
    
    # Formatear contexto
    context_parts = []
    context_parts.append("═" * 80)
    context_parts.append("📚 CONTEXTO CIENTÍFICO DE LA BASE DE CONOCIMIENTO")
    context_parts.append("═" * 80)
    context_parts.append("")
    context_parts.append("⚠️ INSTRUCCIÓN CRÍTICA: Usa la siguiente información científica respaldada por")
    context_parts.append("estudios peer-reviewed para generar el plan. NO ignores este contexto.")
    context_parts.append("")
    
    for i, doc in enumerate(unique_docs, 1):
        title = doc.get('title', 'Sin título')
        content = doc.get('content', '')
        source = doc.get('source', '')
        similarity = doc.get('similarity', 0)
        
        # Limitar contenido a 1000 caracteres por documento para optimizar tokens
        # Priorizar el inicio del contenido que suele ser más relevante
        content_limited = content[:1000] + "..." if len(content) > 1000 else content
        
        context_parts.append(f"📄 DOCUMENTO {i}: {title}")
        context_parts.append(f"   Relevancia: {similarity:.3f}")
        context_parts.append(f"   Fuente: {source}")
        context_parts.append(f"   Contenido:")
        context_parts.append(f"   {content_limited}")
        context_parts.append("")
    
    context_parts.append("═" * 80)
    context_parts.append("✅ Fin del contexto científico - ÚSALO para generar el plan")
    context_parts.append("═" * 80)
    context_parts.append("")
    
    final_context = "\n".join(context_parts)
    
    logger.info(f"✅ Contexto RAG generado: {len(unique_docs)} documentos únicos (objetivo: 6)")
    
    return final_context


async def generar_plan_safe(user_data, user_id):
    """
    Genera plan con GPT - SIN fallback silencioso
    🔧 FIX: Ya no devuelve template genérico. Debe propagar excepciones.
    """
    
    logger.info(f"🤖 Intentando generar plan con GPT para usuario {user_id}")
    
    try:
        plan_data = await generar_plan_personalizado(user_data)
        
        # 🔧 FIX: Validar que GPT devolvió dieta válida (no template genérico)
        if not plan_data or 'dieta' not in plan_data:
            logger.error(f"❌ GPT no devolvió dieta válida")
            raise ValueError("GPT no devolvió dieta válida")
        
        # 🔧 FIX: Detectar si GPT devolvió template genérico por error
        dieta = plan_data.get('dieta', {})
        comidas = dieta.get('comidas', [])
        
        if not comidas or len(comidas) == 0:
            logger.error(f"❌ GPT devolvió dieta sin comidas")
            raise ValueError("GPT devolvió dieta sin comidas")
        
        # Verificar que los alimentos no sean exactamente del template genérico
        # Template genérico siempre tiene: "300ml leche semidesnatada - 150kcal"
        primer_alimento = None
        for comida in comidas:
            alimentos = comida.get('alimentos', [])
            if alimentos and len(alimentos) > 0:
                primer_alimento = alimentos[0]
                break
        
        if primer_alimento and isinstance(primer_alimento, str):
            # Si el primer alimento es exactamente el del template, algo falló
            if "300ml leche semidesnatada - 150kcal" in primer_alimento:
                logger.warning(f"⚠️ Posible template genérico detectado en respuesta GPT")
                logger.warning(f"   Primer alimento: {primer_alimento}")
                # NO lanzar error aquí, solo loguear - puede ser coincidencia
        
        logger.info(f"✅ Plan GPT generado exitosamente ({len(comidas)} comidas)")
        return plan_data
        
    except (asyncio.CancelledError, asyncio.TimeoutError, HTTPException) as e:
        # 🔧 FIX: NO usar fallback silencioso - propagar excepción
        logger.error(f"❌ GPT falló ({type(e).__name__}): {e}")
        raise  # Propagar excepción para manejo en capa superior
        
    except Exception as e:
        # 🔧 FIX: NO usar fallback silencioso - propagar excepción
        logger.error(f"❌ Error inesperado en GPT: {e}")
        logger.exception(e)
        raise  # Propagar excepción para manejo en capa superior


async def generar_plan_personalizado(datos):
    # ═══════════════════════════════════════════════════════
    # 🔥 NUEVO: RECUPERAR CONTEXTO RAG ANTES DE CALCULAR
    # ═══════════════════════════════════════════════════════
    logger.info("=" * 80)
    logger.info("🔍 PASO 1: RECUPERANDO CONTEXTO CIENTÍFICO DEL RAG")
    logger.info("=" * 80)
    
    rag_context = await get_rag_context_for_plan(datos)
    
    if rag_context:
        logger.info(f"✅ Contexto RAG recuperado ({len(rag_context)} caracteres)")
        # El costo de embeddings ya se loguea dentro de get_rag_context_for_plan
    else:
        logger.warning("⚠️ No se recuperó contexto RAG - continuando sin él")
    
    # ═══════════════════════════════════════════════════════
    # CALCULAR NUTRICIÓN CIENTÍFICAMENTE CON TMB/TDEE
    # ═══════════════════════════════════════════════════════
    
    nutrition_goal = datos.get('nutrition_goal', 'mantenimiento')
    
    # 🔧 FIX: Si el usuario especificó calorías objetivo específicas, usarlas directamente
    target_calories_override = datos.get('target_calories_override')
    
    logger.info("=" * 70)
    logger.info("🧮 PASO 2: CALCULANDO PLAN NUTRICIONAL CIENTÍFICO")
    logger.info("=" * 70)
    logger.info(f"📊 Objetivo nutricional: {nutrition_goal}")
    if target_calories_override:
        logger.info(f"🎯 Calorías objetivo especificadas: {target_calories_override} kcal")
    
    # Calcular plan nutricional con función científica (TMB + TDEE)
    nutrition_plan = get_complete_nutrition_plan(datos, nutrition_goal)
    
    tmb = nutrition_plan['tmb']
    tdee = nutrition_plan['tdee']
    
    # 🔧 FIX: Usar calorías especificadas si están presentes, sino calcular desde objetivo
    if target_calories_override:
        kcal_objetivo = int(target_calories_override)
        logger.info(f"✅ Usando calorías objetivo especificadas: {kcal_objetivo} kcal")
        # Recalcular macros desde las calorías objetivo especificadas
        from app.utils.nutrition_calculator import calculate_macros_distribution, parse_peso
        peso_kg = parse_peso(datos.get('peso', 75))
        macros = calculate_macros_distribution(kcal_objetivo, peso_kg, nutrition_goal)
        logger.info(f"📊 Macros recalculados desde calorías objetivo: P={macros['proteina']}g, C={macros['carbohidratos']}g, G={macros['grasas']}g")
    else:
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
    training_days_raw = datos.get('training_days', ['lunes', 'martes', 'jueves', 'viernes'])
    # Normalizar días: capitalizar primera letra (Lunes, Martes, etc.)
    training_days = [day.capitalize() if day else day for day in training_days_raw] if training_days_raw else ['Lunes', 'Martes', 'Jueves', 'Viernes']
    
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
⚠️⚠️⚠️ REGLA ABSOLUTA: AJUSTE DE CANTIDADES ⚠️⚠️⚠️
La dieta DEBE sumar EXACTAMENTE {kcal_objetivo} kcal/día total.
NO uses cantidades fijas. AJUSTA las cantidades de cada alimento para que:
- Las 5 comidas sumen EXACTAMENTE {kcal_objetivo} kcal
- Los macros totales se aproximen a: P={macros['proteina']}g, C={macros['carbohidratos']}g, G={macros['grasas']}g

CÓMO AJUSTAR LAS CANTIDADES:
1. Calcula las calorías objetivo por comida (aprox. {kcal_objetivo // 5} kcal por comida)
2. AJUSTA las cantidades de cada alimento para que cada comida sume sus kcal objetivo
3. Si la suma total es mayor a {kcal_objetivo}, REDUCE las cantidades proporcionalmente
4. Si la suma total es menor a {kcal_objetivo}, AUMENTA las cantidades proporcionalmente
5. Verifica que la suma de las 5 comidas = {kcal_objetivo} kcal EXACTAMENTE

EJEMPLO DE AJUSTE:
- Si necesitas 2216 kcal total y una comida tiene 600 kcal, AJUSTA a ~443 kcal (2216/5)
- Si un alimento aporta 100 kcal pero necesitas 80 kcal, reduce la cantidad: 80g en lugar de 100g
- Si un alimento aporta 50 kcal pero necesitas 70 kcal, aumenta la cantidad: 140g en lugar de 100g

DISTRIBUCIÓN DE CALORÍAS POR COMIDA:
- Desayuno: ~{int(kcal_objetivo * 0.20)} kcal (20% del total)
- Media mañana: ~{int(kcal_objetivo * 0.15)} kcal (15% del total)
- Comida: ~{int(kcal_objetivo * 0.30)} kcal (30% del total)
- Merienda: ~{int(kcal_objetivo * 0.15)} kcal (15% del total)
- Cena: ~{int(kcal_objetivo * 0.20)} kcal (20% del total)
- TOTAL: {kcal_objetivo} kcal EXACTAMENTE

Ahora, crea una dieta estructurada en 5 comidas al día. AJUSTA las cantidades de cada alimento para que cuadren con las calorías objetivo. Usa los siguientes alimentos de preferencia:
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

    # ═══════════════════════════════════════════════════════
    # 🔥 MODIFICACIÓN PRINCIPAL: INYECTAR CONTEXTO RAG
    # ═══════════════════════════════════════════════════════
    
    prompt = f"""
Eres un entrenador profesional de fuerza y nutrición. Genera un plan completo y personalizado.

{rag_context}

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

⚠️ IMPORTANTE: Si hay una lesión especificada arriba, DEBES:
- EVITAR completamente ejercicios que afecten esa parte del cuerpo
- Generar ejercicios alternativos seguros
- Adaptar el volumen e intensidad según la severidad de la lesión

🎯 ENFOQUE ESPECIAL: {f"- ÁREA DE ENFOQUE: {datos.get('focus_area', 'ninguna')} - DEBES darle PRIORIDAD y MAYOR VOLUMEN a esta zona" if datos.get('focus_area') else "- No hay área de enfoque específica"}
{f"- AUMENTAR FRECUENCIA: {'Sí' if datos.get('increase_frequency') else 'No'} - Incluir esta zona en más días de entrenamiento" if datos.get('focus_area') else ""}
{f"- CAMBIO DE VOLUMEN: {datos.get('volume_change', 'ninguno')} - Ajustar series y repeticiones según este cambio" if datos.get('focus_area') else ""}
{f"⚠️ CRÍTICO: La rutina DEBE estar ENFOCADA en {datos.get('focus_area')} con MAYOR VOLUMEN, MÁS EJERCICIOS y MÁS FRECUENCIA para esta zona específica" if datos.get('focus_area') else ""}

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
- Equipamiento disponible: {', '.join(datos['materiales']) if isinstance(datos['materiales'], list) else datos['materiales']}

{f"""
⚠️⚠️⚠️ RESTRICCIÓN DE EQUIPAMIENTO CRÍTICA ⚠️⚠️⚠️
🚫 EQUIPAMIENTO NO DISPONIBLE: {datos.get('missing_equipment', 'ninguno')}
✅ EQUIPAMIENTO DISPONIBLE: {datos.get('available_equipment', 'ninguno')}

REGLAS OBLIGATORIAS:
1. ❌ PROHIBIDO: NO incluir NINGÚN ejercicio que requiera {datos.get('missing_equipment')}
2. ✅ OBLIGATORIO: Usar SOLO ejercicios con {datos.get('available_equipment', 'equipamiento disponible')}
3. ✅ OBLIGATORIO: Generar una rutina COMPLETA nueva que NO dependa de {datos.get('missing_equipment')}
4. ✅ OBLIGATORIO: Cada grupo muscular debe tener alternativas usando {datos.get('available_equipment', 'equipamiento disponible')}

EJERCICIOS A EVITAR ABSOLUTAMENTE:
{datos.get('affected_exercises', f'TODOS los ejercicios que mencionen o requieran {datos.get("missing_equipment")} en su nombre o ejecución')}

EJEMPLOS ESPECÍFICOS DE SUSTITUCIÓN:
- Si falta "barras olímpicas":
  ❌ PROHIBIDO: Dominadas, Remo con barra, Press de banca con barra, Curl con barra, Press militar con barra, Peso muerto con barra
  ✅ USAR: Remo con mancuernas, Flexiones, Remo invertido, Curl con mancuernas, Press con mancuernas, Peso muerto con mancuernas, Remo con bandas

- Si falta "banco de press":
  ❌ PROHIBIDO: Press de banca, Press inclinado, Press declinado, Press banca con barra, Press banca con mancuernas
  ✅ USAR: Flexiones, Flexiones inclinadas, Flexiones con pies elevados, Press con mancuernas en suelo, Dips

- Si falta "mancuernas":
  ❌ PROHIBIDO: Cualquier ejercicio que mencione "mancuernas" o "dumbbells"
  ✅ USAR: Ejercicios con peso corporal, bandas elásticas, barras (si están disponibles), kettlebells (si están disponibles)

- Si falta "rack de sentadillas":
  ❌ PROHIBIDO: Sentadillas con barra, Squat con barra, Sentadillas frontales con barra
  ✅ USAR: Sentadillas con peso corporal, Sentadillas con mancuernas, Sentadillas con kettlebell, Zancadas, Prensa de piernas (si hay máquina)

VALIDACIÓN ANTES DE GENERAR LA RUTINA:
- Revisa CADA ejercicio generado y verifica que NO requiera {datos.get('missing_equipment')}
- Si un ejercicio requiere {datos.get('missing_equipment')}, REEMPLÁZALO inmediatamente por una alternativa
- Asegúrate de que TODOS los ejercicios usen {datos.get('available_equipment', 'equipamiento disponible')}
""" if datos.get('missing_equipment') else ""}

{f"""
⚠️⚠️⚠️ SUSTITUCIÓN DE EJERCICIO ESPECÍFICO (CRÍTICO) ⚠️⚠️⚠️
🔄 EJERCICIO A REEMPLAZAR: {datos.get('exercise_to_replace', 'ninguno')}
📝 RAZÓN: {datos.get('replacement_reason', 'no especificada')}
🎯 GRUPO MUSCULAR: {datos.get('target_muscles', 'no especificado')}
🏋️ EQUIPAMIENTO DISPONIBLE: {datos.get('equipment_available', 'cualquiera')}

REGLAS OBLIGATORIAS:
1. ❌ PROHIBIDO: NO incluir NINGÚN ejercicio que se llame "{datos.get('exercise_to_replace')}" o variaciones similares
2. ✅ OBLIGATORIO: Sustituir "{datos.get('exercise_to_replace')}" por un ejercicio alternativo para {datos.get('target_muscles', 'el mismo grupo muscular')}
3. ✅ OBLIGATORIO: El ejercicio alternativo debe trabajar el mismo grupo muscular ({datos.get('target_muscles', 'no especificado')})
4. ✅ OBLIGATORIO: Considerar el equipamiento disponible: {datos.get('equipment_available', 'cualquiera')}
5. ✅ OBLIGATORIO: Mantener la estructura y equilibrio del resto de la rutina
6. ✅ OBLIGATORIO: Si el ejercicio original tenía series/reps específicas, intentar mantener similares en el alternativo

EJEMPLOS DE SUSTITUCIÓN POR GRUPO MUSCULAR:
- Si se reemplaza "Press de banca" (pecho):
  ❌ PROHIBIDO: Press de banca, Bench press, Press banca
  ✅ USAR: Press con mancuernas, Flexiones, Press inclinado con mancuernas, Aperturas con mancuernas

- Si se reemplaza "Sentadillas" (piernas):
  ❌ PROHIBIDO: Sentadillas, Squat, Sentadillas con barra
  ✅ USAR: Prensa de piernas, Zancadas, Sentadillas con mancuernas, Extensión de cuádriceps

- Si se reemplaza "Dominadas" (espalda):
  ❌ PROHIBIDO: Dominadas, Pull-ups, Chin-ups
  ✅ USAR: Jalones en polea, Remo con barra, Remo con mancuerna, Remo invertido

- Si se reemplaza "Peso muerto" (espalda/piernas):
  ❌ PROHIBIDO: Peso muerto, Deadlift, Peso muerto con barra
  ✅ USAR: Peso muerto rumano, Remo con barra, Zancadas, Hip thrust

VALIDACIÓN ANTES DE GENERAR LA RUTINA:
- Revisa CADA ejercicio generado y verifica que NO sea "{datos.get('exercise_to_replace')}" o variaciones
- Si generas "{datos.get('exercise_to_replace')}", REEMPLÁZALO inmediatamente por una alternativa apropiada
- Asegúrate de que el ejercicio alternativo trabaje {datos.get('target_muscles', 'el mismo grupo muscular')}
- Mantén el equilibrio y estructura del resto de la rutina intacta
""" if datos.get('exercise_to_replace') else ""}

{f"""
⚠️⚠️⚠️ CRÍTICO: Si incluyes CUALQUIER ejercicio que requiera {datos.get('missing_equipment')}, la rutina será INVÁLIDA ⚠️⚠️⚠️
""" if datos.get('missing_equipment') else ""}

═══════════════════════════════════════════════
RESTRICCIONES:
═══════════════════════════════════════════════
- Alergias: {datos.get('alergias', 'ninguna')}
- Restricciones dietéticas: {datos.get('restricciones', 'ninguna')}
- Idioma: {idioma}

{texto_dieta}
{texto_rutina}

INSTRUCCIONES CRÍTICAS:

{f"""
⚠️⚠️⚠️ VALIDACIÓN FINAL DE EQUIPAMIENTO ⚠️⚠️⚠️
ANTES de generar CADA ejercicio de la rutina, verifica:
1. ¿Este ejercicio requiere {datos.get('missing_equipment')}? → Si SÍ, NO LO INCLUYAS
2. ¿Este ejercicio puede hacerse con {datos.get('available_equipment')}? → Si NO, CÁMBIALO
3. ¿El nombre del ejercicio menciona {datos.get('missing_equipment')}? → Si SÍ, SUSTITÚYELO

REVISA LA RUTINA COMPLETA antes de devolverla y asegúrate de que:
- NINGÚN ejercicio requiera {datos.get('missing_equipment')}
- TODOS los ejercicios usen {datos.get('available_equipment')} o equipamiento compatible
- La rutina sea completa y funcional SIN {datos.get('missing_equipment')}

""" if datos.get('missing_equipment') else ""}

1. RUTINA DE ENTRENAMIENTO:
   - Diseña la rutina para EXACTAMENTE {training_frequency} días
   - ⚠️⚠️⚠️ DÍAS ESPECÍFICOS OBLIGATORIOS: {', '.join(training_days)} ⚠️⚠️⚠️
   - ⚠️ CRÍTICO: El array "dias" DEBE tener EXACTAMENTE {len(training_days)} elementos
   - ⚠️ CRÍTICO: El campo "dia" de cada objeto DEBE ser EXACTAMENTE uno de estos (en este orden): {', '.join(training_days)}
   - ⚠️ CRÍTICO: NO uses días que no estén en esta lista: {', '.join(training_days)}
   - Cada día debe tener su nombre específico con el día de la semana (ej: "Lunes - Pecho y Tríceps", "Martes - Espalda y Bíceps")
   - El orden de los días en el array DEBE seguir: {', '.join(training_days)}
   - Ajusta los ejercicios y volumen según el objetivo de gym: {gym_goal}
     * Si es "ganar_musculo": Hipertrofia - 8-12 reps, 3-4 series, descansos 60-90s
     * Si es "ganar_fuerza": Fuerza - 4-6 reps, 4-5 series, descansos 2-3min
   - Considera el equipamiento disponible: {', '.join(datos['materiales']) if isinstance(datos['materiales'], list) else datos['materiales']}
   {f"- ⚠️ CRÍTICO: NO uses {datos.get('missing_equipment')} - Usa SOLO {datos.get('available_equipment')}" if datos.get('missing_equipment') else ""}
   - Cada día debe tener 4-6 ejercicios diferentes
   
   {f"""
   ⚠️⚠️⚠️ INSTRUCCIÓN CRÍTICA DE ENFOQUE ⚠️⚠️⚠️
   El usuario quiere ENFOCAR la rutina en: {datos.get('focus_area', 'ninguna')}
   
   DEBES:
   1. PRIORIZAR ejercicios de {datos.get('focus_area')} en MÁS días de la semana
   2. Si hay {training_frequency} días, INCLUYE {datos.get('focus_area')} en AL MENOS {training_frequency - 1} días
   3. Cada día que incluya {datos.get('focus_area')} debe tener MÍNIMO 2 ejercicios específicos para esa zona
   4. {"INCREMENTA la frecuencia: Incluye esta zona en más días de lo normal" if datos.get('increase_frequency') else "Mantén frecuencia normal pero aumenta volumen"}
   5. Cambio de volumen: {datos.get('volume_change', 'ninguno')} - 
      * Si es "aumento_significativo": 5-6 series por ejercicio, más ejercicios totales
      * Si es "aumento_moderado": 4-5 series por ejercicio
      * Si es "ligero_aumento": 3-4 series por ejercicio
   
   EJEMPLOS:
   - Si el enfoque es "brazos" y hay 4 días: Lunes (Brazos y Pecho), Martes (Brazos y Espalda), Jueves (Brazos y Piernas), Viernes (Solo Brazos)
   - Si el enfoque es "piernas" y hay 4 días: Lunes (Piernas), Martes (Piernas y Espalda), Jueves (Piernas), Viernes (Piernas y Brazos)
   - Cada día con enfoque debe tener MÍNIMO 2 ejercicios de la zona enfocada
   
   ⚠️ CRÍTICO: La rutina DEBE reflejar claramente el enfoque en {datos.get('focus_area')} con más frecuencia y volumen que otras zonas
   """ if datos.get('focus_area') else ""}

2. PLAN NUTRICIONAL:
   ⚠️⚠️⚠️ CRÍTICO: AJUSTE DE CANTIDADES SEGÚN CALORÍAS OBJETIVO ⚠️⚠️⚠️
   
   - Calorías objetivo ({nutrition_goal}): {kcal_objetivo} kcal/día EXACTAS
     * Si "volumen": Superávit de ~300 kcal → {kcal_objetivo} kcal/día
     * Si "definicion": Déficit de ~300 kcal → {kcal_objetivo} kcal/día
     * Si "mantenimiento": Calorías de mantenimiento → {kcal_objetivo} kcal/día
   
   - REGLA ABSOLUTA: Las 5 comidas DEBEN sumar EXACTAMENTE {kcal_objetivo} kcal
     * NO uses cantidades fijas de alimentos
     * AJUSTA las cantidades (gramos/ml) de cada alimento para cuadrar con las calorías objetivo
     * Calcula: calorías por comida = {kcal_objetivo // 5} kcal aprox. por comida
     * Distribución sugerida: Desayuno 20%, Media mañana 15%, Comida 30%, Merienda 15%, Cena 20%
     * Verifica que la suma total = {kcal_objetivo} kcal EXACTAMENTE antes de devolver
   
   - Distribución de macros objetivo:
     * Proteína: {macros['proteina']}g/día ({macros['proteina'] * 4} kcal)
     * Carbohidratos: {macros['carbohidratos']}g/día ({macros['carbohidratos'] * 4} kcal)
     * Grasas: {macros['grasas']}g/día ({macros['grasas'] * 9} kcal)
     * AJUSTA las cantidades de alimentos para aproximar estos macros
   
   - Respetar restricciones: {datos.get('restricciones', 'ninguna')}
   - Evitar alergias: {datos.get('alergias', 'ninguna')}
   - Generar exactamente 5 comidas al día

3. ⚠️⚠️⚠️ USO OBLIGATORIO DEL CONTEXTO CIENTÍFICO ⚠️⚠️⚠️
   - DEBES usar la información científica proporcionada en la sección "CONTEXTO CIENTÍFICO"
   - Los estudios citados son peer-reviewed y respaldados por investigación real
   - Aplica las recomendaciones de volumen, frecuencia, macros según los documentos
   - NO ignores el contexto científico - es la base de tu respuesta

4. FORMATO DE RESPUESTA:
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
    logger.info("=" * 80)
    logger.info(f"🔄 PASO 3: GENERANDO PLAN CON GPT-4o")
    logger.info(f"📦 Modelo: {MODEL}")
    logger.info(f"📚 RAG activo: {len(rag_context) > 0 if rag_context else False}")
    logger.info("=" * 80)
    
    # ═══════════════════════════════════════════════════════
    # 🔄 RETRY LOGIC CON EXPONENTIAL BACKOFF
    # ═══════════════════════════════════════════════════════
    MAX_RETRIES = 3
    BASE_DELAY = 2  # Segundos base para exponential backoff
    
    response = None
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"🔄 Intento {attempt + 1}/{MAX_RETRIES} de generación de plan")
            
            response = await client.chat.completions.create(
                model=MODEL,  # ✅ GPT-4o con sistema RAG completo
                messages=[{"role": "user", "content": prompt}],
                temperature=0.85,
                max_tokens=2500,  # 🛡️ Limitar tokens para evitar excesos
                timeout=120.0  # 🛡️ Timeout aumentado a 2 minutos
            )
            
            # ✅ Éxito: salir del loop de retry
            logger.info(f"✅ Plan generado exitosamente en intento {attempt + 1}")
            break
            
        except RateLimitError as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                # Exponential backoff: 2s, 4s, 8s
                delay = BASE_DELAY * (2 ** attempt)
                logger.warning(f"⚠️ Rate limit alcanzado (intento {attempt + 1}/{MAX_RETRIES}). Esperando {delay}s antes de reintentar...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"❌ Rate limit después de {MAX_RETRIES} intentos")
                raise HTTPException(
                    status_code=429,
                    detail="El servicio está temporalmente saturado. Por favor, espera unos segundos e intenta de nuevo."
                )
                
        except APIError as e:
            last_error = e
            # Errores de API que pueden ser temporales (500, 502, 503)
            if attempt < MAX_RETRIES - 1 and hasattr(e, 'status_code') and e.status_code in [500, 502, 503]:
                delay = BASE_DELAY * (2 ** attempt)
                logger.warning(f"⚠️ Error de API {e.status_code} (intento {attempt + 1}/{MAX_RETRIES}). Esperando {delay}s antes de reintentar...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"❌ Error de API no recuperable: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error temporal del servicio de IA. Por favor, intenta de nuevo en unos momentos."
                )
                
        except asyncio.TimeoutError as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)
                logger.warning(f"⚠️ Timeout en generación (intento {attempt + 1}/{MAX_RETRIES}). Esperando {delay}s antes de reintentar...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"❌ Timeout después de {MAX_RETRIES} intentos")
                raise HTTPException(
                    status_code=504,
                    detail="La generación del plan tardó demasiado. Intenta de nuevo."
                )
                
        except Exception as e:
            # Otros errores no esperados
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)
                logger.warning(f"⚠️ Error inesperado: {type(e).__name__} (intento {attempt + 1}/{MAX_RETRIES}). Esperando {delay}s antes de reintentar...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"❌ Error no recuperable después de {MAX_RETRIES} intentos: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error al generar plan: {str(e)}"
                )
    
    # Si llegamos aquí sin response, hubo un error no manejado
    if response is None:
        logger.error(f"❌ No se pudo generar plan después de {MAX_RETRIES} intentos. Último error: {last_error}")
        raise HTTPException(
            status_code=500,
            detail="No se pudo generar el plan después de varios intentos. Por favor, intenta de nuevo más tarde."
        )
    
    # 📊 Logging de tokens usados y costo estimado
        if hasattr(response, 'usage') and response.usage:
            tokens_used = response.usage.total_tokens
            prompt_tokens = response.usage.prompt_tokens if hasattr(response.usage, 'prompt_tokens') else 0
            completion_tokens = response.usage.completion_tokens if hasattr(response.usage, 'completion_tokens') else 0
            
            # Costo estimado GPT-4o (precios aproximados de OpenAI)
            # Input: $0.005/1K tokens, Output: $0.015/1K tokens
            gpt_cost = (prompt_tokens / 1000 * 0.005) + (completion_tokens / 1000 * 0.015)
            
            # Costo de embeddings RAG (text-embedding-3-small: $0.02 por 1M tokens)
            # Estimación conservadora: ~5-10 queries × ~15 tokens/query = ~75-150 tokens
            # Costo: (150 / 1,000,000) * $0.02 = $0.000003 (muy bajo, ~0.006% del costo total)
            # Nota: El costo real se calcula en get_rag_context_for_plan y se loguea allí
            # Aquí usamos una estimación para el cálculo total
            estimated_embedding_tokens = 150  # ~10 queries × 15 tokens promedio
            embedding_cost = (estimated_embedding_tokens / 1_000_000) * 0.02
            total_cost = gpt_cost + embedding_cost
            
            logger.info(f"📊 Tokens GPT: {tokens_used} total ({prompt_tokens} prompt + {completion_tokens} completion)")
            logger.info(f"💰 Costo GPT-4o: ${gpt_cost:.4f}")
            logger.info(f"💰 Costo embeddings RAG: ~${embedding_cost:.6f} (ver logs de RAG para valor exacto)")
            logger.info(f"💰 Costo TOTAL estimado (GPT + RAG): ${total_cost:.4f}")
            
            if tokens_used > 3000:
                logger.warning(f"⚠️ Plan usando muchos tokens: {tokens_used} (costo GPT: ${gpt_cost:.4f}, total: ${total_cost:.4f})")
        
    contenido = response.choices[0].message.content
    logger.info(f"✅ Plan generado exitosamente con GPT-4o")
    print("Respuesta cruda de GPT:", contenido[:200] + "...")  # Solo mostrar primeros 200 chars

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
        'diferencia_mantenimiento': diferencia_mantenimiento,
        'rag_used': bool(rag_context)  # 🔥 NUEVO: Indicar si se usó RAG
    })
    
    logger.info("📦 Metadatos científicos añadidos a la dieta:")
    logger.info(f"   TMB: {tmb} kcal/día")
    logger.info(f"   TDEE: {tdee} kcal/día")
    logger.info(f"   Calorías objetivo: {kcal_objetivo} kcal/día")
    logger.info(f"   Método: Mifflin-St Jeor")
    logger.info(f"   RAG usado: {bool(rag_context)}")
    
    # ═══════════════════════════════════════════════════════
    # AÑADIR MACROS A NIVEL RAIZ DE LA DIETA (CRÍTICO)
    # ═══════════════════════════════════════════════════════
    # Los macros calculados científicamente deben estar en plan.dieta.macros
    # para que el frontend pueda acceder a ellos fácilmente
    data['dieta']['macros'] = {
        'proteina': macros['proteina'],
        'carbohidratos': macros['carbohidratos'],
        'grasas': macros['grasas'],
        'calorias': kcal_objetivo
    }
    
    logger.info(f"✅ Macros añadidos a plan.dieta.macros:")
    logger.info(f"   Proteína: {macros['proteina']}g")
    logger.info(f"   Carbohidratos: {macros['carbohidratos']}g")
    logger.info(f"   Grasas: {macros['grasas']}g")

    return {
        "rutina": data["rutina"],
        "dieta": data["dieta"],
        "motivacion": data["motivacion"]
    }


async def generar_comida_personalizada(datos: Dict[str, Any]) -> Dict[str, Any]:
    """
    Genera UNA comida específica personalizada con GPT
    - Respeta calorías objetivo de la comida
    - Respeta macros objetivo de la comida
    - Excluye alimentos no deseados
    """
    try:
        # Extraer parámetros de la comida específica
        meal_type = datos.get('meal_type', 'desayuno')
        meal_target_kcal = datos.get('meal_target_kcal', 0)
        meal_target_macros = datos.get('meal_target_macros', {})
        excluded_foods = datos.get('excluded_foods', [])
        
        # Obtener macros objetivo
        target_protein = meal_target_macros.get('proteinas', meal_target_macros.get('proteina', 0))
        target_carbs = meal_target_macros.get('carbohidratos', meal_target_macros.get('hidratos', meal_target_macros.get('carbohidratos', 0)))
        target_fats = meal_target_macros.get('grasas', 0)
        
        # Construir prompt para generar solo UNA comida
        prompt = f"""Eres un nutricionista experto. Tu tarea es generar UNA comida específica para un usuario.

TIPO DE COMIDA: {meal_type.upper()}

PARÁMETROS OBLIGATORIOS:
- Calorías objetivo: {meal_target_kcal} kcal EXACTAMENTE
- Proteínas objetivo: {target_protein}g
- Carbohidratos objetivo: {target_carbs}g
- Grasas objetivo: {target_fats}g

{f'''
⚠️⚠️⚠️ ALIMENTOS EXCLUIDOS (CRÍTICO) ⚠️⚠️⚠️
El usuario NO quiere estos alimentos en esta comida:
{', '.join(excluded_foods)}

⚠️⚠️⚠️ IMPORTANTE - SINÓNIMOS Y VARIANTES ⚠️⚠️⚠️
NO debes incluir NINGÚN alimento que sea el mismo o equivalente a los excluidos, incluso si se llama diferente.

REGLAS OBLIGATORIAS:
1. ❌ PROHIBIDO: NO incluir NINGÚN alimento que contenga: {', '.join(excluded_foods)}
2. ❌ PROHIBIDO: NO incluir NINGÚN alimento que sea equivalente o sinónimo de los excluidos
3. ✅ OBLIGATORIO: Usar alimentos completamente diferentes a los excluidos
4. ✅ OBLIGATORIO: Mantener las calorías objetivo EXACTAS ({meal_target_kcal} kcal)
5. ✅ OBLIGATORIO: Mantener los macros objetivo: P={target_protein}g, C={target_carbs}g, G={target_fats}g
6. ✅ OBLIGATORIO: Ajustar las cantidades de los alimentos para cuadrar con las calorías y macros

EJEMPLOS DE SUSTITUCIÓN:
- Si excluye "avena": usar quinoa, arroz integral, mijo, o trigo sarraceno en su lugar
- Si excluye "crema de cacahuete" o "mantequilla de cacahuete": usar mantequilla de almendras, tahini, o aguacate
- Si excluye "leche": usar leche de almendras, leche de avena, leche de soja, o yogur natural
- Si excluye "pollo": usar pavo, ternera magra, pescado blanco, o tofu
- Ajusta las cantidades para mantener las mismas calorías y macros

VALIDACIÓN FINAL:
- Revisa CADA alimento generado y verifica que NO contenga ningún alimento excluido O SUS SINÓNIMOS
- Si un alimento contiene un excluido o su sinónimo, REEMPLÁZALO inmediatamente por una alternativa
- Asegúrate de que la suma total = {meal_target_kcal} kcal EXACTAMENTE
- Asegúrate de que los macros se aproximen a P={target_protein}g, C={target_carbs}g, G={target_fats}g

⚠️⚠️⚠️ CRÍTICO: Si incluyes CUALQUIER alimento excluido O SUS SINÓNIMOS, la comida será INVÁLIDA ⚠️⚠️⚠️
''' if excluded_foods else ''}

Formato obligatorio de salida en JSON:

{{
  "nombre": "{meal_type.capitalize()}",
  "kcal": {meal_target_kcal},
  "macros": {{
    "proteinas": {target_protein},
    "carbohidratos": {target_carbs},
    "grasas": {target_fats}
  }},
  "alimentos": [
    "cantidad alimento1 - kcal",
    "cantidad alimento2 - kcal",
    "cantidad alimento3 - kcal"
  ],
  "alternativas": []
}}

IMPORTANTE:
- La suma de calorías de todos los alimentos debe ser EXACTAMENTE {meal_target_kcal} kcal
- Los macros deben aproximarse a P={target_protein}g, C={target_carbs}g, G={target_fats}g
- NO incluyas NINGÚN alimento de la lista de excluidos: {', '.join(excluded_foods) if excluded_foods else 'ninguno'}
- Usa alimentos variados y nutricionalmente completos
- Ajusta las cantidades para cuadrar con las calorías objetivo

Genera SOLO esta comida en formato JSON válido."""

        # Llamar a GPT
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Eres un nutricionista experto especializado en generar comidas personalizadas con macros precisos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        contenido = response.choices[0].message.content
        
        if not contenido:
            logger.error("❌ GPT no devolvió contenido para comida personalizada")
            return None
        
        # Parsear JSON
        try:
            comida_json = json.loads(contenido)
            logger.info(f"✅ Comida generada por GPT: {comida_json.get('nombre', '')}")
            return comida_json
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parseando JSON de GPT: {e}")
            logger.error(f"   Contenido recibido: {contenido[:200]}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error generando comida personalizada: {e}", exc_info=True)
        return None