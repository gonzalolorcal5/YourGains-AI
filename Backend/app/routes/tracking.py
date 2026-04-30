from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta, timezone
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
import json

from app.database import get_db
from app.auth_utils import get_current_user
from app.models import Usuario, EntrenamientoSession, EntrenamientoSet

load_dotenv()
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=60.0)

router = APIRouter(prefix="/api/tracking", tags=["tracking"])


class SetTrack(BaseModel):
    nombre_rutina: str
    dia_rutina: str  # Día específico de la rutina (ej: "Lunes", "Día 1")
    ejercicio_nombre: str
    peso: float
    repes: int
    rpe: Optional[int] = None
    numero_serie: int


def _serialize_set(set_row: EntrenamientoSet) -> Dict[str, Any]:
    return {
        "id": set_row.id,
        "ejercicio_nombre": set_row.ejercicio_nombre,
        "peso": set_row.peso,
        "reps": set_row.reps,
        "rpe": set_row.rpe,
        "numero_serie": set_row.numero_serie
    }


def _serialize_session(session_row: EntrenamientoSession, series: List[EntrenamientoSet]) -> Dict[str, Any]:
    total_series = len(series)
    total_reps = sum((serie.reps or 0) for serie in series)
    total_volume_kg = sum((serie.peso or 0) * (serie.reps or 0) for serie in series)
    avg_rpe_values = [serie.rpe for serie in series if serie.rpe is not None]
    avg_rpe = (sum(avg_rpe_values) / len(avg_rpe_values)) if avg_rpe_values else None

    ejercicios_unicos = list({
        (serie.ejercicio_nombre or "").strip()
        for serie in series
        if (serie.ejercicio_nombre or "").strip()
    })

    return {
        "session_id": session_row.id,
        "fecha": session_row.fecha.isoformat() if session_row.fecha else None,
        "nombre_rutina": session_row.nombre_rutina,
        "notas": session_row.notas,
        "sets": [_serialize_set(serie) for serie in series],
        "metrics": {
            "total_series": total_series,
            "total_reps": total_reps,
            "total_volume_kg": round(total_volume_kg, 2),
            "avg_rpe": round(avg_rpe, 2) if avg_rpe is not None else None,
            "ejercicios_unicos": ejercicios_unicos
        }
    }


