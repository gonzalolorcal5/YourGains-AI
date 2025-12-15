# 🔍 QUERIES RAG ADICIONALES - SUGERENCIAS

**Objetivo:** Identificar queries RAG específicas que podrían mejorar la generación de planes cuando hay modificaciones o datos específicos del usuario.

---

## ✅ QUERIES YA IMPLEMENTADAS (Genéricas)

1. ✅ Rutina según objetivo gym (hipertrofia/fuerza)
2. ✅ Frecuencia de entrenamiento
3. ✅ Nutrición según objetivo nutricional (volumen/definición)
4. ✅ Distribución de macronutrientes
5. ✅ Recuperación general

---

## 🎯 QUERIES PROPUESTAS (Específicas para Modificaciones)

### 1. 🏥 **LESIONES** (Ya mencionado)
**Cuándo:** Si `lesiones` contiene información específica (no "Ninguna")

**Queries sugeridas:**
```python
# Si hay lesión de hombro
"lesión hombro ejercicios alternativos entrenamiento seguro evitar"
"adaptación rutina hombro lesión ejercicios sustitutos"
"rehabilitación hombro entrenamiento fuerza sin dolor"

# Si hay lesión de rodilla
"lesión rodilla ejercicios piernas alternativos sentadillas"
"entrenamiento piernas rodilla lesionada prensa extensión"

# Si hay lesión de espalda
"lesión espalda ejercicios seguros evitar peso muerto"
"entrenamiento espalda lesionada remo alternativas"
```

**Prioridad:** 🔴 ALTA (crítico para seguridad)

---

### 2. 🏋️ **MATERIALES NO DISPONIBLES** (Ya mencionado)
**Cuándo:** Si `missing_equipment` está presente

**Queries sugeridas:**
```python
# Si falta barra olímpica
"entrenamiento sin barra olímpica mancuernas alternativas"
"ejercicios compuestos mancuernas peso libre"

# Si falta banco de press
"entrenamiento pecho sin banco flexiones variaciones"
"press banca alternativas peso corporal"

# Si falta rack de sentadillas
"sentadillas alternativas sin rack prensa máquina"
"entrenamiento piernas sin rack sentadillas"
```

**Prioridad:** 🟡 MEDIA (importante para personalización)

---

### 3. 🎯 **ENFOQUE EN ÁREAS** (Ya mencionado)
**Cuándo:** Si `focus_area` está presente

**Queries sugeridas:**
```python
# Si focus_area = "brazos"
"hipertrofia brazos volumen óptimo series repeticiones frecuencia"
"entrenamiento brazos frecuencia semanal volumen máximo"
"bíceps tríceps hipertrofia frecuencia entrenamiento"

# Si focus_area = "piernas"
"hipertrofia piernas volumen semanal frecuencia óptima"
"entrenamiento piernas frecuencia máxima crecimiento"
"cuádriceps glúteos hipertrofia volumen series"

# Si focus_area = "pecho"
"hipertrofia pectoral volumen frecuencia entrenamiento"
"desarrollo pecho volumen óptimo series repeticiones"
```

**Prioridad:** 🟡 MEDIA (mejora personalización)

---

### 4. 🥛 **ALERGIAS ALIMENTARIAS**
**Cuándo:** Si `alergias` contiene información específica (no "Ninguna")

**Queries sugeridas:**
```python
# Si alergia a lactosa
"dieta sin lactosa proteínas alternativas lácteos"
"alimentos ricos proteína sin lactosa sustitutos leche"
"nutrición fitness intolerancia lactosa alternativas"

# Si alergia a gluten (celíaco)
"dieta fitness celíaco sin gluten carbohidratos"
"alimentos fitness sin gluten hidratos complejos"
"nutrición deportiva celiaquía macronutrientes"

# Si alergia a frutos secos
"proteínas alternativas frutos secos alergia"
"grasas saludables sin frutos secos dieta fitness"
"alimentos fitness sin frutos secos omega 3"

# Si alergia a huevo
"proteínas alternativas huevo dieta fitness"
"desayuno fitness sin huevo proteínas completas"
"nutrición deportiva sin huevo aminoácidos esenciales"
```

**Prioridad:** 🔴 ALTA (crítico para salud)

---

### 5. 🌱 **RESTRICCIONES DIETÉTICAS**
**Cuándo:** Si `restricciones` contiene "vegetariano", "vegano", "halal", etc.

