# app/migrations/001_add_freemium_columns.py
import os
import sqlite3
import argparse

def resolve_db_path(arg_path: str | None) -> str:
    if arg_path:
        return arg_path
    db_url = os.getenv("DATABASE_URL", "sqlite:///./gymai.db")
    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "", 1)
    return db_url

def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table});")
    cols = [row[1] for row in cur.fetchall()]
    return column in cols

def add_column_if_missing(conn: sqlite3.Connection, table: str, column_def: str):
    col_name = column_def.strip().split()[0]
    if column_exists(conn, table, col_name):
        print(f"✔ Columna '{col_name}' ya existe en '{table}'. No hago nada.")
        return
    print(f"➕ Añadiendo columna '{col_name}' a '{table}'...")
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_def};")
    print(f"✔ Columna '{col_name}' añadida.")

def main():
    parser = argparse.ArgumentParser(description="Añade columnas freemium a la tabla usuarios.")
    parser.add_argument("--db", help="Ruta al archivo .db (opcional). Ej: ./gymai.db")
    args = parser.parse_args()

    db_path = resolve_db_path(args.db)
    if not os.path.exists(db_path):
        print(f"❌ No encuentro la base de datos en: {db_path}")
        return

    print(f"🗄  Conectando a: {db_path}")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("BEGIN;")
        add_column_if_missing(conn, "usuarios", "plan_type TEXT DEFAULT 'FREE' NOT NULL")
        add_column_if_missing(conn, "usuarios", "chat_uses_free INTEGER DEFAULT 2 NOT NULL")
        conn.execute("UPDATE usuarios SET plan_type='FREE' WHERE plan_type IS NULL;")
        conn.execute("UPDATE usuarios SET chat_uses_free=2 WHERE chat_uses_free IS NULL;")
        conn.execute("UPDATE usuarios SET plan_type='PREMIUM' WHERE is_premium=1;")
        conn.commit()
        print("✅ Migración completada correctamente.")
        cur = conn.execute("PRAGMA table_info(usuarios);")
        cols = [(r[1], r[2], r[4]) for r in cur.fetchall()]
        print("📋 Esquema final de 'usuarios':")
        for name, typ, dflt in cols:
            print(f"   - {name} ({typ}) DEFAULT={dflt}")
    except Exception as e:
        conn.rollback()
        print("❌ Error en la migración. Se hizo ROLLBACK.")
        print(e)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
