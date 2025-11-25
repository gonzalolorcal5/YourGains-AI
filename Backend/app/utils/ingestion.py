from dotenv import load_dotenv
load_dotenv()

import os, json, glob
from .embeddings import get_embedding
from .vectorstore import KnowledgeStore

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_PATH = os.path.join(BASE_DIR, "knowledge")

REQUIRED_FIELDS = ["title","category","tags","level","goal","language","content","source"]

def ingest():
    files = glob.glob(os.path.join(KNOWLEDGE_PATH, "*.json"))
    if not files:
        print(f"No hay JSON en {KNOWLEDGE_PATH}. Crea alguno primero.")
        return
    count = 0
    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            doc = json.load(f)
        for f in REQUIRED_FIELDS:
            if f not in doc:
                raise ValueError(f"Falta '{f}' en {fp}")
        emb = get_embedding(doc["content"])
        KnowledgeStore.insert_document(
            title=doc["title"], category=doc["category"], tags=doc["tags"],
            level=doc["level"], goal=doc["goal"], language=doc["language"],
            content=doc["content"], source=doc["source"], embedding=emb,
            references=doc.get("references", [])  # ← AÑADIDO
        )
        count += 1
        print(f"✅ Documento insertado: {doc['title']} (ID: {count})")  # ← AÑADIDO (opcional, para ver progreso)
    print(f"Ingestados {count} documentos.")

if __name__ == "__main__":
    ingest()