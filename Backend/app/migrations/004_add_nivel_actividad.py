#!/usr/bin/env python3
"""
Migración 004: Añadir campo nivel_actividad a tabla planes
Fecha: 2025-10-21
Descripción: Añade el campo nivel_actividad necesario para calcular correctamente
             la Tasa Metabólica Basal (TMB) y las calorías de mantenimiento.
"""

import sqlite3
import os

def run_migration():
    """
    Añade el campo nivel_actividad a la tabla planes
    """
    # Ruta a la base de datos
    db_path = os.path.join(os.path.dirname(__file__), '..', 'database.db')
    
    if not os.path.exists(db_path):
        print(f"⚠️ Base de datos no encontrada en: {db_path}")
        print("ℹ️ La columna se creará automáticamente cuando se genere un nuevo Plan")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(planes)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'nivel_actividad' in columns:
            print("✅ La columna 'nivel_actividad' ya existe en la tabla 'planes'")
            conn.close()
            return
        
        print("📝 Añadiendo columna 'nivel_actividad' a la tabla 'planes'...")
        
        # Añadir la columna con valor por defecto "moderado"
        cursor.execute("""
            ALTER TABLE planes 
            ADD COLUMN nivel_actividad VARCHAR DEFAULT 'moderado' NOT NULL
        """)
        
        conn.commit()
        print("✅ Migración 004 completada exitosamente")
        print("ℹ️ Todos los planes existentes tienen ahora nivel_actividad='moderado'")
        
        # Verificar cuántos registros se actualizaron
        cursor.execute("SELECT COUNT(*) FROM planes")
        count = cursor.fetchone()[0]
        print(f"📊 {count} planes actualizados con nivel_actividad='moderado'")
        
        conn.close()
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("✅ La columna 'nivel_actividad' ya existe")
        else:
            print(f"❌ Error en la migración: {e}")
            raise
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        raise

if __name__ == "__main__":
    print("=" * 60)
    print("MIGRACIÓN 004: Añadir nivel_actividad a planes")
    print("=" * 60)
    run_migration()

