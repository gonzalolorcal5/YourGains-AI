import sqlite3
import os

print("\n" + "=" * 80)
print("AUDITORÍA DE ESQUEMAS")
print("=" * 80)

# ===== SQLITE LOCAL =====
print("\n[1/2] SQLITE LOCAL - gymai.db")
print("-" * 80)

conn = sqlite3.connect('gymai.db')
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(usuarios)")
local_cols = cursor.fetchall()

print(f"\n{'#':<4} {'Columna':<35} {'Tipo':<15}")
print("-" * 56)
for col in local_cols:
    print(f"{col[0]:<4} {col[1]:<35} {col[2]:<15}")

print(f"\nTotal: {len(local_cols)} columnas")
conn.close()

# ===== POSTGRESQL RAILWAY =====
print("\n\n[2/2] POSTGRESQL RAILWAY")
print("-" * 80)

os.environ["DATABASE_URL"] = "postgresql://postgres:ciiIZQTRDvRlPNJMUrdbobUDFWTqMIyN@crossover.proxy.rlwy.net:23493/railway"

try:
    from sqlalchemy import create_engine, text
    engine = create_engine(os.environ["DATABASE_URL"], connect_args={"connect_timeout": 10})
    
    with engine.connect() as conn:
        result = conn.execute(text('''
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'usuarios'
            ORDER BY ordinal_position
        '''))
        
        prod_cols = result.fetchall()
        
        print(f"\n{'Columna':<35} {'Tipo':<20} {'Nullable'}")
        print("-" * 62)
        for col in prod_cols:
            print(f"{col[0]:<35} {col[1]:<20} {col[2]}")
        
        print(f"\nTotal: {len(prod_cols)} columnas")
    
    # ===== COMPARACIÓN =====
    print("\n\n" + "=" * 80)
    print("DIFERENCIAS")
    print("=" * 80)
    
    local_names = {col[1] for col in local_cols}
    prod_names = {col[0] for col in prod_cols}
    
    missing = prod_names - local_names
    
    if missing:
        print(f"\n❌ FALTAN EN LOCAL ({len(missing)}):")
        for col_name in sorted(missing):
            col_info = [c for c in prod_cols if c[0] == col_name][0]
            print(f"   {col_name:<35} | {col_info[1]:<20} | Nullable: {col_info[2]}")
    else:
        print("\n✅ Todas las columnas están presentes")
    
    print("\n" + "=" * 80)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nRailway no accesible desde tu red.")
