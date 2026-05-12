import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Usuario, EntrenamientoSession, EntrenamientoSet

def inyectar_datos():
    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.email == "gonzalolorcal5@gmail.com").first()
        if not user:
            print("❌ Usuario no encontrado.")
            return

        hoy = datetime.now(timezone.utc)
        
        sesiones = [
            (28, [("Press banca", 60.0, 10, 8.0), ("Sentadillas", 80.0, 10, 8.0)]),
            (21, [("Press banca", 62.5, 9, 8.5), ("Sentadillas", 85.0, 9, 8.5)]),
            (14, [("Press banca", 65.0, 8, 9.0), ("Sentadillas", 90.0, 8, 9.0)]),
            (7,  [("Press banca", 67.5, 7, 9.5), ("Sentadillas", 95.0, 6, 9.5)])
        ]

        total_sesiones = 0
        total_sets = 0

        for dias_atras, ejercicios in sesiones:
            nueva_sesion = EntrenamientoSession(
                user_id=user.id,
                fecha=hoy - timedelta(days=dias_atras),
                nombre_rutina="Rutina Simulada"
            )
            db.add(nueva_sesion)
            db.flush() 

            numero_serie = 1
            for nombre, peso, reps, rpe in ejercicios:
                nuevo_set = EntrenamientoSet(
                    session_id=nueva_sesion.id,
                    ejercicio_nombre=nombre,
                    peso=peso,
                    reps=reps,
                    rpe=rpe,
                    numero_serie=numero_serie
                )
                db.add(nuevo_set)
                numero_serie += 1
                total_sets += 1
            
            total_sesiones += 1

        db.commit()
        print(f"✅ ¡Éxito! Inyectadas {total_sesiones} sesiones y {total_sets} series.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error inyectando datos: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inyectar_datos()