**Queries sugeridas:**
```python
# Si vegetariano
"dieta vegetariana fitness proteínas completas"
"nutrición vegetariana hipertrofia macronutrientes"
"proteínas vegetales fitness combinaciones completas"

# Si vegano
"dieta vegana fitness proteínas completas"
"nutrición vegana hipertrofia B12 creatina"
"proteínas veganas fitness aminoácidos esenciales"

# Si halal
"dieta halal fitness proteínas permitidas"
"nutrición halal deportiva macronutrientes"
```

**Prioridad:** 🟡 MEDIA (importante para adherencia)

---

### 6. 📊 **TIPO DE CUERPO**
**Cuándo:** Si `tipo_cuerpo` es específico (ectomorfo, mesomorfo, endomorfo)

**Queries sugeridas:**
```python
# Si ectomorfo (delgado, difícil ganar peso)
"entrenamiento ectomorfo ganar músculo volumen frecuencia"
"nutrición ectomorfo superávit calórico ganar peso"
"hipertrofia ectomorfo frecuencia entrenamiento volumen"

# Si endomorfo (tendencia a acumular grasa)
"entrenamiento endomorfo pérdida grasa hipertrofia"
"nutrición endomorfo definición déficit calórico"
"metabolismo endomorfo frecuencia entrenamiento"

# Si mesomorfo (genética favorable)
"entrenamiento mesomorfo optimización hipertrofia"
"nutrición mesomorfo volumen definición"
```

**Prioridad:** 🟢 BAJA (nice to have, pero no crítico)

---

### 7. 💪 **PUNTOS DÉBILES/ÁREAS REZAGADAS**
**Cuándo:** Si `puntos_debiles` contiene información específica

**Queries sugeridas:**
```python
# Si puntos débiles = "brazos"
"desarrollo brazos rezagados hipertrofia volumen"
"entrenamiento brazos puntos débiles frecuencia volumen"
"bíceps tríceps desarrollo volumen óptimo"

# Si puntos débiles = "piernas"
"desarrollo piernas rezagadas volumen frecuencia"
"entrenamiento piernas puntos débiles hipertrofia"
"cuádriceps glúteos desarrollo volumen máximo"
```

**Prioridad:** 🟢 BAJA (similar a focus_area)

---

### 8. 🔄 **CAMBIOS DE OBJETIVO**
**Cuándo:** Si se detecta cambio de `gym_goal` o `nutrition_goal`

**Queries sugeridas:**
```python
# Si cambio de fuerza a hipertrofia
"transición fuerza a hipertrofia adaptación rutina"
"cambiar objetivo fuerza hipertrofia volumen repeticiones"
"periodización fuerza hipertrofia entrenamiento"

# Si cambio de volumen a definición
"transición volumen a definición déficit calórico"
"cambiar objetivo volumen definición preservar músculo"
"déficit calórico definición preservación masa muscular"

# Si cambio de hipertrofia a fuerza
"transición hipertrofia a fuerza powerlifting"
"cambiar objetivo hipertrofia fuerza repeticiones series"
"entrenamiento fuerza powerlifting periodización"
```

**Prioridad:** 🟡 MEDIA (importante para transiciones)

---

### 9. 👤 **SEXO Y HORMONAS**
**Cuándo:** Si `sexo` = "femenino" (consideraciones hormonales)

**Queries sugeridas:**
```python
# Si mujer
"entrenamiento mujer hipertrofia hormonas ciclo menstrual"
"nutrición mujer fitness macronutrientes hormonas"
"hipertrofia mujer frecuencia entrenamiento ciclo"
"entrenamiento mujer fuerza volumen óptimo"
```

**Prioridad:** 🟡 MEDIA (importante para personalización)

---

### 10. 🎂 **EDAD Y RECUPERACIÓN**
**Cuándo:** Si `edad` > 40 (consideraciones de recuperación)

**Queries sugeridas:**
```python
# Si edad > 40
"entrenamiento mayores 40 años recuperación volumen"
"hipertrofia mayores 40 años frecuencia descanso"
"nutrición mayores 40 años proteína recuperación"
"entrenamiento fuerza mayores 40 años adaptaciones"
```

**Prioridad:** 🟢 BAJA (nice to have)

---

