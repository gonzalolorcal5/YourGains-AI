from pydantic import BaseModel, field_validator
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
    session_duration: Optional[str] = '45-60'  # Duración de sesión: "30-45", "45-60", "60-75", "75-90", "90+"
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

# ---------- USER RESPONSE ----------
class UserResponse(BaseModel):
    """Schema de respuesta del usuario con valores por defecto para compatibilidad con usuarios antiguos"""
    id: int
    email: str
    plan_type: str = "FREE"
    is_premium: bool = False
    racha_actual: int = 0
    mejor_racha: int = 0
    onboarding_completed: bool = False
    session_duration: str = "45-60"  # Valor por defecto para usuarios antiguos
    profile_picture: Optional[str] = None
    chat_uses_free: int = 2
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    subscription_type: Optional[str] = None

# ---------- EXTRA OPCIONAL ----------
class UserCreate(BaseModel):
    email: str
    password: str


class EjercicioEdit(BaseModel):
    """Un ejercicio dentro de un día de rutina editada."""
    nombre: str
    series: int
    repeticiones: str
    descanso: str

    @field_validator('nombre')
    @classmethod
    def nombre_no_vacio(cls, v):
        v = (v or '').strip()
        if not v:
            raise ValueError('El nombre del ejercicio no puede estar vacío')
        if len(v) > 100:
            raise ValueError('El nombre del ejercicio es demasiado largo (máx 100 caracteres)')
        return v

    @field_validator('series')
    @classmethod
    def series_en_rango(cls, v):
        if v < 1 or v > 10:
            raise ValueError('Las series deben estar entre 1 y 10')
        return v

    @field_validator('repeticiones')
    @classmethod
    def repeticiones_no_vacio(cls, v):
        v = (v or '').strip()
        if not v:
            raise ValueError('Las repeticiones no pueden estar vacías')
        if len(v) > 30:
            raise ValueError('Repeticiones demasiado largo (máx 30 caracteres)')
        return v

    @field_validator('descanso')
    @classmethod
    def descanso_no_vacio(cls, v):
        v = (v or '').strip()
        if not v:
            raise ValueError('El descanso no puede estar vacío')
        if len(v) > 30:
            raise ValueError('Descanso demasiado largo (máx 30 caracteres)')
        return v


class DiaEdit(BaseModel):
    """Un día de la rutina editada."""
    dia: str
    ejercicios: List[EjercicioEdit]

    @field_validator('dia')
    @classmethod
    def dia_no_vacio(cls, v):
        v = (v or '').strip()
        if not v:
            raise ValueError('El nombre del día no puede estar vacío')
        if len(v) > 100:
            raise ValueError('Nombre de día demasiado largo (máx 100 caracteres)')
        return v

    @field_validator('ejercicios')
    @classmethod
    def al_menos_un_ejercicio(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Cada día debe tener al menos un ejercicio')
        if len(v) > 20:
            raise ValueError('Demasiados ejercicios en un día (máx 20)')
        return v


class RutinaEditRequest(BaseModel):
    """Body del PUT /user/rutina."""
    dias: List[DiaEdit]

    @field_validator('dias')
    @classmethod
    def al_menos_un_dia(cls, v):
        if not v or len(v) == 0:
            raise ValueError('La rutina debe tener al menos un día')
        if len(v) > 7:
            raise ValueError('Demasiados días en la rutina (máx 7)')
        return v