@router.post("/guardar-serie")
def guardar_serie(
    datos: SetTrack,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    hoy_inicio = datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # Nombre compuesto para aislar sesiones por día
    # Ej: "Tu Rutina Personalizada | Lunes"
    nombre_sesion = f"{datos.nombre_rutina} | {datos.dia_rutina}"

    # 1. Buscar sesión de hoy para este día específico
    sesion = db.query(EntrenamientoSession).filter(
        EntrenamientoSession.user_id == usuario.id,
        EntrenamientoSession.nombre_rutina == nombre_sesion,
        EntrenamientoSession.fecha >= hoy_inicio
    ).first()

    # 2. Crear sesión si no existe
    if not sesion:
        sesion = EntrenamientoSession(
            user_id=usuario.id,
            nombre_rutina=nombre_sesion,
            fecha=datetime.utcnow()
        )
        db.add(sesion)
        db.commit()
        db.refresh(sesion)

    # 3. UPSERT: actualizar si ya existe esta serie, insertar si no
    serie_existente = db.query(EntrenamientoSet).filter(
        EntrenamientoSet.session_id == sesion.id,
        EntrenamientoSet.ejercicio_nombre == datos.ejercicio_nombre,
        EntrenamientoSet.numero_serie == datos.numero_serie
    ).first()

    if serie_existente:
        serie_existente.peso = datos.peso
        serie_existente.reps = datos.repes
        serie_existente.rpe = datos.rpe
    else:
        nueva_serie = EntrenamientoSet(
            session_id=sesion.id,
            ejercicio_nombre=datos.ejercicio_nombre,
            peso=datos.peso,
            reps=datos.repes,
            rpe=datos.rpe,
            numero_serie=datos.numero_serie
        )
        db.add(nueva_serie)

    db.commit()

    return {
        "success": True,
        "message": "Serie guardada/actualizada",
        "session_id": sesion.id
    }


@router.get("/historial")
def obtener_historial_tracking(
    limit: int = 10,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    """
    Devuelve las últimas sesiones del usuario con sus series y métricas agregadas.
    Incluye un bloque weekly_context para usar como base en resúmenes semanales con IA.
    """
    limit = max(1, min(limit, 50))

    sesiones = db.query(EntrenamientoSession).filter(
        EntrenamientoSession.user_id == usuario.id
    ).order_by(EntrenamientoSession.fecha.desc()).limit(limit).all()

    if not sesiones:
        return {
            "success": True,
            "sessions": [],
            "weekly_context": {
                "total_sessions": 0,
                "total_sets": 0,
                "total_reps": 0,
                "total_volume_kg": 0,
                "avg_rpe": None,
                "top_exercises": []
            },
            "ai_summary_ready": True
        }

    sesiones_ids = [s.id for s in sesiones]
    all_sets = db.query(EntrenamientoSet).filter(
        EntrenamientoSet.session_id.in_(sesiones_ids)
    ).order_by(EntrenamientoSet.numero_serie.asc()).all()

    sets_by_session: Dict[int, List[EntrenamientoSet]] = {sid: [] for sid in sesiones_ids}
    for serie in all_sets:
        sets_by_session.setdefault(serie.session_id, []).append(serie)

    sessions_payload = [
        _serialize_session(sesion, sets_by_session.get(sesion.id, []))
        for sesion in sesiones
    ]

    all_series = [serie for session_sets in sets_by_session.values() for serie in session_sets]
    total_sets = len(all_series)
    total_reps = sum((serie.reps or 0) for serie in all_series)
    total_volume_kg = sum((serie.peso or 0) * (serie.reps or 0) for serie in all_series)
    rpe_values = [serie.rpe for serie in all_series if serie.rpe is not None]
    avg_rpe = (sum(rpe_values) / len(rpe_values)) if rpe_values else None

    exercise_counter: Dict[str, int] = {}
    for serie in all_series:
        nombre = (serie.ejercicio_nombre or "").strip()
        if not nombre:
            continue
        exercise_counter[nombre] = exercise_counter.get(nombre, 0) + 1

    top_exercises = [
        {"ejercicio_nombre": nombre, "sets": sets_count}
        for nombre, sets_count in sorted(
            exercise_counter.items(),
            key=lambda item: item[1],
            reverse=True
        )[:5]
    ]

    return {
        "success": True,
        "sessions": sessions_payload,
        "weekly_context": {
            "total_sessions": len(sesiones),
            "total_sets": total_sets,
            "total_reps": total_reps,
            "total_volume_kg": round(total_volume_kg, 2),
            "avg_rpe": round(avg_rpe, 2) if avg_rpe is not None else None,
            "top_exercises": top_exercises
        },
        "ai_summary_ready": True
    }


@router.get("/sesion-semana-actual")
def obtener_sesion_semana_actual(
    nombre_rutina: str,
    dia_rutina: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    """
    Devuelve las series guardadas para un bloque de rutina específico
    dentro de la semana actual (lunes-domingo hora España UTC+1).
    Usado por el frontend para precargar inputs con datos registrados.
    """
    # Calcular "ahora" en UTC+1 (España)
    tz_spain = timezone(timedelta(hours=1))
    ahora_spain = datetime.now(tz_spain)

    # Inicio de semana: lunes 00:00 hora España
    dias_desde_lunes = ahora_spain.weekday()  # 0=lunes, 6=domingo
    inicio_semana_spain = ahora_spain.replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(days=dias_desde_lunes)

    # Convertir a UTC para comparar con la BD (que guarda en UTC)
    inicio_semana_utc = inicio_semana_spain.astimezone(
        timezone.utc
    ).replace(tzinfo=None)

    nombre_sesion = f"{nombre_rutina} | {dia_rutina}"

    # Buscar la sesión más reciente de este bloque en la semana actual
    sesion = db.query(EntrenamientoSession).filter(
        EntrenamientoSession.user_id == usuario.id,
        EntrenamientoSession.nombre_rutina == nombre_sesion,
        EntrenamientoSession.fecha >= inicio_semana_utc
    ).order_by(EntrenamientoSession.fecha.desc()).first()

    if not sesion:
        return {
            "success": True,
            "has_data": False,
            "sets": []
        }

    series = db.query(EntrenamientoSet).filter(
        EntrenamientoSet.session_id == sesion.id
    ).order_by(
        EntrenamientoSet.ejercicio_nombre.asc(),
        EntrenamientoSet.numero_serie.asc()
    ).all()

    sets_payload = [
        {
            "ejercicio_nombre": s.ejercicio_nombre,
            "numero_serie": s.numero_serie,
            "peso": s.peso,
            "reps": s.reps,
            "rpe": s.rpe
        }
        for s in series
    ]

    return {
        "success": True,
        "has_data": True,
        "sets": sets_payload
    }


def _calcular_stats_semana(sesiones: list, all_sets_map: dict) -> dict:
    """
    Calcula estadísticas por ejercicio para una semana.
    Devuelve dict: ejercicio_nombre -> {peso_max, peso_min, vol_total, reps_total, avg_rpe, num_series}
    """
    stats = {}
    for sesion in sesiones:
        sets = all_sets_map.get(sesion.id, [])
        for s in sets:
            nombre = (s.ejercicio_nombre or "").strip()
            if not nombre:
                continue
            if nombre not in stats:
                stats[nombre] = {
                    "peso_max": 0.0,
                    "vol_total": 0.0,
                    "reps_total": 0,
                    "rpe_values": [],
                    "num_series": 0
                }
            peso = s.peso or 0.0
            reps = s.reps or 0
            stats[nombre]["peso_max"] = max(stats[nombre]["peso_max"], peso)
            stats[nombre]["vol_total"] += round(peso * reps, 2)
            stats[nombre]["reps_total"] += reps
            stats[nombre]["num_series"] += 1
            if s.rpe is not None:
                stats[nombre]["rpe_values"].append(s.rpe)
    # Calcular avg_rpe y limpiar rpe_values
    for nombre in stats:
        rpe_vals = stats[nombre].pop("rpe_values")
        stats[nombre]["avg_rpe"] = round(
            sum(rpe_vals) / len(rpe_vals), 1
        ) if rpe_vals else None
        stats[nombre]["vol_total"] = round(stats[nombre]["vol_total"], 2)
    return stats


@router.post("/resumen-semanal")
async def generar_resumen_semanal(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    """
    Genera un resumen semanal con IA comparando semana actual vs anterior.
    Python calcula todas las matemáticas — GPT solo redacta.
    """
    # --- Calcular rangos de fechas en UTC+1 España ---
    tz_spain = timezone(timedelta(hours=1))
    ahora_spain = datetime.now(tz_spain)
    dias_desde_lunes = ahora_spain.weekday()

    inicio_semana_actual_spain = ahora_spain.replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(days=dias_desde_lunes)
    inicio_semana_anterior_spain = inicio_semana_actual_spain - timedelta(weeks=1)
    fin_semana_anterior_spain = inicio_semana_actual_spain - timedelta(seconds=1)

    # Convertir a UTC para BD
    inicio_actual_utc = inicio_semana_actual_spain.astimezone(
        timezone.utc).replace(tzinfo=None)
    inicio_anterior_utc = inicio_semana_anterior_spain.astimezone(
        timezone.utc).replace(tzinfo=None)
    fin_anterior_utc = fin_semana_anterior_spain.astimezone(
        timezone.utc).replace(tzinfo=None)

    # --- Consultar sesiones semana actual ---
    sesiones_actual = db.query(EntrenamientoSession).filter(
        EntrenamientoSession.user_id == usuario.id,
        EntrenamientoSession.fecha >= inicio_actual_utc
    ).all()

    # Sin datos esta semana → respuesta directa sin GPT
    if not sesiones_actual:
        return {
            "success": True,
            "tiene_datos": False,
            "mensaje": "Aún no tienes entrenamientos registrados esta semana. ¡Empieza a entrenar para ver tu resumen!",
            "resumen": None
        }

    # --- Consultar sesiones semana anterior ---
    sesiones_anterior = db.query(EntrenamientoSession).filter(
        EntrenamientoSession.user_id == usuario.id,
        EntrenamientoSession.fecha >= inicio_anterior_utc,
        EntrenamientoSession.fecha <= fin_anterior_utc
    ).all()

    # --- Cargar todos los sets de ambas semanas ---
    ids_actual = [s.id for s in sesiones_actual]
    ids_anterior = [s.id for s in sesiones_anterior]
    todos_ids = ids_actual + ids_anterior

    all_sets = db.query(EntrenamientoSet).filter(
        EntrenamientoSet.session_id.in_(todos_ids)
    ).all() if todos_ids else []

    sets_map = {}
    for s in all_sets:
        sets_map.setdefault(s.session_id, []).append(s)

    # --- Python calcula todas las matemáticas ---
    stats_actual = _calcular_stats_semana(sesiones_actual, sets_map)
    stats_anterior = _calcular_stats_semana(sesiones_anterior, sets_map)
    es_primera_semana = len(sesiones_anterior) == 0

    # Construir bloque de datos para GPT (ya calculado, solo texto)
    ejercicios_texto = []
    for nombre, datos in stats_actual.items():
        linea = f"- {nombre}: {datos['num_series']} series, peso máx {datos['peso_max']}kg, volumen total {datos['vol_total']}kg, RPE medio {datos['avg_rpe'] or 'no registrado'}"
        if not es_primera_semana and nombre in stats_anterior:
            ant = stats_anterior[nombre]
            diff_vol = round(datos['vol_total'] - ant['vol_total'], 2)
            diff_peso = round(datos['peso_max'] - ant['peso_max'], 2)
            linea += f" | Semana anterior: peso máx {ant['peso_max']}kg, volumen {ant['vol_total']}kg (diferencia volumen: {'+' if diff_vol >= 0 else ''}{diff_vol}kg, diferencia peso máx: {'+' if diff_peso >= 0 else ''}{diff_peso}kg)"
        ejercicios_texto.append(linea)

    datos_semana = "\n".join(ejercicios_texto)
    num_sesiones = len(sesiones_actual)

    if es_primera_semana:
        contexto_comparacion = "Es la primera semana del usuario, no hay datos de semana anterior para comparar."
    else:
        contexto_comparacion = f"Hay datos de la semana anterior para comparar. Analiza la progresión ejercicio por ejercicio."

    prompt = f"""Eres el entrenador personal IA de YourGains. Analiza los datos de entrenamiento de esta semana y genera un resumen profesional y motivador en español.

{contexto_comparacion}

Datos de esta semana ({num_sesiones} sesión/es registrada/s):
{datos_semana}

Genera un resumen con este formato JSON exacto, sin markdown:
{{
  "resumen_general": "2-3 frases sobre cómo fue la semana en general",
  "analisis_por_ejercicio": [
    {{
      "ejercicio": "nombre del ejercicio",
      "observacion": "frase breve sobre rendimiento y progresión si hay datos anteriores",
      "peso_recomendado_proxima_semana": número o null
    }}
  ],
  "conclusion": "1-2 frases motivadoras con proyección para la próxima semana"
}}

Instrucciones:
- Solo analiza los ejercicios con datos reales, no inventes
- Si hay comparativa con semana anterior, menciona si mejoró o bajó el rendimiento
- El peso recomendado debe ser un número realista basado en la progresión, o null si no hay base suficiente
- Tono profesional pero motivador, como un entrenador personal de confianza
- NO menciones que eres una IA dentro del análisis
"""

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.4
        )
        raw = response.choices[0].message.content or ""
        # Limpiar markdown si GPT lo añade
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        resumen_data = json.loads(raw)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error generando resumen con IA: {str(e)}"
        )

    return {
        "success": True,
        "tiene_datos": True,
        "es_primera_semana": es_primera_semana,
        "num_sesiones": num_sesiones,
        "resumen": resumen_data
    }
