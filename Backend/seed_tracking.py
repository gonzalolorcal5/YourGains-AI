import os
import sys
from datetime import datetime, timedelta

# Asegurar que el script puede importar tu carpeta 'app'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Usuario, EntrenamientoSession, EntrenamientoSet

def inyectar_datos():
    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.email == "gonzalolorcal5@gmail.com").first()
        if not user:
            print("❌ Usuario no encontrado en la base de datos.")
            return

        hoy = datetime.utcnow()

        # Estructura: (dias_hacia_atras, [ (ejercicio, peso, reps, rpe) ])
        sesiones = [
            # --- SEMANA 1 (Hace 4 semanas) ---
            (28, [("Press banca", 60.0, 10, 8.0), ("Press banca", 60.0, 8, 8.5), ("Press inclinado con mancuernas", 22.0, 10, 8.0)]), # Lunes
            (27, [("Dominadas", 80.0, 8, 8.5), ("Remo con barra", 50.0, 10, 8.0)]), # Martes
            (25, [("Sentadillas", 80.0, 10, 8.0), ("Sentadillas", 80.0, 8, 8.5), ("Peso muerto", 90.0, 8, 8.0)]), # Jueves
            (24, [("Press militar", 35.0, 10, 8.0), ("Elevaciones laterales", 8.0, 12, 8.0)]), # Viernes

            # --- SEMANA 2 (Hace 3 semanas) ---
            (21, [("Press banca", 62.5, 9, 8.5), ("Press banca", 62.5, 8, 9.0), ("Press inclinado con mancuernas", 24.0, 9, 8.5)]),
            (20, [("Dominadas", 80.0, 9, 8.5), ("Remo con barra", 55.0, 9, 8.5)]),
            (18, [("Sentadillas", 85.0, 9, 8.5), ("Sentadillas", 85.0, 8, 9.0), ("Peso muerto", 95.0, 8, 8.5)]),
            (17, [("Press militar", 37.5, 9, 8.5), ("Elevaciones laterales", 10.0, 10, 8.5)]),

            # --- SEMANA 3 (Hace 2 semanas) ---
            (14, [("Press banca", 65.0, 8, 9.0), ("Press banca", 65.0, 7, 9.5), ("Press inclinado con mancuernas", 24.0, 10, 9.0)]),
            (13, [("Dominadas", 80.0, 10, 9.0), ("Remo con barra", 60.0, 8, 9.0)]),
            (11, [("Sentadillas", 90.0, 8, 9.0), ("Sentadillas", 90.0, 7, 9.5), ("Peso muerto", 100.0, 7, 9.0)]),
            (10, [("Press militar", 40.0, 8, 9.0), ("Elevaciones laterales", 10.0, 12, 9.0)]),

            # --- SEMANA 4 (Hace 1 semana - Actual) ---
            (7, [("Press banca", 67.5, 7, 9.5), ("Press banca", 67.5, 6, 9.5), ("Press inclinado con mancuernas", 26.0, 8, 9.5)]),
            (6, [("Dominadas", 80.0, 11, 9.5), ("Remo con barra", 65.0, 7, 9.5)]),
            (4, [("Sentadillas", 95.0, 6, 9.5), ("Sentadillas", 95.0, 6, 9.5), ("Peso muerto", 105.0, 6, 9.5)]),
            (3, [("Press militar", 42.5, 7, 9.5), ("Elevaciones laterales", 12.0, 10, 9.0)])
        ]

        total_sesiones = 0
        total_sets = 0

        for dias_atras, ejercicios in sesiones:
            fecha_sesion = hoy - timedelta(days=dias_atras)
            
            # Calcular volumen total de la sesión (peso * reps)
            volumen_sesion = sum([peso * reps for _, peso, reps, _ in ejercicios])
            
            # Crear la sesión padre
            nueva_sesion = EntrenamientoSession(
                user_id=user.id,
                fecha=fecha_sesion,
                duracion_minutos=45,
                volumen_total=volumen_sesion,
                completado=True
            )
            db.add(nueva_sesion)
            db.flush() # Flush nos da el ID de la sesión recién creada sin hacer un commit final

            # Añadir las series hijas a esa sesión
            orden = 1
            for nombre, peso, reps, rpe in ejercicios:
                nuevo_set = EntrenamientoSet(
                    session_id=nueva_sesion.id,
                    ejercicio=nombre,
                    peso=peso,
                    repeticiones=reps,
                    rpe=rpe,
                    orden=orden
                )
                db.add(nuevo_set)
                orden += 1
                total_sets += 1
            
            total_sesiones += 1

        db.commit()
        print(f"✅ ¡Éxito! Inyectadas {total_sesiones} sesiones y {total_sets} series para {user.email}.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error inyectando datos: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inyectar_datos()