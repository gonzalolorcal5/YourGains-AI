from pydantic import BaseModel
from typing import List, Optional, Any

# ---------- PLAN ----------

class PlanRequest(BaseModel):
    altura: int
    peso: int
    edad: int
    sexo: str
    experiencia: str
    objetivo: str
    materiales: str
    dias_entrenamiento: int
    training_days: Optional[List[str]] = None  # ["lunes", "martes", "miércoles", ...]
    tipo_cuerpo: Optional[str] = None
    idioma: str = "es"
    puntos_fuertes: Optional[str] = None
    puntos_debiles: Optional[str] = None
    entrenar_fuerte: Optional[str] = None
    lesiones: Optional[str] = None
    alergias: Optional[str] = None
    restricciones_dieta: Optional[str] = None

class PlanResponse(BaseModel):
    rutina: Any
    dieta: Any
    motivacion: str

# ---------- AUTH ----------

class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ---------- EXTRA OPCIONAL ----------
class UserCreate(BaseModel):
    email: str
    password: str
