from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth_utils import get_current_user
from app.database import get_db
from app.models import Usuario

router = APIRouter()


class AvatarRequest(BaseModel):
    profile_picture: str


@router.post("/api/user/avatar")
def upload_avatar(
    request: AvatarRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Sube y actualiza el avatar en Base64 comprimido del usuario"""
    try:
        user = db.query(Usuario).filter(Usuario.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        user.profile_picture = request.profile_picture
        db.commit()
        return {"success": True, "message": "Avatar actualizado"}
    except Exception as e:
        db.rollback()
        print(f"❌ Error guardando avatar: {e}")
        raise HTTPException(status_code=500, detail="Error interno al guardar")
