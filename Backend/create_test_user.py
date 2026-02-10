# Backend/create_test_user.py
"""
Script para crear usuario de prueba en base de datos local
"""
import sys
import os

# Asegurar que Backend es el cwd para imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Forzar entorno local para que init_db cree tablas (si no está ya en .env)
if not os.getenv("ENVIRONMENT"):
    os.environ["ENVIRONMENT"] = "local"

from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db
from app.models import Usuario
from app.auth_utils import get_password_hash


def create_test_user():
    """Crear usuario de prueba para desarrollo local"""

    # Inicializar base de datos
    init_db()

    # Crear sesión
    db: Session = SessionLocal()

    try:
        # Verificar si ya existe
        existing = db.query(Usuario).filter(Usuario.email == "test@yourgains.local").first()
        if existing:
            print("⚠️  Usuario de prueba ya existe")
            print(f"   Email: {existing.email}")
            print(f"   Plan: {existing.plan_type}")
            return

        # Crear usuario
        test_user = Usuario(
            email="test@yourgains.local",
            hashed_password=get_password_hash("test123"),
            plan_type="PREMIUM",  # O "FREE"
            is_premium=True,      # O False
            onboarding_completed=True
        )

        db.add(test_user)
        db.commit()
        db.refresh(test_user)

        print("✅ Usuario de prueba creado")
        print(f"   Email: {test_user.email}")
        print(f"   Password: test123")
        print(f"   Plan: {test_user.plan_type}")
        print(f"   ID: {test_user.id}")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_test_user()
