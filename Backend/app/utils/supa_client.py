"""
Cliente HTTP ligero para Supabase - Sin dependencias del SDK completo.
Usa solo requests para mayor estabilidad en Railway.
"""
import os
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class SupabaseClient:
    """
    Cliente HTTP simple para Supabase REST API.
    Reemplaza el SDK oficial para evitar problemas de dependencias.
    """
    
    def __init__(self, url: str, key: str):
        self.url = url.rstrip('/')
        self.key = key
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
    
    def table(self, table_name: str):
        """Retorna un TableClient para operaciones en una tabla."""
        return TableClient(self, table_name)
    
    def rpc(self, function_name: str, params: Dict[str, Any]):
        """Ejecuta una función RPC en Supabase."""
        return RPCClient(self, function_name, params)


class TableClient:
    """Cliente para operaciones en tablas de Supabase."""
    
    def __init__(self, client: SupabaseClient, table_name: str):
        self.client = client
        self.table_name = table_name
    
    def insert(self, data: Dict[str, Any]):
        """Inserta datos en la tabla."""
        self.data = data
        return self
    
    def execute(self):
        """Ejecuta la inserción."""
        url = f"{self.client.url}/rest/v1/{self.table_name}"
        
        try:
            response = requests.post(
                url,
                headers=self.client.headers,
                json=self.data,
                timeout=30
            )
            response.raise_for_status()
            
            return SupabaseResponse(data=response.json())
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Error en insert: {e}")
            return SupabaseResponse(data=[])


class RPCClient:
    """Cliente para llamadas RPC a funciones de Supabase."""
    
    def __init__(self, client: SupabaseClient, function_name: str, params: Dict[str, Any]):
        self.client = client
        self.function_name = function_name
        self.params = params
    
    def execute(self):
        """Ejecuta la función RPC."""
        url = f"{self.client.url}/rest/v1/rpc/{self.function_name}"
        
        try:
            response = requests.post(
                url,
                headers=self.client.headers,
                json=self.params,
                timeout=30
            )
            response.raise_for_status()
            
            return SupabaseResponse(data=response.json())
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Error en RPC {self.function_name}: {e}")
            return SupabaseResponse(data=[])


class SupabaseResponse:
    """Wrapper para respuestas de Supabase."""
    
    def __init__(self, data):
        self.data = data


def get_client() -> SupabaseClient:
    """
    Retorna un cliente de Supabase autenticado.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        raise RuntimeError("❌ Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en .env")
    
    return SupabaseClient(url, key)