import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def get_client() -> Client:
    """
    Retorna un cliente de Supabase autenticado.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        raise RuntimeError("❌ Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en .env")
    
    return create_client(url, key)