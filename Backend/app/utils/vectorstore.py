from typing import List, Optional, Dict, Any
from .supa_client import get_client

class KnowledgeStore:
    """
    Gestor de la base de conocimiento usando Supabase HTTP SDK.
    """
    
    @staticmethod
    def insert_document(
        title: str,
        category: str,
        tags: List[str],
        level: str,
        goal: List[str],
        language: str,
        content: str,
        source: str,
        embedding: List[float],
        references: Optional[List[Dict[str, Any]]] = None  # ← AÑADIDO
    ) -> int:
        """
        Inserta un documento con su embedding en knowledge_base.
        Retorna el ID del documento insertado o -1 si falla.
        """
        sb = get_client()
        
        data = {
            "title": title,
            "category": category,
            "tags": tags,
            "level": level,
            "goal": goal,
            "language": language,
            "content": content,
            "source": source,
            "embedding": embedding,
            "references": references or []  # ← AÑADIDO
        }
        
        try:
            res = sb.table("knowledge_base").insert(data).execute()
            
            if res.data and len(res.data) > 0 and "id" in res.data[0]:
                return int(res.data[0]["id"])
            
            return -1
        
        except Exception as e:
            print(f"❌ Error insertando documento: {e}")
            return -1
    
    @staticmethod
    def search(
        query_embedding: List[float],
        k: int = 5,
        language: Optional[str] = None,
        category: Optional[str] = None,
        goal: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca documentos similares usando la función RPC match_knowledge.
        
        Args:
            query_embedding: Vector de embeddings de la query
            k: Número de resultados a retornar
            language: Filtro opcional por idioma
            category: Filtro opcional por categoría
            goal: Filtro opcional por objetivo (no implementado en RPC aún)
        
        Returns:
            Lista de documentos ordenados por similitud
        """
        sb = get_client()
        
        params = {
            "query_embedding": query_embedding,
            "match_count": k,
            "filter_lang": language,
            "filter_category": category
        }
        
        try:
            res = sb.rpc("match_knowledge", params).execute()
            return res.data or []
        
        except Exception as e:
            print(f"❌ Error buscando documentos: {e}")
            return []