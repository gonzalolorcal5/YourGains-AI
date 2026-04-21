from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, date
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.auth_utils import get_current_user
from app.models import Usuario, EntrenamientoSession, EntrenamientoSet

router = APIRouter(prefix="/api/tracking", tags=["tracking"])


class SetTrack(BaseModel):
    nombre_rutina: str
    ejercicio_nombre: str
    peso: float
    repes: int
    rpe: Optional[int] = None
    numero_serie: int


@router.post("/guardar-serie")
def guardar_serie(
    datos: SetTrack,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    # Obtener el inicio del día para la búsqueda
    hoy_inicio = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. Buscar si ya hay una sesión HOY para esta rutina específica
    sesion = db.query(EntrenamientoSession).filter(
        EntrenamientoSession.user_id == usuario.id,
        EntrenamientoSession.nombre_rutina == datos.nombre_rutina,
        EntrenamientoSession.fecha >= hoy_inicio
    ).first()

    # 2. Si no existe, la creamos al vuelo (UX: cero fricción para el usuario)
    if not sesion:
        sesion = EntrenamientoSession(
            user_id=usuario.id,
            nombre_rutina=datos.nombre_rutina,
            fecha=datetime.utcnow()
        )
        db.add(sesion)
        db.commit()
        db.refresh(sesion)

    # 3. Guardar la serie vinculada a la sesión
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

    return {"success": True, "message": "Serie guardada correctamente", "session_id": sesion.id}
