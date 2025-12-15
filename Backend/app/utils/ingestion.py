import os
import json
import requests
import tiktoken  # Necesario para contar tokens reales
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Cargar variables
load_dotenv()

# Configuración
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL") # Asegúrate que sea: https://whxrphlxuopjkpvagrjf.supabase.co
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# --- FUNCIÓN CRÍTICA: TRUNCADO SEGURO ---
def truncate_text_safe(text: str, max_tokens: int = 8000) -> str:
    """Corta el texto basándose en tokens reales, no en caracteres."""
    try:
        encoding = tiktoken.get_encoding("cl100k_base") # Encoding de GPT-4/Embeddings-3
    except:
        encoding = tiktoken.get_encoding("cl100k_base")
    
    tokens = encoding.encode(text)
    
    if len(tokens) > max_tokens:
        print(f"   ✂️ Texto muy largo ({len(tokens)} tokens). Recortando a {max_tokens}...")
        tokens = tokens[:max_tokens]
        return encoding.decode(tokens)
    return text

def generate_embedding(text: str) -> list:
    # Usamos el truncado seguro
    safe_text = truncate_text_safe(text, max_tokens=8100) # Dejamos un margen pequeño (límite 8191)
    
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=safe_text
    )
    return response.data[0].embedding

def insert_document(doc_data: dict) -> bool:
    """Inserta en Supabase usando la URL estándar (sin IP directa)"""
    url = f"{SUPABASE_URL}/rest/v1/knowledge_base"
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    try:
        # verify=True es lo correcto. Si falla DNS, cambia tus DNS de Windows a 8.8.8.8
        response = requests.post(url, headers=headers, json=doc_data, timeout=20)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")
        return False

def process_json_file(file_path: Path) -> dict:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Combinar título y contenido
    full_text = f"{data.get('title', '')}\n\n{data.get('content', '')}"
    
    print(f"   🧠 Generando embedding...")
    embedding = generate_embedding(full_text)
    
    doc_data = {
        "title": data.get("title", ""),
        "content": data.get("content", ""),
        "category": data.get("category", "general"),
        "subcategory": data.get("subcategory", ""),
        "tags": data.get("tags", []),
        "studies": data.get("studies", []),
        "embedding": embedding
    }
    return doc_data

def main():
    knowledge_dir = Path("app/knowledge")
    json_files = list(knowledge_dir.glob("*.json"))
    
    print(f"\n🚀 Iniciando ingestión de {len(json_files)} archivos")
    print(f"📡 Destino: {SUPABASE_URL}\n")
    
    success, failed = 0, 0
    
    for idx, file_path in enumerate(json_files, 1):
        print(f"[{idx}/{len(json_files)}] Procesando: {file_path.name}")
        try:
            doc_data = process_json_file(file_path)
            if insert_document(doc_data):
                print("   ✅ Guardado correctamente\n")
                success += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   ❌ Error grave: {e}\n")
            failed += 1
            
    print(f"🏁 Terminado: {success} OK | {failed} Fallos")

if __name__ == "__main__":
    main()