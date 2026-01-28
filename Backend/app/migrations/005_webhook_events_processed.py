# app/migrations/005_webhook_events_processed.py
"""
Crea tabla webhook_events_processed para idempotencia de webhooks Stripe.
Evita duplicar planes cuando Stripe reenvía checkout.session.completed.
"""
import os
import sqlite3
from pathlib import Path


def resolve_db_path():
    db_url = os.getenv("DATABASE_URL", "sqlite:///./gymai.db")
    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "", 1)
    return None


def find_databases():
    """Buscar bases de datos en ubicaciones habituales."""
    base = Path(__file__).resolve().parents[2]
    candidates = [
        base / "gymai.db",
        base / "app" / "database.db",
        base / "instance" / "app.db",
        Path("gymai.db"),
    ]
    if resolve_db_path():
        candidates.insert(0, Path(resolve_db_path()))
    return [p for p in candidates if p.exists()]


def run_migration_on_db(db_path: Path) -> bool:
    print(f"  {db_path}")
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='webhook_events_processed'"
        )
        if cur.fetchone():
            print("     Tabla webhook_events_processed ya existe.")
            conn.close()
            return True
        cur.execute("""
            CREATE TABLE webhook_events_processed (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_event_id VARCHAR(255) NOT NULL UNIQUE,
                processed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute(
            "CREATE INDEX ix_webhook_events_processed_stripe_event_id ON webhook_events_processed(stripe_event_id)"
        )
        conn.commit()
        print("     Tabla webhook_events_processed creada.")
        conn.close()
        return True
    except Exception as e:
        print(f"     Error: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return False


def main():
    print("=" * 60)
    print("Migracion 005: webhook_events_processed (idempotencia)")
    print("=" * 60)
    dbs = find_databases()
    if not dbs:
        print("No se encontro ninguna base de datos.")
        return False
    ok = 0
    for path in dbs:
        if run_migration_on_db(path):
            ok += 1
    print()
    print("Migracion completada." if ok == len(dbs) else "Migracion parcial.")
    return ok == len(dbs)


if __name__ == "__main__":
    exit(0 if main() else 1)
