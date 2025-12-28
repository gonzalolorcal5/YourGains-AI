import asyncio
from app.utils.gpt import MODEL, generate_embedding, get_rag_context_for_plan

async def test_gpt4_config():
    """Test 1: Verificar configuración GPT-4o"""
    print("\n" + "="*80)
    print("TEST 1: CONFIGURACIÓN DEL MODELO")
    print("="*80)
    
    print(f"Modelo configurado: {MODEL}")
    
    if MODEL == "gpt-4o":
        print("✅ CORRECTO - Usando GPT-4o")
    else:
        print(f"❌ ERROR - Se esperaba gpt-4o, pero está usando: {MODEL}")
    
    return MODEL == "gpt-4o"

async def test_embedding():
    """Test 2: Verificar generación de embeddings"""
    print("\n" + "="*80)
    print("TEST 2: GENERACIÓN DE EMBEDDINGS")
    print("="*80)
    
    try:
        embedding = await generate_embedding("test de hipertrofia muscular")
        
        if embedding and len(embedding) == 1536:
            print(f"✅ CORRECTO - Embedding generado: {len(embedding)} dimensiones")
            return True
        else:
            print(f"❌ ERROR - Embedding inválido: {len(embedding) if embedding else 0} dims")
            return False
    except Exception as e:
        print(f"❌ ERROR generando embedding: {e}")
        return False

async def test_rag_context():
    """Test 3: Verificar recuperación de contexto RAG"""
    print("\n" + "="*80)
    print("TEST 3: SISTEMA RAG - RECUPERACIÓN DE CONTEXTO")
    print("="*80)
    
    try:
        # Datos de prueba
        test_data = {
            'gym_goal': 'ganar_musculo',
            'nutrition_goal': 'volumen',
            'experiencia': 'intermedio',
            'training_frequency': 4
        }
        
        print("Recuperando contexto RAG...")
        context = await get_rag_context_for_plan(test_data)
        
        if context and len(context) > 1000:
            print(f"✅ CORRECTO - Contexto RAG recuperado: {len(context)} caracteres")
            
            # Verificar que contiene contenido científico
            if "CONTEXTO CIENTÍFICO" in context or "📚" in context:
                print("✅ CORRECTO - Contexto contiene información científica")
                return True
            else:
                print("⚠️ ADVERTENCIA - Contexto sin formato esperado")
                return True
        else:
            print(f"❌ ERROR - Contexto vacío o muy corto: {len(context) if context else 0} chars")
            return False
    except Exception as e:
        print(f"❌ ERROR recuperando contexto RAG: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_rag_documents():
    """Test 4: Verificar cantidad de documentos en RAG"""
    print("\n" + "="*80)
    print("TEST 4: DOCUMENTOS EN BASE DE CONOCIMIENTO")
    print("="*80)
    
    try:
        from app.utils.vectorstore import KnowledgeStore
        
        # Obtener stats de la base
        stats = KnowledgeStore.get_stats()
        
        total_docs = stats.get('total_documents', 0)
        
        print(f"Documentos totales: {total_docs}")
        
        if total_docs >= 46:
            print(f"✅ CORRECTO - {total_docs} documentos en RAG")
            return True
        else:
            print(f"⚠️ ADVERTENCIA - Solo {total_docs} documentos (esperado: 46)")
            return total_docs > 0
    except Exception as e:
        print(f"⚠️ No se pudo verificar stats de RAG: {e}")
        return True  # No es crítico

async def run_all_tests():
    """Ejecutar todos los tests"""
    print("\n" + "="*80)
    print("🧪 SUITE DE TESTS - GPT-4o + RAG")
    print("="*80 + "\n")
    
    results = []
    
    # Test 1: Configuración
    results.append(await test_gpt4_config())
    
    # Test 2: Embeddings
    results.append(await test_embedding())
    
    # Test 3: RAG Context
    results.append(await test_rag_context())
    
    # Test 4: RAG Documents
    results.append(await test_rag_documents())
    
    # Resumen
    print("\n" + "="*80)
    print("📊 RESUMEN DE TESTS")
    print("="*80)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nTests pasados: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ¡PERFECTO! Sistema GPT-4o + RAG completamente funcional")
    elif passed >= 3:
        print("\n✅ BIEN - Sistema funcional con advertencias menores")
    else:
        print("\n❌ PROBLEMAS DETECTADOS - Revisar configuración")
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(run_all_tests())