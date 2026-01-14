# 💰 RESUMEN DE COSTOS - OPENAI API

## 📊 COSTOS POR OPERACIÓN

### 1. GENERAR UN PLAN (Rutina + Dieta)

#### Modelo Utilizado
- **GPT-4o** (configurable con `OPENAI_MODEL` en `.env`)
- **Precios:** $5.00 / 1M input tokens, $15.00 / 1M output tokens

#### RAG (Retrieval Augmented Generation)
- ✅ **SÍ se usa RAG** para generar planes
- **Modelo de embeddings:** `text-embedding-3-small` ($0.02 / 1M tokens)
- **Proceso:**
  1. Genera 5-10 queries basadas en el perfil del usuario
  2. Cada query genera un embedding
  3. Busca top 6 documentos científicos relevantes
  4. Inyecta contexto científico en el prompt de GPT-4o

#### Tokens Aproximados por Plan
| Componente | Tokens | Descripción |
|------------|--------|-------------|
| **Embeddings RAG** | ~150 | 5-10 queries × ~15 tokens/query |
| **Prompt (Input)** | ~2,000-2,500 | Contexto RAG + datos usuario + instrucciones |
| **Output (Completion)** | ~1,500-2,000 | Plan completo (rutina + dieta + motivación) |
| **TOTAL** | **~3,500-4,500** | Tokens por plan completo |

#### Costo por Plan
| Concepto | Cálculo | Costo |
|----------|---------|-------|
| **Embeddings RAG** | 150 tokens × $0.02 / 1M | **$0.000003** |
| **GPT-4o Input** | 2,500 tokens × $5.00 / 1M | **$0.0125** |
| **GPT-4o Output** | 1,500 tokens × $15.00 / 1M | **$0.0225** |
| **TOTAL POR PLAN** | | **~$0.035** |

**Nota:** El costo real puede variar según:
- Complejidad del perfil del usuario
- Número de queries RAG generadas
- Longitud del plan generado

---

### 2. PREGUNTA EN EL CHAT

#### Modelo Utilizado
- **gpt-4o-mini** (hardcoded en `app/routes/chat.py` línea 126)
- **Precios:** $0.15 / 1M input tokens, $0.60 / 1M output tokens

#### RAG (Retrieval Augmented Generation)
- ✅ **SÍ se usa RAG** para el chat
- **Modelo de embeddings:** `text-embedding-3-small` ($0.02 / 1M tokens)
- **Proceso:**
  1. Genera 1 embedding del mensaje del usuario
  2. Busca top 3 documentos científicos relevantes
  3. Inyecta contexto científico en el prompt de gpt-4o-mini

#### Tokens Aproximados por Pregunta
| Componente | Tokens | Descripción |
|------------|--------|-------------|
| **Embedding RAG** | ~15 | 1 mensaje del usuario |
| **Prompt (Input)** | ~500-800 | Contexto RAG + prompt sistema + mensaje usuario |
| **Output (Completion)** | ~200-300 | Respuesta limitada a 300 tokens máximo |
| **TOTAL** | **~700-1,100** | Tokens por pregunta |

#### Costo por Pregunta
| Concepto | Cálculo | Costo |
|----------|---------|-------|
| **Embedding RAG** | 15 tokens × $0.02 / 1M | **$0.0000003** |
| **gpt-4o-mini Input** | 700 tokens × $0.15 / 1M | **$0.0001** |
| **gpt-4o-mini Output** | 300 tokens × $0.60 / 1M | **$0.0002** |
| **TOTAL POR PREGUNTA** | | **~$0.0003** |

**Nota:** El costo es ~100x más barato que generar un plan porque:
- Usa `gpt-4o-mini` en lugar de `gpt-4o`
- Respuesta limitada a 300 tokens
- Menos contexto RAG (3 documentos vs 6)

---

## 📈 COSTOS MENSUALES ESTIMADOS

