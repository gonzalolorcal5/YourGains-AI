# 🔍 ANÁLISIS: Integrar RAG en Modificaciones de Planes

**Fecha:** 2024  
**Objetivo:** Analizar si es posible y seguro integrar RAG cuando GPT genera planes por modificaciones (lesiones, cambios de objetivo, etc.)

---

## ✅ CONCLUSIÓN PREVIA

**SÍ ES POSIBLE** y **RECOMENDABLE**, pero con precauciones. El RAG ya se está usando para generación de planes nuevos, pero **NO está optimizado para modificaciones específicas**.

---

## 📊 ESTADO ACTUAL

### 1. Cómo funcionan las modificaciones

#### **Handler de Lesiones** (`handle_modify_routine_injury`)
- **Ubicación:** `Backend/app/utils/function_handlers_optimized.py:70`
- **Llamada a GPT:** Línea 143 → `await generar_plan_personalizado(datos_gpt)`
- **Datos que se pasan:**
  ```python
  datos_gpt = {
      # ... datos del plan actual ...
      'lesiones': f"{body_part} ({injury_type}, severidad: {severity}) - EVITAR ejercicios que afecten esta parte",
      # ...
  }
  ```
- **Estado RAG:** ✅ **SÍ se consulta RAG**, pero con queries genéricas (no específicas para lesiones)

#### **Handler de Enfoque** (`handle_modify_routine_focus`)
- **Ubicación:** `Backend/app/utils/function_handlers_optimized.py:1190`
- **Llamada a GPT:** Línea 1271 → `await generar_plan_personalizado(datos_gpt)`
- **Datos que se pasan:**
  ```python
  datos_gpt = {
      # ... datos del plan actual ...
      'focus_area': mapped_focus_area,  # ej: "brazos", "piernas"
      'increase_frequency': increase_frequency,
      'volume_change': volume_change
  }
  ```
- **Estado RAG:** ✅ **SÍ se consulta RAG**, pero con queries genéricas (no específicas para enfoque)

#### **Handler de Macros** (`handle_recalculate_macros`)
- **Ubicación:** `Backend/app/utils/function_handlers_optimized.py:523`
- **Llamada a GPT:** ❌ **NO llama a GPT** - Solo recalcula macros matemáticamente
- **Estado RAG:** ❌ **NO aplica** (no genera plan nuevo)

### 2. Qué hace el RAG actualmente

**Función:** `get_rag_context_for_plan()` en `Backend/app/utils/gpt.py:73`

**Queries actuales (genéricas):**
1. ✅ Rutina según `gym_goal` (hipertrofia/fuerza)
2. ✅ Frecuencia de entrenamiento
3. ✅ Nutrición según `nutrition_goal` (volumen/definición)
4. ✅ Distribución de macronutrientes
5. ✅ Recuperación general

**Queries que FALTAN (específicas para modificaciones):**
- ❌ Lesiones específicas (ej: "lesión hombro ejercicios alternativos")
- ❌ Enfoque en áreas específicas (ej: "hipertrofia brazos volumen óptimo")
- ❌ Cambios de objetivo (ej: "transición fuerza a hipertrofia")
- ❌ Sustitución de ejercicios (ej: "alternativas press banca lesión hombro")

---

## 🎯 PROPUESTA DE IMPLEMENTACIÓN

### Opción 1: Queries Adicionales Condicionales (RECOMENDADA)

**Modificar `get_rag_context_for_plan()` para detectar modificaciones y añadir queries específicas:**

