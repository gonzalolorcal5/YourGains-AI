#!/usr/bin/env python3
"""
Migración 003: Añadir campos para rutina y dieta dinámica
Fecha: 2025-01-02
Descripción: Añade campos JSON para manejo dinámico de rutinas, dietas, lesiones y preferencias
"""

import sqlite3
import json
import os
from pathlib import Path

def run_migration():
    """Ejecuta la migración para añadir campos dinámicos a la tabla usuarios"""
    
    # Ruta a la base de datos
    db_path = Path(__file__).parent.parent.parent / "gymai.db"
    
    print(f"🔄 Ejecutando migración 003: Campos dinámicos rutina/dieta")
    print(f"📁 Base de datos: {db_path}")
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Verificar que la tabla usuarios existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
        if not cursor.fetchone():
            raise Exception("❌ Tabla 'usuarios' no encontrada")
        
        # Verificar que los campos no existen ya
        cursor.execute("PRAGMA table_info(usuarios)")
        columns = [column[1] for column in cursor.fetchall()]
        
        new_columns = [
            "current_routine",
            "current_diet", 
            "injuries",
            "focus_areas",
            "disliked_foods",
            "modification_history"
        ]
        
        # Añadir solo las columnas que no existen
        for column in new_columns:
            if column not in columns:
                print(f"➕ Añadiendo columna: {column}")
                
                if column == "current_routine":
                    cursor.execute("ALTER TABLE usuarios ADD COLUMN current_routine TEXT DEFAULT '{}'")
                elif column == "current_diet":
                    cursor.execute("ALTER TABLE usuarios ADD COLUMN current_diet TEXT DEFAULT '{}'")
                elif column == "injuries":
                    cursor.execute("ALTER TABLE usuarios ADD COLUMN injuries TEXT DEFAULT '[]'")
                elif column == "focus_areas":
                    cursor.execute("ALTER TABLE usuarios ADD COLUMN focus_areas TEXT DEFAULT '[]'")
                elif column == "disliked_foods":
                    cursor.execute("ALTER TABLE usuarios ADD COLUMN disliked_foods TEXT DEFAULT '[]'")
                elif column == "modification_history":
                    cursor.execute("ALTER TABLE usuarios ADD COLUMN modification_history TEXT DEFAULT '[]'")
            else:
                print(f"⏭️  Columna {column} ya existe, saltando...")
        
        # Confirmar cambios
        conn.commit()
        
        # Verificar que las columnas se añadieron correctamente
        cursor.execute("PRAGMA table_info(usuarios)")
        final_columns = [column[1] for column in cursor.fetchall()]
        
        print(f"✅ Migración completada. Columnas en tabla usuarios:")
        for col in final_columns:
            print(f"   - {col}")
        
        # Verificar que los JSON por defecto son válidos
        cursor.execute("SELECT id, current_routine, current_diet, injuries, focus_areas, disliked_foods, modification_history FROM usuarios LIMIT 1")
        result = cursor.fetchone()
        
        if result:
            print("🧪 Probando validación JSON...")
            for i, field in enumerate(['current_routine', 'current_diet', 'injuries', 'focus_areas', 'disliked_foods', 'modification_history'], 1):
                try:
                    json.loads(result[i])
                    print(f"   ✅ {field}: JSON válido")
                except json.JSONDecodeError as e:
                    print(f"   ❌ {field}: JSON inválido - {e}")
        
        conn.close()
        print("🎉 Migración 003 completada exitosamente")
        
    except Exception as e:
        print(f"❌ Error en migración: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        raise

def rollback_migration():
    """Rollback de la migración (NO SOPORTADO EN SQLITE)"""
    print("⚠️  SQLite no soporta DROP COLUMN. Rollback manual requerido.")
    print("💡 Para hacer rollback, restaurar backup de la base de datos.")

if __name__ == "__main__":
    run_migration()