### Escenario Conservador (100 usuarios activos/mes)
| Operación | Cantidad | Costo Unitario | Costo Total |
|-----------|----------|---------------|-------------|
| **Generar Plan** | 100 planes | $0.035 | **$3.50** |
| **Preguntas Chat** | 1,000 preguntas | $0.0003 | **$0.30** |
| **TOTAL MENSUAL** | | | **~$3.80** |

### Escenario Moderado (500 usuarios activos/mes)
| Operación | Cantidad | Costo Unitario | Costo Total |
|-----------|----------|---------------|-------------|
| **Generar Plan** | 500 planes | $0.035 | **$17.50** |
| **Preguntas Chat** | 5,000 preguntas | $0.0003 | **$1.50** |
| **TOTAL MENSUAL** | | | **~$19.00** |

### Escenario Alto (2,000 usuarios activos/mes)
| Operación | Cantidad | Costo Unitario | Costo Total |
|-----------|----------|---------------|-------------|
| **Generar Plan** | 2,000 planes | $0.035 | **$70.00** |
| **Preguntas Chat** | 20,000 preguntas | $0.0003 | **$6.00** |
| **TOTAL MENSUAL** | | | **~$76.00** |

---

## 💡 OPTIMIZACIONES Y CONSIDERACIONES

### Costos de Embeddings (RAG)
- **Muy bajos:** Representan <0.1% del costo total
- **Modelo:** `text-embedding-3-small` es el más económico de OpenAI
- **No es necesario optimizar** - el costo es insignificante

### Costos de Generación de Planes
- **Principal costo:** Generación de planes con GPT-4o
- **Optimización posible:** Usar `gpt-3.5-turbo` reduce costos a ~$0.0035 por plan (10x más barato)
- **Trade-off:** Menor calidad en planes personalizados

### Costos de Chat
- **Ya optimizado:** Usa `gpt-4o-mini` (más económico)
- **Límite de tokens:** 300 tokens máximo por respuesta
- **RAG eficiente:** Solo 3 documentos vs 6 en planes

### Recomendaciones
1. **Mantener GPT-4o para planes:** La calidad justifica el costo
2. **Chat ya optimizado:** No requiere cambios
3. **Monitorear uso:** Revisar logs para detectar picos de costos
4. **Considerar cache:** Cachear planes similares para reducir llamadas

---

## 🔍 VERIFICACIÓN EN LOGS

### Al Generar un Plan
Busca en los logs:
```
📊 Tokens GPT: 3500 total (2500 prompt + 1000 completion)
💰 Costo GPT-4o: $0.0350
💰 Costo embeddings RAG: ~$0.000003
💰 Costo TOTAL estimado (GPT + RAG): $0.0350
```

### Al Hacer una Pregunta en Chat
Busca en los logs:
```
🔍 Obteniendo contexto RAG para el chat...
✅ Contexto RAG añadido al prompt
```

---

## 📝 NOTAS IMPORTANTES

1. **Modelo de Chat:** Actualmente usa `gpt-4o-mini` (hardcoded), NO usa `OPENAI_MODEL`
2. **Modelo de Planes:** Usa `OPENAI_MODEL` o `gpt-4o` por defecto
3. **RAG siempre activo:** Tanto planes como chat usan RAG
4. **Costos reales:** Pueden variar según uso real - estos son estimados
5. **Embeddings:** Costo insignificante (<0.1% del total)

---

## 🎯 RESUMEN EJECUTIVO

| Operación | Modelo | RAG | Costo Unitario | Costo Mensual (500 users) |
|-----------|--------|-----|----------------|---------------------------|
| **Generar Plan** | GPT-4o | ✅ Sí | $0.035 | $17.50 |
| **Pregunta Chat** | gpt-4o-mini | ✅ Sí | $0.0003 | $1.50 |
| **TOTAL** | | | | **~$19.00/mes** |

**Conclusión:** Los costos son muy razonables. El chat es extremadamente barato (~$0.0003 por pregunta) y los planes tienen un costo aceptable (~$0.035 por plan) considerando la calidad y personalización que ofrecen.