```python
async def get_rag_context_for_plan(datos: Dict[str, Any]) -> str:
    # ... queries actuales ...
    
    # ═══════════════════════════════════════════════════════
    # 🔥 NUEVO: QUERIES ESPECÍFICAS PARA MODIFICACIONES
    # ═══════════════════════════════════════════════════════
    
    # 6️⃣ QUERY PARA LESIONES (si hay información de lesión)
    lesiones = datos.get('lesiones', '')
    if lesiones and lesiones.lower() != 'ninguna' and 'evitar' in lesiones.lower():
        # Extraer parte del cuerpo de la lesión
        body_part = None
        for part in ['hombro', 'rodilla', 'espalda', 'codo', 'muñeca', 'tobillo', 'cadera']:
            if part in lesiones.lower():
                body_part = part
                break
        
        if body_part:
            queries.append({
                'text': f'lesión {body_part} ejercicios alternativos entrenamiento seguro evitar',
                'category': 'training_knowledge',
                'goal': gym_goal_rag,
                'weight': 2.0  # Mayor peso porque es crítico
            })
            queries.append({
                'text': f'adaptación rutina {body_part} lesión ejercicios sustitutos',
                'category': 'training_knowledge',
                'goal': gym_goal_rag,
                'weight': 1.8
            })
    
    # 7️⃣ QUERY PARA ENFOQUE EN ÁREAS (si hay focus_area)
    focus_area = datos.get('focus_area')
    if focus_area:
        queries.append({
            'text': f'hipertrofia {focus_area} volumen óptimo series repeticiones frecuencia',
            'category': 'training_knowledge',
            'goal': 'hipertrofia',  # Siempre hipertrofia para enfoque
            'weight': 1.8
        })
        queries.append({
            'text': f'entrenamiento {focus_area} frecuencia semanal volumen máximo',
            'category': 'training_knowledge',
            'goal': 'hipertrofia',
            'weight': 1.5
        })
    
    # 8️⃣ QUERY PARA CAMBIOS DE OBJETIVO (si se detecta cambio)
    # Nota: Esto requeriría comparar objetivo actual vs anterior
    # Por ahora, solo si el objetivo es diferente al default
    if datos.get('goal_changed'):
        old_goal = datos.get('old_goal')
        new_goal = datos.get('gym_goal')
        if old_goal and new_goal and old_goal != new_goal:
            queries.append({
                'text': f'transición entrenamiento {old_goal} a {new_goal} adaptación rutina',
                'category': 'training_knowledge',
                'goal': new_goal,
                'weight': 1.5
            })
    
    # ... continuar con queries actuales ...
```

**Ventajas:**
- ✅ No rompe la lógica existente
- ✅ Solo añade queries cuando hay modificaciones
- ✅ Mantiene queries genéricas para casos normales
- ✅ Fácil de implementar

**Desventajas:**
- ⚠️ Aumenta número de queries (más tiempo de respuesta)
- ⚠️ Más tokens en el prompt (más coste)

---

### Opción 2: Función Separada para Modificaciones

**Crear `get_rag_context_for_modification()` específica para modificaciones:**

```python
async def get_rag_context_for_modification(
    datos: Dict[str, Any],
    modification_type: str,  # "injury", "focus", "goal_change", etc.
    modification_data: Dict[str, Any]  # Datos específicos de la modificación
) -> str:
    """
    Recupera contexto RAG específico para modificaciones de planes.
    """
    queries = []
    
    if modification_type == "injury":
        body_part = modification_data.get('body_part')
        severity = modification_data.get('severity')
        queries.append({
            'text': f'lesión {body_part} severidad {severity} ejercicios alternativos entrenamiento seguro',
            'category': 'training_knowledge',
            'weight': 2.0
        })
        # ... más queries específicas ...
    
    elif modification_type == "focus":
        focus_area = modification_data.get('focus_area')
        queries.append({
            'text': f'hipertrofia {focus_area} volumen frecuencia óptima',
            'category': 'training_knowledge',
            'weight': 1.8
        })
        # ... más queries específicas ...
    
    # ... ejecutar queries y retornar contexto ...
```

**Luego modificar `generar_plan_personalizado()` para usar ambas funciones:**

```python
async def generar_plan_personalizado(datos):
    # Contexto RAG genérico
    rag_context_generic = await get_rag_context_for_plan(datos)
    
    # Contexto RAG específico para modificaciones (si aplica)
    rag_context_modification = ""
    if datos.get('modification_type'):
        rag_context_modification = await get_rag_context_for_modification(
            datos,
            datos.get('modification_type'),
            datos.get('modification_data', {})
        )
    
    # Combinar contextos
    rag_context = f"{rag_context_generic}\n\n{rag_context_modification}"
    
    # ... continuar con generación ...
```

