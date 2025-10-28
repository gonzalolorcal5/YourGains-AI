"""
Verificar que la migración de nivel_actividad se aplicó correctamente
"""
import sqlite3
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

def verify_db(db_path):
    """Verificar una base de datos específica"""
    print(f"\n📂 Verificando BD: {db_path}")
    print("-" * 70)
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Verificar si la tabla planes existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='planes'")
        if not cursor.fetchone():
            print("⚠️ La tabla 'planes' no existe en esta base de datos")
            conn.close()
            return False
        
        # Obtener estructura de la tabla
        cursor.execute("PRAGMA table_info(planes)")
        columns = cursor.fetchall()
        
        print("\n📋 ESTRUCTURA DE LA TABLA 'planes':")
        print("-" * 70)
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            not_null = "NOT NULL" if col[3] else "NULL"
            default = col[4] if col[4] else "None"
            
            # Destacar nivel_actividad
            if col_name == 'nivel_actividad':
                print(f"  ✅ {col_name:20s} | {col_type:10s} | {not_null:8s} | Default: {default}")
            else:
                print(f"     {col_name:20s} | {col_type:10s} | {not_null:8s} | Default: {default}")
        print("-" * 70)
        
        # Buscar específicamente nivel_actividad
        cursor.execute("PRAGMA table_info(planes)")
        nivel_actividad_exists = any(col[1] == 'nivel_actividad' for col in cursor.fetchall())
        
        if nivel_actividad_exists:
            print("\n✅ La columna 'nivel_actividad' EXISTE")
            
            # Mostrar algunos registros
            cursor.execute("SELECT COUNT(*) FROM planes")
            count = cursor.fetchone()[0]
            print(f"📊 Total de planes en BD: {count}")
            
            if count > 0:
                cursor.execute("SELECT id, nivel_actividad FROM planes LIMIT 5")
                print("\n📋 Primeros 5 registros:")
                for row in cursor.fetchall():
                    print(f"  Plan ID {row[0]}: nivel_actividad = '{row[1]}'")
            
            conn.close()
            return True
        else:
            print("\n❌ La columna 'nivel_actividad' NO EXISTE")
            print("   Ejecuta: python -m app.migrations.run_migration")
            conn.close()
            return False
            
    except Exception as e:
        print(f"❌ Error verificando BD: {e}")
        import traceback
        print(traceback.format_exc())
        try:
            conn.close()
        except:
            pass
        return False


def main():
    print("="*70)
    print("🔍 VERIFICACIÓN DE MIGRACIÓN: nivel_actividad")
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
    
    # Verificar cada base de datos
    success_count = 0
    for db_path in databases:
        if verify_db(db_path):
            success_count += 1
    
    print()
    print("="*70)
    if success_count == len(databases):
        print("✅ VERIFICACIÓN EXITOSA EN TODAS LAS BASES DE DATOS")
        print(f"   {success_count}/{len(databases)} bases de datos tienen la columna")
        print("\n✅ TODO ESTÁ CORRECTO - Puedes continuar con el onboarding")
    elif success_count > 0:
        print(f"⚠️ VERIFICACIÓN PARCIAL")
        print(f"   {success_count}/{len(databases)} bases de datos tienen la columna")
        print("\n📝 Acción requerida:")
        print("   Ejecuta: python -m app.migrations.run_migration")
    else:
        print("❌ VERIFICACIÓN FALLIDA")
        print("   Ninguna base de datos tiene la columna nivel_actividad")
        print("\n📝 Acción requerida:")
        print("   Ejecuta: python -m app.migrations.run_migration")
    print("="*70)
    
    return success_count == len(databases)


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

