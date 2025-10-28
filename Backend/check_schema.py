import sqlite3

def check_database_schema():
    conn = sqlite3.connect('gymai.db')
    cursor = conn.cursor()
    
    print("="*70)
    print("📊 ESQUEMA DE BASE DE DATOS")
    print("="*70)
    
    # Tabla usuarios
    print("\n🔍 TABLA USUARIOS:")
    print("-" * 50)
    cursor.execute('PRAGMA table_info(usuarios)')
    usuarios_cols = cursor.fetchall()
    for row in usuarios_cols:
        col_name = row[1]
        col_type = row[2]
        not_null = "NOT NULL" if row[3] else "NULL"
        default = row[4] if row[4] else "None"
        print(f"  {col_name:20s} | {col_type:10s} | {not_null:8s} | Default: {default}")
    
    # Tabla planes
    print("\n🔍 TABLA PLANES:")
    print("-" * 50)
    cursor.execute('PRAGMA table_info(planes)')
    planes_cols = cursor.fetchall()
    for row in planes_cols:
        col_name = row[1]
        col_type = row[2]
        not_null = "NOT NULL" if row[3] else "NULL"
        default = row[4] if row[4] else "None"
        print(f"  {col_name:20s} | {col_type:10s} | {not_null:8s} | Default: {default}")
    
    # Relaciones
    print("\n🔗 RELACIONES:")
    print("-" * 50)
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='planes'")
    planes_sql = cursor.fetchone()[0]
    if "FOREIGN KEY" in planes_sql:
        print("  planes.user_id → usuarios.id (FK)")
    else:
        print("  ❌ No se encontró FK definida")
    
    # Índices
    print("\n📇 ÍNDICES:")
    print("-" * 50)
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index'")
    indices = cursor.fetchall()
    for idx_name, idx_sql in indices:
        if idx_name.startswith('sqlite_'):
            continue
        print(f"  {idx_name}: {idx_sql}")
    
    conn.close()

if __name__ == "__main__":
    check_database_schema()