**Ventajas:**
- ✅ Separación clara de responsabilidades
- ✅ Más fácil de mantener y testear
- ✅ Permite optimizar queries por tipo de modificación

**Desventajas:**
- ⚠️ Requiere modificar handlers para pasar `modification_type`
- ⚠️ Más complejidad en el código

---

## ⚠️ PELIGROS Y RIESGOS

### 1. **Aumento de Latencia** 🔴 ALTO

**Problema:**
- Cada query RAG requiere:
  - Generar embedding (~200-500ms)
  - Buscar en vectorstore (~100-300ms)
  - Total: ~300-800ms por query
- Si añadimos 2-3 queries adicionales: **+600-2400ms de latencia**

**Impacto:**
- Usuario espera más tiempo al hacer modificaciones
- Timeout de GPT podría activarse (actualmente 30s)
- Experiencia de usuario degradada

**Solución:**
- ✅ Ejecutar queries en paralelo con `asyncio.gather()`
- ✅ Limitar número máximo de queries (ej: máximo 8 total)
- ✅ Cachear resultados de queries comunes (ej: lesiones comunes)

---

### 2. **Aumento de Tokens y Coste** 🟡 MEDIO

**Problema:**
- Cada documento RAG añade ~500-2000 tokens al prompt
- Si añadimos 2-3 documentos más: **+1000-6000 tokens por request**
- Coste adicional: ~$0.01-0.05 por modificación (con GPT-4)

**Impacto:**
- Coste mensual aumenta significativamente
- Si hay muchas modificaciones, coste puede ser alto

**Solución:**
- ✅ Limitar documentos RAG a top 6-8 (ya implementado)
- ✅ Priorizar documentos más relevantes (usar `weight`)
- ✅ Considerar usar GPT-3.5 para modificaciones (más barato)

---

### 3. **Contexto Demasiado Largo** 🟡 MEDIO

**Problema:**
- Prompt muy largo puede:
  - Confundir a GPT (información contradictoria)
  - Hacer que GPT ignore partes del contexto
  - Generar respuestas menos coherentes

**Impacto:**
- Calidad de planes generados puede disminuir
- GPT puede ignorar información crítica (ej: lesión)

**Solución:**
- ✅ Limitar total de documentos a 8-10 máximo
- ✅ Priorizar documentos más relevantes (mayor `weight`)
- ✅ Estructurar contexto claramente (secciones separadas)
- ✅ Añadir instrucciones explícitas: "⚠️ CRÍTICO: Evitar ejercicios para {body_part}"

---

### 4. **Queries Irrelevantes** 🟢 BAJO

**Problema:**
- Si la base de conocimiento RAG no tiene información sobre una lesión específica, las queries pueden retornar documentos genéricos o irrelevantes

**Impacto:**
- Contexto RAG puede ser ruidoso
- GPT puede recibir información no útil

**Solución:**
- ✅ Filtrar resultados por `similarity` (solo >0.7)
- ✅ Validar que los documentos retornados son relevantes
- ✅ Fallback: si no hay documentos relevantes, no añadir contexto RAG específico

---

### 5. **Conflictos con Lógica Existente** 🟢 BAJO

**Problema:**
- Los handlers ya tienen lógica de fallback si GPT falla
- Si RAG añade complejidad y GPT falla más, podría activar fallbacks más frecuentemente

**Impacto:**
- Fallbacks menos personalizados se activarían más
- Experiencia de usuario inconsistente

**Solución:**
- ✅ Mantener fallbacks existentes
- ✅ Si RAG falla, continuar sin él (no bloquear generación)
- ✅ Logging detallado para monitorear fallos

---

### 6. **Detección Incorrecta de Modificaciones** 🟡 MEDIO

**Problema:**
- Si detectamos mal una modificación (ej: "lesiones" contiene "ninguna" pero lo detectamos como lesión), añadimos queries innecesarias

**Impacto:**
- Queries innecesarias = latencia y coste adicional sin beneficio

