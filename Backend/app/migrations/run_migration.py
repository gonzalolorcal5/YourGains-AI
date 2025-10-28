"""
Script para ejecutar la migración de nivel_actividad
Añade la columna a la tabla planes si no existe

Este script busca la base de datos en múltiples ubicaciones posibles.
"""
import sqlite3
import os
from pathlib import Path

def find_databases():
    """Buscar todas las bases de datos posibles"""
    base_dir = Path(__file__).parent.parent.parent
    possible_paths = [
        base_dir / 'app' / 'database.db',
        base_dir / 'instance' / 'app.db',
        base_dir / 'gymai.db',
        base_dir / 'database.db',
        Path(__file__).parent.parent / 'database.db',
    ]
    
    found = []
    for path in possible_paths:
        if path.exists():
            found.append(path)
    
    return found

def run_migration_on_db(db_path):
    """Ejecutar migración en una base de datos específica"""
    print(f"\n📂 Procesando: {db_path}")
    print("-" * 70)
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        print("🔍 Verificando estructura de la tabla planes...")
        
        # Verificar si la tabla planes existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='planes'")
        if not cursor.fetchone():
            print("⚠️ La tabla 'planes' no existe en esta base de datos")
            conn.close()
            return False
        
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(planes)")
        columns = [col[1] for col in cursor.fetchall()]
        
        print(f"📋 Columnas actuales en planes: {', '.join(columns)}")
        
        if 'nivel_actividad' in columns:
            print("✅ La columna nivel_actividad YA existe en la tabla")
            print("   No es necesario ejecutar la migración")
            conn.close()
            return True
        
        print("\n➕ La columna nivel_actividad NO existe")
        print("   Ejecutando migración...")
        
        # Añadir la columna
        cursor.execute("""
            ALTER TABLE planes 
            ADD COLUMN nivel_actividad VARCHAR NOT NULL DEFAULT 'moderado'
        """)
        
        print("✅ Columna nivel_actividad añadida exitosamente")
        
        # Actualizar registros existentes por si acaso
        cursor.execute("""
            UPDATE planes 
            SET nivel_actividad = 'moderado' 
            WHERE nivel_actividad IS NULL OR nivel_actividad = ''
        """)
        
        rows_updated = cursor.rowcount
        
        # Confirmar cambios
        conn.commit()
        
        print(f"✅ Actualizados {rows_updated} registros existentes con valor 'moderado'")
        
        # Verificar que se aplicó correctamente
        cursor.execute("PRAGMA table_info(planes)")
        columns_after = [col[1] for col in cursor.fetchall()]
        
        if 'nivel_actividad' in columns_after:
            print("\n✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
            
            # Contar registros
            cursor.execute("SELECT COUNT(*) FROM planes")
            total_count = cursor.fetchone()[0]
            print(f"📊 Total de planes en BD: {total_count}")
            
            conn.close()
            return True
        else:
            print("\n❌ ERROR: La columna no se añadió correctamente")
            conn.close()
            return False
            
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("✅ La columna ya existe (error esperado si se ejecuta dos veces)")
            conn.close()
            return True
        else:
            print(f"❌ ERROR SQLite: {e}")
            try:
                conn.rollback()
            except:
                pass
            conn.close()
            return False
            
    except Exception as e:
        print(f"❌ ERROR inesperado: {e}")
        import traceback
        print(traceback.format_exc())
        try:
            conn.rollback()
        except:
            pass
        conn.close()
        return False


def main():
    print("="*70)
    print("🚀 EJECUTANDO MIGRACIÓN: Añadir campo nivel_actividad")
    print("="*70)
    print()
    
    # Buscar todas las bases de datos
    print("🔍 Buscando bases de datos...")
    databases = find_databases()
    
    if not databases:
        print("❌ No se encontró ninguna base de datos")
        print("\nUbicaciones verificadas:")
        base_dir = Path(__file__).parent.parent.parent
        print(f"  - {base_dir / 'app' / 'database.db'}")
        print(f"  - {base_dir / 'instance' / 'app.db'}")
        print(f"  - {base_dir / 'gymai.db'}")
        print(f"  - {base_dir / 'database.db'}")
        return False
    
    print(f"✅ Se encontraron {len(databases)} base(s) de datos:")
    for db in databases:
        print(f"  📁 {db}")
    print()
    
    # Ejecutar migración en todas las bases de datos encontradas
    success_count = 0
    for db_path in databases:
        if run_migration_on_db(db_path):
            success_count += 1
    
    print()
    print("="*70)
    if success_count == len(databases):
        print("✅ MIGRACIÓN EXITOSA EN TODAS LAS BASES DE DATOS")
        print(f"   {success_count}/{len(databases)} bases de datos actualizadas")
        print()
        print("📝 SIGUIENTE PASO:")
        print("   Reinicia el servidor backend si está corriendo:")
        print("   - Presiona Ctrl+C en la terminal del servidor")
        print("   - Ejecuta: python Backend/app/main.py")
        return True
    else:
        print(f"⚠️ MIGRACIÓN PARCIAL")
        print(f"   {success_count}/{len(databases)} bases de datos actualizadas exitosamente")
        print("   Revisa los errores arriba")
        return False
    print("="*70)


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

