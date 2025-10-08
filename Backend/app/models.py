from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Stripe / gating
    is_premium = Column(Boolean, default=False, nullable=False)
    stripe_customer_id = Column(String, nullable=True)

    # NUEVO: plan y cupo de chat
    plan_type = Column(String, default="FREE", nullable=False)   # FREE | PREMIUM
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

    planes = relationship("Plan", back_populates="usuario")


class Plan(Base):
    __tablename__ = "planes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuarios.id"))

    altura = Column(Integer, nullable=False)
    peso = Column(String, nullable=False)
    edad = Column(Integer, nullable=False)
    sexo = Column(String, nullable=False)
    experiencia = Column(String, nullable=False)
    objetivo = Column(String, nullable=False)
    materiales = Column(String, nullable=False)
    tipo_cuerpo = Column(String, nullable=True)
    idioma = Column(String, default="es")
    puntos_fuertes = Column(String, nullable=True)
    puntos_debiles = Column(String, nullable=True)
    entrenar_fuerte = Column(String, nullable=True)
    lesiones = Column(String, nullable=True)
    alergias = Column(String, nullable=True)
    restricciones_dieta = Column(String, nullable=True)

    rutina = Column(Text, nullable=False)
    dieta = Column(Text, nullable=False)
    motivacion = Column(Text, nullable=False)

    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="planes")