**Solución:**
- ✅ Validación estricta antes de añadir queries:
  ```python
  if lesiones and lesiones.lower() != 'ninguna' and 'evitar' in lesiones.lower() and len(lesiones) > 20:
      # Solo entonces añadir queries
  ```
- ✅ Logging para detectar falsos positivos

---

## 📋 PLAN DE IMPLEMENTACIÓN RECOMENDADO

### Fase 1: Implementación Básica (Opción 1)

1. **Modificar `get_rag_context_for_plan()`:**
   - Añadir detección de lesiones
   - Añadir detección de `focus_area`
   - Añadir queries específicas condicionales

2. **Testing:**
   - Probar con lesión de hombro
   - Probar con enfoque en brazos
   - Verificar que no rompe generación normal

3. **Monitoreo:**
   - Medir latencia antes/después
   - Medir tokens antes/después
   - Verificar calidad de planes generados

### Fase 2: Optimización

1. **Paralelización:**
   - Ejecutar queries RAG en paralelo
   - Reducir latencia total

2. **Caché:**
   - Cachear queries comunes (ej: "lesión hombro")
   - Reducir llamadas a vectorstore

3. **Límites:**
   - Limitar queries totales a 8
   - Priorizar por `weight`

### Fase 3: Expansión (Opcional)

1. **Más tipos de modificaciones:**
   - Cambios de objetivo
   - Sustitución de ejercicios
   - Cambios de equipamiento

2. **Queries más específicas:**
   - Basadas en severidad de lesión
   - Basadas en tipo de lesión (tendinitis vs rotura)

---

## ✅ RECOMENDACIÓN FINAL

**IMPLEMENTAR con Opción 1 (Queries Adicionales Condicionales):**

1. ✅ **Es seguro:** No rompe lógica existente
2. ✅ **Es efectivo:** Añade contexto relevante cuando hay modificaciones
3. ✅ **Es simple:** Cambio mínimo en código
4. ✅ **Es reversible:** Fácil de desactivar si hay problemas

**Precauciones:**
- ⚠️ Limitar a máximo 2-3 queries adicionales por modificación
- ⚠️ Ejecutar queries en paralelo para reducir latencia
- ⚠️ Monitorear coste y latencia después de implementar
- ⚠️ Validar que los documentos retornados son relevantes

**Métricas a monitorear:**
- Latencia promedio de modificaciones (objetivo: <5s)
- Tokens promedio por request (objetivo: <8000 tokens)
- Tasa de éxito de generación (objetivo: >95%)
- Satisfacción del usuario (planes más personalizados)

---

## 🔧 CÓDIGO DE EJEMPLO (Implementación Mínima)

```python
# En get_rag_context_for_plan(), después de la línea 175:

# 6️⃣ QUERY PARA LESIONES (si hay información de lesión específica)
lesiones = datos.get('lesiones', '')
if lesiones and lesiones.lower() != 'ninguna' and len(lesiones) > 20:
    # Detectar si es una lesión específica (contiene "EVITAR" o parte del cuerpo)
    body_parts = ['hombro', 'rodilla', 'espalda', 'codo', 'muñeca', 'tobillo', 'cadera', 'cuello']
    detected_part = None
    for part in body_parts:
        if part in lesiones.lower():
            detected_part = part
            break
    
    if detected_part and 'evitar' in lesiones.lower():
        queries.append({
            'text': f'lesión {detected_part} ejercicios alternativos entrenamiento seguro evitar',
            'category': 'training_knowledge',
            'goal': gym_goal_rag,
            'weight': 2.0  # Mayor prioridad
        })

# 7️⃣ QUERY PARA ENFOQUE (si hay focus_area)
focus_area = datos.get('focus_area')
if focus_area:
    queries.append({
        'text': f'hipertrofia {focus_area} volumen óptimo series repeticiones frecuencia',
        'category': 'training_knowledge',
        'goal': 'hipertrofia',
        'weight': 1.8
    })

# Continuar con queries actuales...
```

---

**FIN DEL ANÁLISIS** ✅

**Próximos pasos:** Revisar este análisis y decidir si implementar. Si se aprueba, proceder con Fase 1.

