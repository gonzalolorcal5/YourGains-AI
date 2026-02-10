# app/routes/bodyscan.py
"""
Body scan: análisis de foto corporal con GPT-4o Vision usando datos del Plan del usuario.
"""
import os
import json
import re
import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from openai import AsyncOpenAI

from app.database import get_db
from app.auth_utils import get_current_user
from app.models import Usuario, Plan, BodyScan

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY no configurada; bodyscan no funcionará hasta configurarla")

client = AsyncOpenAI(api_key=OPENAI_API_KEY, timeout=90.0, max_retries=2) if OPENAI_API_KEY else None
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

router = APIRouter(prefix="/bodyscan", tags=["bodyscan"])


class BodyScanAnalyzeRequest(BaseModel):
    """Lista de imágenes en base64 (sin prefijo data:...)."""
    images: List[str]


def _normalize_base64_url(b64: str) -> str:
    """Añade prefijo data URL si no está presente."""
    s = (b64 or "").strip()
    if not s:
        return ""
    if s.startswith("data:"):
        return s
    return f"data:image/jpeg;base64,{s}"


def _extract_json_from_response(text: str) -> dict:
    """Extrae un objeto JSON de la respuesta (puede venir con markdown)."""
    text = (text or "").strip()
    if text.startswith("```"):
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        else:
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1].strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No se encontró JSON en la respuesta de GPT")
    return json.loads(match.group(0))


@router.post("/analyze")
async def analyze_body_scan(
    body: BodyScanAnalyzeRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Analiza una o varias fotos corporales con GPT-4o Vision usando datos del Plan del usuario.
    Devuelve tipo de cuerpo, % graso estimado, puntos fuertes/debiles y recomendación (Volumen/Definición).
    """
    if not client:
        raise HTTPException(status_code=503, detail="Servicio de análisis no configurado (OPENAI_API_KEY)")

    images = body.images or []
    if not images:
        raise HTTPException(status_code=400, detail="Se requiere al menos una imagen en base64")

    # Plan más reciente del usuario para peso, altura, sexo, experiencia
    plan = (
        db.query(Plan)
        .filter(Plan.user_id == usuario.id)
        .order_by(Plan.fecha_creacion.desc())
        .first()
    )
    peso = None
    altura = None
    sexo = "no indicado"
    experiencia = "principiante"
    if plan:
        try:
            peso = float(plan.peso) if plan.peso else None
        except (TypeError, ValueError):
            peso = None
        altura = getattr(plan, "altura", None)
        if altura is not None and isinstance(altura, str):
            try:
                altura = float(altura)
            except (TypeError, ValueError):
                altura = None
        sexo = (plan.sexo or "no indicado").strip() or "no indicado"
        experiencia = (plan.experiencia or "principiante").strip() or "principiante"

    # Construir contenido del mensaje: texto + imágenes
    prompt = f"""Eres un experto en fitness y composición corporal. Analiza las imágenes que te envío junto con estos datos del usuario:

- Peso: {peso or "no indicado"} kg
- Altura: {altura or "no indicado"} cm
- Sexo: {sexo}
- Nivel de experiencia: {experiencia}

Debes determinar, con precisión y basándote en las imágenes y los datos:

1. tipo_cuerpo: clasificación (ectomorfo, mesomorfo, endomorfo o intermedio; ej. "mesomorfo-ectomorfo").
2. grasa_estimada_min y grasa_estimada_max: rango de % graso corporal estimado visualmente (números, ej. 12 y 18).
3. puntos_fuertes: texto breve con 2-4 grupos musculares o aspectos positivos visibles.
4. puntos_debiles: texto breve con 2-4 aspectos a mejorar o grupos a priorizar.
5. recomendacion: una sola palabra o frase corta: "Volumen", "Definición", "Recomposición" o "Mantenimiento", según lo que más le convenga.
6. analisis_completo: párrafo breve (2-4 frases) con tu análisis global y consejo profesional.

Responde ÚNICAMENTE con un JSON válido, sin markdown ni texto alrededor, con esta estructura exacta:

{{
  "tipo_cuerpo": "string",
  "grasa_estimada_min": number,
  "grasa_estimada_max": number,
  "puntos_fuertes": "string",
  "puntos_debiles": "string",
  "recomendacion": "string",
  "analisis_completo": "string"
}}
"""

    content = [{"type": "text", "text": prompt}]
    for b64 in images[:5]:  # Máximo 5 imágenes por petición
        url = _normalize_base64_url(b64)
        if url:
            content.append({"type": "image_url", "image_url": {"url": url}})

    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": content}],
            max_tokens=1024,
            temperature=0.3,
        )
    except Exception as e:
        logger.exception("Error llamando a GPT-4o para bodyscan: %s", e)
        raise HTTPException(status_code=502, detail=f"Error del servicio de IA: {str(e)}")

    raw = response.choices[0].message.content
    if not raw:
        raise HTTPException(status_code=502, detail="La IA no devolvió contenido")

    try:
        data = _extract_json_from_response(raw)
    except (ValueError, json.JSONDecodeError) as e:
        logger.warning("Respuesta GPT no es JSON válido: %s", raw[:300])
        raise HTTPException(status_code=502, detail=f"La IA no devolvió JSON válido: {str(e)}")

    # Guardar en BodyScan
    scan = BodyScan(
        user_id=usuario.id,
        fecha_scan=datetime.utcnow(),
        peso=peso,
        altura=float(altura) if altura is not None else None,
        experiencia=experiencia,
        tipo_cuerpo=data.get("tipo_cuerpo"),
        grasa_estimada_min=data.get("grasa_estimada_min"),
        grasa_estimada_max=data.get("grasa_estimada_max"),
        puntos_fuertes=data.get("puntos_fuertes"),
        puntos_debiles=data.get("puntos_debiles"),
        recomendacion=data.get("recomendacion"),
        analisis_completo=data.get("analisis_completo"),
        image_url=None,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    return {
        "success": True,
        "scan_id": scan.id,
        "tipo_cuerpo": scan.tipo_cuerpo,
        "grasa_estimada_min": scan.grasa_estimada_min,
        "grasa_estimada_max": scan.grasa_estimada_max,
        "puntos_fuertes": scan.puntos_fuertes,
        "puntos_debiles": scan.puntos_debiles,
        "recomendacion": scan.recomendacion,
        "analisis_completo": scan.analisis_completo,
        "peso": scan.peso,
        "altura": scan.altura,
        "experiencia": scan.experiencia,
    }
