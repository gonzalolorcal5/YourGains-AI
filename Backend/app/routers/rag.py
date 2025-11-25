from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.utils.embeddings import get_embedding
from app.utils.vectorstore import KnowledgeStore

router = APIRouter(prefix="/rag", tags=["RAG"])

class RAGQuery(BaseModel):
    query: str
    language: Optional[str] = "es"
    category: Optional[str] = None
    k: int = 3

class Reference(BaseModel):
    title: str
    authors: str
    year: int
    url: str

class RAGResult(BaseModel):
    id: int
    title: str
    category: str
    level: str
    content: str
    similarity: float
    references: List[Reference]

class RAGResponse(BaseModel):
    results: List[RAGResult]
    context: str

@router.post("/query", response_model=RAGResponse)
async def query_knowledge(req: RAGQuery):
    """
    Consulta la base de conocimiento usando RAG.
    
    - Genera embedding de la query
    - Busca documentos similares
    - Retorna contexto enriquecido con referencias científicas
    """
    try:
        # Generar embedding de la query
        query_embedding = get_embedding(req.query)
        
        # Buscar documentos similares
        results = KnowledgeStore.search(
            query_embedding=query_embedding,
            k=req.k,
            language=req.language,
            category=req.category
        )
        
        if not results:
            return RAGResponse(results=[], context="")
        
        # Construir contexto con referencias
        context_parts = []
        formatted_results = []
        
        for i, doc in enumerate(results, 1):
            # Construir contexto textual
            context_parts.append(
                f"[Documento {i}: {doc['title']}]\n"
                f"Categoría: {doc['category']}\n"
                f"Nivel: {doc['level']}\n"
                f"Contenido: {doc['content']}\n"
                f"Similitud: {doc['similarity']:.3f}\n"
            )
            
            # Si hay referencias, añadirlas al contexto
            if doc.get('references') and len(doc['references']) > 0:
                context_parts.append("Referencias científicas:")
                for ref in doc['references']:
                    context_parts.append(f"- {ref['authors']} ({ref['year']}): {ref['title']}")
                    context_parts.append(f"  {ref['url']}")
            
            # Formatear resultado
            formatted_results.append(RAGResult(
                id=doc['id'],
                title=doc['title'],
                category=doc['category'],
                level=doc['level'],
                content=doc['content'],
                similarity=doc['similarity'],
                references=[Reference(**ref) for ref in doc.get('references', [])]
            ))
        
        context = "\n---\n".join(context_parts)
        
        return RAGResponse(results=formatted_results, context=context)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en RAG: {str(e)}")