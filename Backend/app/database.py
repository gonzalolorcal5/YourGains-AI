from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv
import os
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/gymai.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 👉 Base canónica de TODO el proyecto
Base = declarative_base()

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 👇 Importa los modelos para que se registren en el metadata
from app import models  # NO importes Base desde models, importas los modelos

# Crea tablas si no existen
Base.metadata.create_all(bind=engine)

# Log para confirmar ruta de la BD
db_path = DATABASE_URL.replace("sqlite:///", "")
logger.info(f"🔍 Base de datos configurada en: {db_path}")
if "/data/" in db_path:
    logger.info("✅ BD está en volumen persistente de Railway")
else:
    logger.warning("⚠️ ADVERTENCIA: BD NO está en volumen persistente, los datos se perderán en restarts")
