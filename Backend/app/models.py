from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)

    # OAuth / Social login
    google_id = Column(String, nullable=True)
    oauth_provider = Column(String, nullable=True)
    profile_picture = Column(String, nullable=True)

    # Stripe / gating
    is_premium = Column(Boolean, default=False, nullable=False)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)  # 🆕 NUEVO campo

    # NUEVO: plan y cupo de chat
    plan_type = Column(String, default="FREE", nullable=False)   # FREE | PREMIUM_MONTHLY | PREMIUM_YEARLY
    chat_uses_free = Column(Integer, default=2, nullable=False)  # preguntas gratis disponibles
    
    # Onboarding
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    
    # Campos dinámicos para rutina y dieta
    current_routine = Column(Text, default='{}', nullable=False)
    current_diet = Column(Text, default='{}', nullable=False)
    injuries = Column(Text, default='[]', nullable=False)
    focus_areas = Column(Text, default='[]', nullable=False)
    disliked_foods = Column(Text, default='[]', nullable=False)
    modification_history = Column(Text, default='[]', nullable=False)
    
    # Lock mechanism para evitar generaciones duplicadas de plan
    is_generating_plan = Column(Boolean, default=False, nullable=False)

    plan = relationship("Plan", back_populates="usuario", uselist=False)
    body_scans = relationship("BodyScan", backref="usuario", cascade="all, delete-orphan")


class Plan(Base):
    __tablename__ = "planes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuarios.id"), unique=True)

    altura = Column(Integer, nullable=False)
    peso = Column(String, nullable=False)
    edad = Column(Integer, nullable=False)
    sexo = Column(String, nullable=False)
    experiencia = Column(String, nullable=False)
    objetivo = Column(String, nullable=False)  # Legacy field
    objetivo_gym = Column(String, nullable=True)  # ganar_musculo, ganar_fuerza, mantener_forma, etc.
    objetivo_dieta = Column(String, nullable=True)  # Legacy field
    objetivo_nutricional = Column(String, nullable=True)  # volumen, definicion, mantenimiento, recomposicion
    materiales = Column(String, nullable=False)
    tipo_cuerpo = Column(String, nullable=True)
    nivel_actividad = Column(String, default="moderado", nullable=False)  # sedentario, ligero, moderado, activo, muy_activo
    idioma = Column(String, default="es")
    puntos_fuertes = Column(String, nullable=True)
    puntos_debiles = Column(String, nullable=True)
    entrenar_fuerte = Column(String, nullable=True)
    lesiones = Column(String, nullable=True)
    alergias = Column(String, nullable=True)
    restricciones_dieta = Column(String, nullable=True)
    session_duration = Column(String, nullable=True, default='45-60')  # Duración de sesión: "30-45", "45-60", "60-75", "75-90", "90+"

    rutina = Column(Text, nullable=False)
    dieta = Column(Text, nullable=False)
    motivacion = Column(Text, nullable=False)

    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="plan")


class BodyScan(Base):
    """Análisis de foto corporal (body scan) con IA usando datos del usuario."""
    __tablename__ = "body_scans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    fecha_scan = Column(DateTime, default=datetime.utcnow)
    peso = Column(Float, nullable=True)
    altura = Column(Float, nullable=True)
    experiencia = Column(String, nullable=True)
    tipo_cuerpo = Column(String, nullable=True)
    grasa_estimada_min = Column(Float, nullable=True)
    grasa_estimada_max = Column(Float, nullable=True)

    puntos_fuertes = Column(Text, nullable=True)
    puntos_debiles = Column(Text, nullable=True)
    recomendacion = Column(String, nullable=True)
    analisis_completo = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)


class ProcessedWebhookEvent(Base):
    """
    Idempotencia: eventos de Stripe ya procesados.
    Evita duplicar planes cuando Stripe reenvía el mismo webhook (retry).
    """
    __tablename__ = "webhook_events_processed"

    id = Column(Integer, primary_key=True, index=True)
    stripe_event_id = Column(String(255), unique=True, nullable=False, index=True)
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class EntrenamientoSession(Base):
    """
    Registra que un usuario ha ido a entrenar en una fecha real.
    Desvinculado del día de la semana para dar flexibilidad.
    """
    __tablename__ = "entrenamiento_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)

    # La fecha real en la que fue al gimnasio
    fecha = Column(DateTime, default=datetime.utcnow, index=True)

    # El día de la rutina que eligió manualmente (ej: "Día 1 - Empuje")
    nombre_rutina = Column(String, nullable=False)

    # Notas opcionales sobre cómo se sintió ese día
    notas = Column(Text, nullable=True)


class EntrenamientoSet(Base):
    """
    Registra cada serie individual dentro de una sesión de entrenamiento.
    """
    __tablename__ = "entrenamiento_sets"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("entrenamiento_sessions.id"), nullable=False, index=True)

    ejercicio_nombre = Column(String, nullable=False)

    # Datos del trackeo
    peso = Column(Float, nullable=True)     # Los kilos levantados
    reps = Column(Integer, nullable=True)   # Repeticiones logradas
    rpe = Column(Integer, nullable=True)    # Esfuerzo (RPE) del 1 al 10

    # Orden en el que se hizo la serie
    numero_serie = Column(Integer, nullable=False)