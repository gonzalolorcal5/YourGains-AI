# Backend/app/database.py
"""
Configuración de base de datos con soporte para SQLite (local) y PostgreSQL (producción)
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Obtener URL de base de datos
DATABASE_URL = os.getenv("DATABASE_URL")

print(f"🔧 [DATABASE] Entorno: {os.getenv('ENVIRONMENT', 'desconocido')}")
print(f"🔧 [DATABASE] Conectando a: {(DATABASE_URL[:30] + '...') if DATABASE_URL else 'None'}")

# ══════════════════════════════════════════════════════════════════
# Configurar engine según el tipo de base de datos
# ══════════════════════════════════════════════════════════════════

if DATABASE_URL and DATABASE_URL.startswith("sqlite"):
    # ✅ SQLite LOCAL - Para desarrollo
    print("✅ [DATABASE] Modo: SQLite LOCAL")
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # Necesario para SQLite con FastAPI
        echo=False  # True para ver queries SQL en consola
    )

elif DATABASE_URL and DATABASE_URL.startswith("postgresql"):
    # ✅ PostgreSQL RAILWAY - Para producción
    print("✅ [DATABASE] Modo: PostgreSQL RAILWAY")
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Verificar conexiones antes de usarlas
        pool_size=10,        # Conexiones simultáneas
        max_overflow=20,     # Conexiones extra si se necesitan
        pool_recycle=3600,   # Reciclar conexiones cada hora
        echo=False
    )

else:
    # ❌ ERROR - No hay DATABASE_URL configurada
    raise ValueError(
        "❌ DATABASE_URL no configurada o formato inválido\n"
        "Debe empezar con 'sqlite:///' o 'postgresql://'"
    )

# ══════════════════════════════════════════════════════════════════
# Crear sesión y base
# ══════════════════════════════════════════════════════════════════

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """
    Dependency para obtener sesión de base de datos.
    Se usa en endpoints FastAPI con Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════
# Crear tablas automáticamente (solo en desarrollo)
# ══════════════════════════════════════════════════════════════════

def init_db():
    """
    Crear todas las tablas si no existen.
    SOLO se ejecuta en local, en producción usar Alembic migrations.
    """
    from app.models import Usuario, Plan, BodyScan, ProcessedWebhookEvent  # Importar TODOS los modelos

    if os.getenv("ENVIRONMENT") == "local":
        print("🔧 [DATABASE] Creando tablas locales...")
        Base.metadata.create_all(bind=engine)
        print("✅ [DATABASE] Tablas creadas correctamente")
    else:
        print("⚠️  [DATABASE] Modo producción - No se crean tablas automáticamente")


# Llamar init_db al importar el módulo (solo en local)
if os.getenv("ENVIRONMENT") == "local":
    init_db()