### 11. 🏃 **NIVEL DE ACTIVIDAD**
**Cuándo:** Si `nivel_actividad` es extremo (sedentario o muy_activo)

**Queries sugeridas:**
```python
# Si sedentario
"entrenamiento principiante sedentario frecuencia inicio"
"nutrición sedentario inicio fitness TDEE bajo"
"adaptación entrenamiento sedentario principiante"

# Si muy activo
"entrenamiento muy activo recuperación volumen"
"nutrición muy activo TDEE alto superávit"
"entrenamiento fuerza muy activo frecuencia descanso"
```

**Prioridad:** 🟢 BAJA (ya se considera en TDEE)

---

### 12. 🔄 **SUSTITUCIÓN DE EJERCICIOS ESPECÍFICOS**
**Cuándo:** Si `exercise_to_replace` está presente

**Queries sugeridas:**
```python
# Si sustituir "press banca"
"alternativas press banca ejercicios pecho"
"sustitutos press banca hipertrofia pectoral"
"ejercicios pecho sin press banca mancuernas"

# Si sustituir "sentadillas"
"alternativas sentadillas ejercicios piernas"
"sustitutos sentadillas hipertrofia piernas"
"ejercicios piernas sin sentadillas prensa"
```

**Prioridad:** 🟡 MEDIA (importante para personalización)

---

### 13. 📈 **EXPERIENCIA ESPECÍFICA**
**Cuándo:** Si `experiencia` es "avanzado" (queries más técnicas)

**Queries sugeridas:**
```python
# Si avanzado
"entrenamiento avanzado hipertrofia técnicas intensidad"
"periodización avanzada hipertrofia volumen frecuencia"
"técnicas avanzadas hipertrofia drop sets rest pause"
"entrenamiento avanzado fuerza periodización"
```

**Prioridad:** 🟢 BAJA (ya se considera en queries genéricas)

---

### 14. 🎯 **RECOMPOSICIÓN CORPORAL**
**Cuándo:** Si `nutrition_goal` = "recomposicion"

**Queries sugeridas:**
```python
# Si recomposición
"recomposición corporal pérdida grasa ganancia músculo"
"déficit calórico recomposición preservar músculo"
"entrenamiento recomposición volumen frecuencia"
"nutrición recomposición macros distribución"
```

**Prioridad:** 🟡 MEDIA (objetivo específico que requiere info especializada)

---

### 15. 🏋️ **ENTRENAR FUERTE/INTENSIDAD**
**Cuándo:** Si `entrenar_fuerte` indica preferencia por alta intensidad

**Queries sugeridas:**
```python
# Si prefiere entrenar fuerte
"entrenamiento alta intensidad hipertrofia volumen"
"frecuencia entrenamiento alta intensidad recuperación"
"periodización alta intensidad volumen descanso"
```

**Prioridad:** 🟢 BAJA (nice to have)

---

## 📊 RESUMEN POR PRIORIDAD

### 🔴 **ALTA PRIORIDAD** (Implementar primero)
1. ✅ **Lesiones** - Crítico para seguridad
2. ✅ **Alergias alimentarias** - Crítico para salud

### 🟡 **MEDIA PRIORIDAD** (Implementar después)
3. ✅ **Materiales no disponibles** - Importante para personalización
4. ✅ **Enfoque en áreas** - Mejora personalización
5. ✅ **Restricciones dietéticas** - Importante para adherencia
6. ✅ **Cambios de objetivo** - Importante para transiciones
7. ✅ **Sexo (mujer)** - Importante para personalización
8. ✅ **Sustitución de ejercicios** - Importante para personalización
9. ✅ **Recomposición corporal** - Objetivo específico

### 🟢 **BAJA PRIORIDAD** (Nice to have)
10. Tipo de cuerpo
11. Puntos débiles
12. Edad > 40
13. Nivel de actividad extremo
14. Experiencia avanzada
15. Entrenar fuerte

---

## 💡 RECOMENDACIÓN DE IMPLEMENTACIÓN

**Fase 1 (Crítico):**
- Lesiones
- Alergias alimentarias

**Fase 2 (Importante):**
- Materiales no disponibles
- Enfoque en áreas
- Restricciones dietéticas
- Sustitución de ejercicios

**Fase 3 (Opcional):**
- Resto de queries según necesidad

---

**FIN DEL DOCUMENTO** ✅

