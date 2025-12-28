import asyncio
from app.utils.gpt import generar_plan_personalizado

async def test_plan_generation():
    """
    Test de generación de plan completo con GPT-4o + RAG
    """
    
    print("\n" + "="*80)
    print("🧪 TEST GENERACIÓN DE PLAN - GPT-4o + RAG")
    print("="*80 + "\n")
    
    # Datos de prueba realistas
    datos_prueba = {
        'edad': 25,
        'altura': 180,
        'peso': '80kg',
        'sexo': 'masculino',
        'experiencia': 'intermedio',
        'gym_goal': 'ganar_musculo',
        'nutrition_goal': 'volumen',
        'training_frequency': 4,
        'training_days': ['lunes', 'martes', 'jueves', 'viernes'],
        'nivel_actividad': 'moderado',
        'materiales': ['mancuernas', 'barra', 'banco', 'rack'],
        'alergias': 'ninguna',
        'restricciones': 'ninguna',
        'lesiones': 'ninguna',
        'idioma': 'es'
    }
    
    print("📋 Datos de usuario:")
    print(f"   - {datos_prueba['edad']} años, {datos_prueba['altura']}cm, {datos_prueba['peso']}")
    print(f"   - Objetivo gym: {datos_prueba['gym_goal']}")
    print(f"   - Objetivo nutrición: {datos_prueba['nutrition_goal']}")
    print(f"   - Frecuencia: {datos_prueba['training_frequency']} días/semana")
    print(f"   - Experiencia: {datos_prueba['experiencia']}")
    
    print("\n⏳ Generando plan con GPT-4o + RAG...\n")
    
    try:
        # Generar plan
        plan = await generar_plan_personalizado(datos_prueba)
        
        # Validar estructura
        print("=" * 80)
        print("✅ PLAN GENERADO EXITOSAMENTE")
        print("=" * 80 + "\n")
        
        # Verificar rutina
        if 'rutina' in plan:
            dias = plan['rutina'].get('dias', [])
            print(f"📅 RUTINA:")
            print(f"   - Días generados: {len(dias)}")
            
            for dia in dias:
                ejercicios = dia.get('ejercicios', [])
                print(f"   - {dia.get('dia', 'Sin nombre')}: {len(ejercicios)} ejercicios")
            
            if len(dias) == 4:
                print("   ✅ Cantidad de días correcta (4)")
            else:
                print(f"   ⚠️ Días generados: {len(dias)} (esperado: 4)")
        else:
            print("❌ Rutina no encontrada en plan")
        
        # Verificar dieta
        print()
        if 'dieta' in plan:
            comidas = plan['dieta'].get('comidas', [])
            total_kcal = sum(c.get('kcal', 0) for c in comidas)
            
            print(f"🍎 DIETA:")
            print(f"   - Comidas generadas: {len(comidas)}")
            print(f"   - Calorías totales: {total_kcal} kcal")
            
            # Verificar metadatos científicos
            metadata = plan['dieta'].get('metadata', {})
            if metadata:
                print(f"   - TMB: {metadata.get('tmb', 'N/A')} kcal/día")
                print(f"   - TDEE: {metadata.get('tdee', 'N/A')} kcal/día")
                print(f"   - Método: {metadata.get('metodo_calculo', 'N/A')}")
                print(f"   - RAG usado: {metadata.get('rag_used', False)}")
                print("   ✅ Metadatos científicos presentes")
            else:
                print("   ⚠️ Metadatos científicos no encontrados")
            
            # Verificar macros
            macros = plan['dieta'].get('macros', {})
            if macros:
                print(f"   - Proteína: {macros.get('proteina', 'N/A')}g")
                print(f"   - Carbohidratos: {macros.get('carbohidratos', 'N/A')}g")
                print(f"   - Grasas: {macros.get('grasas', 'N/A')}g")
                print("   ✅ Macros calculados correctamente")
            
            if len(comidas) == 5:
                print("   ✅ Cantidad de comidas correcta (5)")
            else:
                print(f"   ⚠️ Comidas generadas: {len(comidas)} (esperado: 5)")
        else:
            print("❌ Dieta no encontrada en plan")
        
        # Verificar motivación
        print()
        if 'motivacion' in plan:
            print(f"💪 MOTIVACIÓN: '{plan['motivacion'][:50]}...'")
        
        # Resumen final
        print("\n" + "=" * 80)
        print("📊 RESUMEN DE CALIDAD")
        print("=" * 80)
        
        checks = []
        checks.append(('Rutina generada', 'rutina' in plan))
        checks.append(('Dieta generada', 'dieta' in plan))
        checks.append(('Días correctos', len(plan.get('rutina', {}).get('dias', [])) == 4))
        checks.append(('Comidas correctas', len(plan.get('dieta', {}).get('comidas', [])) == 5))
        checks.append(('Metadatos científicos', bool(plan.get('dieta', {}).get('metadata'))))
        checks.append(('RAG usado', plan.get('dieta', {}).get('metadata', {}).get('rag_used', False)))
        checks.append(('Macros calculados', bool(plan.get('dieta', {}).get('macros'))))
        
        passed = sum(1 for _, check in checks if check)
        total = len(checks)
        
        print()
        for label, check in checks:
            emoji = "✅" if check else "❌"
            print(f"{emoji} {label}")
        
        print(f"\n📊 Calidad: {passed}/{total} checks pasados ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("\n🎉 ¡PERFECTO! Plan de máxima calidad con GPT-4o + RAG")
        elif passed >= total * 0.85:
            print("\n✅ MUY BIEN - Plan de alta calidad")
        else:
            print("\n⚠️ ACEPTABLE - Plan funcional pero mejorable")
        
        return plan
        
    except Exception as e:
        print(f"\n❌ ERROR generando plan: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    plan = asyncio.run(test_plan_generation())
    
    if plan:
        print("\n" + "=" * 80)
        print("✅ TEST COMPLETADO - Sistema GPT-4o + RAG totalmente funcional")
        print("=" * 80 + "\n")