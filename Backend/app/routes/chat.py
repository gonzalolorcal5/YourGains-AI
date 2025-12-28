# app/routes/chat.py
from fastapi import APIRouter, Header, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
import os
import logging
import json
from openai import OpenAI
import asyncio

from app.database import get_db
from app.models import Usuario
from app.utils.gpt import get_rag_context_for_chat

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class ChatRequestBody(BaseModel):
    message: str

class ChatResponse(BaseModel):
    answer: str
    chat_uses_free_restantes: Optional[int] = None

# Cliente OpenAI
api_key = os.getenv("OPENAI_API_KEY", "").strip()
client = None
if api_key:
    client = OpenAI(api_key=api_key)

def get_fitness_prompt():
    """Prompt base para el asistente de fitness"""
    return """Eres YourGains AI, un entrenador personal y nutricionista experto con más de 10 años de experiencia. 

Tu personalidad:
- Profesional pero cercano y motivador
- Basas tus respuestas en evidencia científica
- Adaptas las recomendaciones al usuario específico
- Siempre priorizas la seguridad y la progresión gradual
- Eres directo pero empático

Áreas de expertise:
- Entrenamiento de fuerza y hipertrofia
- Nutrición deportiva y composición corporal
- Prevención de lesiones
- Periodización del entrenamiento
- Suplementación deportiva

Cuando respondas:
1. Sé específico y práctico
2. Incluye el "por qué" detrás de tus recomendaciones
3. Adapta las respuestas al nivel del usuario
4. Si detectas algo peligroso, recomienda consultar un profesional
5. Mantén un tono motivador pero realista

Responde en español y limita tus respuestas a 200 palabras máximo para mantener la conversación dinámica."""

async def call_openai_chat(message: str, user_email: str) -> str:
    """Llama a OpenAI con el contexto de fitness y RAG"""
    if not client:
        return "⚠️ Chat con IA temporalmente no disponible. Contacta con soporte."
    
    try:
        # 🔥 NUEVO: Obtener contexto RAG basado en el mensaje del usuario
        logger.info("🔍 Obteniendo contexto RAG para el chat...")
        rag_context = await get_rag_context_for_chat(message)
        
        # Construir prompt del sistema con contexto RAG
        system_prompt = get_fitness_prompt()
        if rag_context:
            system_prompt += "\n\n" + rag_context
            logger.info("✅ Contexto RAG añadido al prompt")
        else:
            logger.info("⚠️ No se obtuvo contexto RAG, continuando sin él")
        
        # Prompt del sistema + mensaje del usuario
        messages = [
            {
                "role": "system", 
                "content": system_prompt
            },
            {
                "role": "user", 
                "content": f"Usuario: {user_email}\nPregunta: {message}"
            }
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Más económico que gpt-4
            messages=messages,
            temperature=0.7,
            max_tokens=300,
            presence_penalty=0.1,
            frequency_penalty=0.1
        )
        
        answer = response.choices[0].message.content.strip()
        
        # Log para debugging
        logger.info(f"Chat request from {user_email}: {message[:50]}...")
        logger.info(f"Chat response: {answer[:50]}...")
        logger.info(f"RAG usado: {'✅ Sí' if rag_context else '❌ No'}")
        
        return answer
        
    except Exception as e:
        logger.error(f"Error en OpenAI API: {str(e)}")
        return f"❌ Error al procesar tu pregunta. Inténtalo de nuevo en unos segundos."

def _demo_answer(msg: str) -> str:
    """Respuesta demo cuando no hay OpenAI configurado"""
    return f"""🤖 **Modo Demo - YourGains AI**

Pregunta recibida: "{msg}"

Esta es una respuesta de demostración. Para activar el chat con IA real:

1. Configura tu OPENAI_API_KEY en las variables de entorno
2. La IA responderá con consejos personalizados de entrenamiento y nutrición
3. Chat ilimitado para usuarios PREMIUM

*Tip: Para usuarios FREE quedan respuestas limitadas. ¡Considera upgrade a PREMIUM!*"""

def _demo_stream_generator(msg: str):
    demo = _demo_answer(msg)
    for chunk in demo.split(" "):
        yield f"data: {chunk} \n\n"
    yield "event: done\n"
    yield "data: {}\n\n"

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    body: ChatRequestBody,
    db: Session = Depends(get_db),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
):
    """
    Chat con IA especializada en fitness con sistema RAG.
    
    - FREE: 2 preguntas gratis
    - PREMIUM: Chat ilimitado
    - RAG: Consulta base de conocimiento científica (46 documentos)
    """
    if not x_user_email:
        raise HTTPException(status_code=400, detail="Falta cabecera X-User-Email")

    # Validar formato de email básico
    if "@" not in x_user_email or "." not in x_user_email:
        raise HTTPException(status_code=400, detail="Email inválido")

    user = db.query(Usuario).filter(Usuario.email == x_user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Verificar estado premium
    plan_type = (user.plan_type or "FREE").upper()
    is_premium = plan_type == "PREMIUM" or bool(user.is_premium)

    # Control de límites para usuarios FREE
    if not is_premium and (user.chat_uses_free or 0) <= 0:
        raise HTTPException(
            status_code=402, 
            detail="Has agotado tus preguntas gratis. Pásate a PREMIUM para chat ilimitado."
        )

    # Validar longitud del mensaje
    if len(body.message.strip()) < 3:
        raise HTTPException(status_code=400, detail="El mensaje debe tener al menos 3 caracteres")
    
    if len(body.message) > 500:
        raise HTTPException(status_code=400, detail="El mensaje es demasiado largo (máximo 500 caracteres)")

    # Procesar con IA (ahora con RAG)
    try:
        if api_key and client:
            answer = await call_openai_chat(body.message, x_user_email)
        else:
            answer = _demo_answer(body.message)
        
        # Descontar uso si es FREE
        remaining = None
        if not is_premium:
            user.chat_uses_free = max(0, (user.chat_uses_free or 0) - 1)
            remaining = user.chat_uses_free
            db.commit()
            
        return ChatResponse(answer=answer, chat_uses_free_restantes=remaining)
        
    except Exception as e:
        logger.error(f"Error en chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# Endpoint adicional para obtener estado del chat
@router.get("/chat/status")
def chat_status(
    db: Session = Depends(get_db),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
):
    """Obtiene el estado actual del chat del usuario"""
    if not x_user_email:
        raise HTTPException(status_code=400, detail="Falta cabecera X-User-Email")
        
    user = db.query(Usuario).filter(Usuario.email == x_user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    is_premium = (user.plan_type == "PREMIUM") or bool(user.is_premium)
    
    return {
        "is_premium": is_premium,
        "chat_uses_free": user.chat_uses_free if not is_premium else None,
        "plan_type": user.plan_type,
        "openai_available": bool(api_key and client)
    }


@router.post("/chat/stream")
def chat_stream(
    body: ChatRequestBody,
    db: Session = Depends(get_db),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
):
    """Streaming SSE del chat para respuesta en tiempo real."""
    if not x_user_email:
        raise HTTPException(status_code=400, detail="Falta cabecera X-User-Email")

    if "@" not in x_user_email or "." not in x_user_email:
        raise HTTPException(status_code=400, detail="Email inválido")

    user = db.query(Usuario).filter(Usuario.email == x_user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    plan_type = (user.plan_type or "FREE").upper()
    is_premium = plan_type == "PREMIUM" or bool(user.is_premium)

    if len(body.message.strip()) < 3:
        raise HTTPException(status_code=400, detail="El mensaje debe tener al menos 3 caracteres")
    if len(body.message) > 500:
        raise HTTPException(status_code=400, detail="El mensaje es demasiado largo (máximo 500 caracteres)")

    # Límite de FREE antes de comenzar a consumir recursos
    if not is_premium and (user.chat_uses_free or 0) <= 0:
        raise HTTPException(status_code=402, detail="Has agotado tus preguntas gratis. Pásate a PREMIUM para chat ilimitado.")

    def event_generator():
        try:
            if not (api_key and client):
                # Stream de demo
                for line in _demo_stream_generator(body.message):
                    yield line
                # Ajuste de consumos para FREE
                remaining = None
                if not is_premium:
                    user.chat_uses_free = max(0, (user.chat_uses_free or 0) - 1)
                    remaining = user.chat_uses_free
                    db.commit()
                meta = {"chat_uses_free_restantes": remaining}
                yield f"event: meta\ndata: {json.dumps(meta, ensure_ascii=False)}\n\n"
                return

            # 🔥 NUEVO: Obtener contexto RAG (ejecutar en thread para no bloquear)
            # Nota: Para streaming, obtenemos el RAG de forma síncrona usando asyncio.run
            # en un thread separado para no bloquear el generador
            import threading
            
            rag_context_result = [""]  # Usar lista para modificar desde thread
            
            def get_rag_sync():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    rag_context_result[0] = loop.run_until_complete(get_rag_context_for_chat(body.message))
                    loop.close()
                except Exception as e:
                    logger.error(f"Error obteniendo RAG en streaming: {e}")
                    rag_context_result[0] = ""
            
            # Ejecutar en thread para no bloquear
            rag_thread = threading.Thread(target=get_rag_sync)
            rag_thread.start()
            rag_thread.join(timeout=2)  # Timeout de 2 segundos para no bloquear mucho
            
            rag_context = rag_context_result[0]
            
            # Construir prompt del sistema con contexto RAG
            system_prompt = get_fitness_prompt()
            if rag_context:
                system_prompt += "\n\n" + rag_context
                logger.info("✅ Contexto RAG añadido al prompt (streaming)")
            
            # Construcción de mensajes para OpenAI
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Usuario: {x_user_email}\nPregunta: {body.message}"},
            ]

            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=300,
                stream=True,
            )

            # Emitir tokens según llegan
            for chunk in stream:
                try:
                    delta = chunk.choices[0].delta
                    if not delta:
                        continue
                    text = getattr(delta, "content", None)
                    if not text:
                        continue
                    # Escape de nuevas líneas conforme SSE
                    text = text.replace("\r", "").replace("\n", "\n")
                    yield f"data: {text}\n\n"
                except Exception:
                    continue

            # Fin del stream
            yield "event: done\n"
            yield "data: {}\n\n"

            # Descontar uso si es FREE
            remaining = None
            if not is_premium:
                user.chat_uses_free = max(0, (user.chat_uses_free or 0) - 1)
                remaining = user.chat_uses_free
                db.commit()

            meta = {"chat_uses_free_restantes": remaining}
            yield f"event: meta\ndata: {json.dumps(meta, ensure_ascii=False)}\n\n"

        except HTTPException as he:
            err = {"detail": he.detail}
            yield f"event: error\ndata: {json.dumps(err, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"Error en chat/stream: {str(e)}")
            err = {"detail": "Error interno del servidor"}
            yield f"event: error\ndata: {json.dumps(err, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")