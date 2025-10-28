# 📋 ESTADO ACTUAL DEL PROYECTO GYMAI
**Fecha:** 20 de Octubre de 2025  
**Versión actual:** v2.0 (Post git reset - Sistema de modificaciones completo)

---

## 🎯 RESUMEN EJECUTIVO

Este proyecto es una **aplicación de fitness con IA** que genera planes personalizados de entrenamiento y dieta, con un **sistema avanzado de modificaciones dinámicas** que detecta automáticamente cambios en las necesidades del usuario.

### Estado General:
- ✅ **Backend:** Completamente funcional con sistema de modificaciones avanzado
- ⚠️ **Onboarding:** Versión básica (falta versión avanzada con días y objetivos separados)
- ✅ **Base de datos:** Completa con campos dinámicos
- ✅ **Chat con IA:** Funcional con OpenAI function calling

---

## 📚 STACK TECNOLÓGICO

### Backend:
- **Framework:** FastAPI (Python)
- **Base de datos:** SQLAlchemy + SQLite
- **IA:** OpenAI GPT-4 Turbo (producción) / GPT-3.5 Turbo (desarrollo)
- **Autenticación:** JWT con bcrypt
- **Pagos:** Stripe

### Frontend:
- **HTML + TailwindCSS + JavaScript Vanilla**
- Sin framework (vanilla JS)

---

## 🗄️ ESTRUCTURA DE BASE DE DATOS

### Tabla `Usuario` (usuarios)
```python
- id: Integer (PK)
- email: String (unique)
- hashed_password: String

# Stripe / Premium
- is_premium: Boolean (default=False)
- stripe_customer_id: String (nullable)
- plan_type: String (default="FREE") # FREE | PREMIUM
- chat_uses_free: Integer (default=2)

# Onboarding
- onboarding_completed: Boolean (default=False)

# Campos dinámicos (JSON almacenado como Text)
- current_routine: Text (JSON) - Rutina actual del usuario
- current_diet: Text (JSON) - Dieta actual del usuario
- injuries: Text (JSON Array) - Historial de lesiones
- focus_areas: Text (JSON Array) - Áreas de enfoque
- disliked_foods: Text (JSON Array) - Alimentos rechazados
- modification_history: Text (JSON Array) - Historial de modificaciones (máx. 50)
```

### Tabla `Plan` (planes)
**Nota:** Esta tabla guarda el plan inicial generado en el onboarding (histórico)
```python
- id: Integer (PK)
- user_id: Integer (FK → usuarios.id)
- altura: Integer
- peso: String
- edad: Integer
- sexo: String
- experiencia: String
- objetivo: String # OBJETIVO ÚNICO (no separado)
- materiales: String (CSV)
- tipo_cuerpo: String
- idioma: String (default="es")
- puntos_fuertes: String (nullable)
- puntos_debiles: String (nullable)
- entrenar_fuerte: String (nullable)
- lesiones: String (nullable)
- alergias: String (nullable)
- restricciones_dieta: String (nullable)
- rutina: Text (JSON) # Plan inicial
- dieta: Text (JSON) # Plan inicial
- motivacion: Text
- fecha_creacion: DateTime
```

---

## ✅ FUNCIONALIDADES IMPLEMENTADAS

### 1. Sistema de Autenticación (`app/routes/auth.py`)
- ✅ Registro de usuarios
- ✅ Login con JWT
- ✅ Hashing de contraseñas con bcrypt
- ✅ Validación de tokens

### 2. Onboarding Básico (`app/routes/onboarding.py`, `frontend/onboarding.html`)
**LO QUE TIENE:**
```yaml
Campos del formulario:
  - Altura (cm)
  - Peso (kg)
  - Edad (años)
  - Sexo (hombre/mujer)
  - Objetivo ÚNICO:
      * perder_peso
      * ganar_musculo
      * definir
      * mantener
      * fuerza
  - Experiencia:
      * principiante (0-6 meses)
      * intermedio (6 meses - 2 años)
      * avanzado (2+ años)
  - Materiales (checkboxes múltiples):
      * Gym completo
      * Pesas libres
      * Mancuernas
      * Barra olímpica
      * Solo en casa
      * Máquinas cardio
  - Tipo de cuerpo:
      * Ectomorfo (delgado)
      * Mesomorfo (atlético)
      * Endomorfo (tendencia a grasa)
  - Alergias alimentarias (texto libre)
  - Restricciones dietéticas:
      * Ninguna
      * Vegetariano
      * Vegano
      * Keto
      * Sin gluten
  - Lesiones o limitaciones (texto libre)

Proceso:
  1. Usuario completa formulario
  2. POST /onboarding → genera plan con GPT
  3. Guarda plan inicial en tabla `Plan` (histórico)
  4. Guarda current_routine y current_diet en Usuario
  5. Marca onboarding_completed = True
  6. Redirige a dashboard
```

### 3. ⭐ SISTEMA DE MODIFICACIONES DINÁMICAS (`app/routes/chat_modify_optimized.py`, `app/utils/function_handlers_optimized.py`)

**ESTE ES EL CORAZÓN DEL SISTEMA - TOTALMENTE FUNCIONAL**

#### Funciones Disponibles:

##### 🏋️ RUTINAS:

1. **`modify_routine_injury`** - Adapta rutina por lesiones
   ```yaml
   Detecta: "me duele el hombro", "lesión en rodilla", "dolor de espalda"
   Acción:
     - Identifica parte del cuerpo lesionada
     - Elimina ejercicios problemáticos
     - Añade alternativas seguras
     - Guarda en injuries[]
   Parámetros:
     - body_part: hombro, rodilla, espalda, cuello, muñeca, tobillo, codo, etc.
     - injury_type: tendinitis, esguince, contractura, inflamacion, etc.
     - severity: mild, moderate, severe
   ```

2. **`modify_routine_focus`** - Enfoca más en un área
   ```yaml
   Detecta: "quiero más pecho", "enfocar piernas", "más brazos"
   Acción:
     - Añade ejercicios del área objetivo
     - Aumenta volumen/frecuencia
     - Mantiene balance muscular
   Parámetros:
     - focus_area: brazos, pecho, espalda, piernas, hombros, core, gluteos
     - increase_frequency: true/false
     - volume_change: ligero_aumento, aumento_moderado, aumento_significativo
   ```

3. **`adjust_routine_difficulty`** - Ajusta dificultad general
   ```yaml
   Detecta: "muy fácil", "muy difícil", "más intensidad", "menos peso"
   Acción:
     - Aumenta/disminuye series
     - Ajusta pesos recomendados
     - Modifica repeticiones
   Parámetros:
     - direction: increase, decrease
     - reason: usuario_se_siente_cansado, usuario_quiere_mas_desafio, etc.
   ```

4. **`substitute_exercise`** - Cambia ejercicios específicos
   ```yaml
   Detecta: "no me gusta sentadillas", "no tengo press banca", "muy difícil dominadas"
   Acción:
     - Identifica ejercicio a sustituir
     - Busca alternativas según equipamiento
     - Mantiene grupos musculares trabajados
   Parámetros:
     - exercise_to_replace: nombre del ejercicio
     - replacement_reason: no_gusta, no_tiene_maquina, muy_dificil, etc.
     - target_muscles: pecho, espalda, piernas, etc.
     - equipment_available: peso_libre, maquinas, cuerpo_libre, bandas
   ```

5. **`modify_routine_equipment`** - Adapta por falta de equipamiento
   ```yaml
   Detecta: "no tengo press banca", "no hay rack de sentadillas", "solo mancuernas"
   Acción:
     - Identifica equipamiento faltante
     - Adapta ejercicios a equipamiento disponible
     - Mantiene intensidad equivalente
   Parámetros:
     - missing_equipment: press_banca, sentadilla_rack, maquinas, etc.
     - available_equipment: peso_libre, cuerpo_libre, bandas, etc.
   ```

##### 🍎 DIETA:

1. **`recalculate_diet_macros`** - Recalcula macros y calorías ⭐⭐⭐
   ```yaml
   Detecta:
     - CAMBIOS DE PESO: "subí 2kg", "bajé 1.5 kilos", "gané peso", "adelgacé"
     - CAMBIOS DE OBJETIVO: "quiero volumen", "ahora definición", "mantener peso"
   Acción:
     - Recalcula calorías según objetivo
     - Ajusta macros proporcionalmente (proteína, carbos, grasas)
     - Modifica cantidades de alimentos
     - Recalcula totales
   Parámetros:
     - weight_change_kg: -10.0 a +10.0 (negativo = pérdida, positivo = ganancia)
     - goal: volumen, definicion, mantenimiento, fuerza, resistencia
   Ajustes:
     - volumen: +250 kcal (si weight_change > 0)
     - definicion: -250 kcal (si weight_change < 0)
     - mantenimiento: ±200 kcal por kg
     - fuerza: +150 kcal
     - resistencia: +100 kcal
   ```

2. **`substitute_disliked_food`** - Sustituye alimentos
   ```yaml
   Detecta: "no me gusta el pollo", "odio el brócoli", "cambiar el atún"
   Acción:
     - Identifica alimento rechazado
     - Valida contra alergias del usuario
     - Busca alternativas con macros similares
     - Actualiza disliked_foods[]
   Parámetros:
     - disliked_food: nombre del alimento
     - meal_type: desayuno, almuerzo, cena, snack, todos
   ```

3. **`generate_meal_alternatives`** - Genera alternativas de comidas
   ```yaml
   Detecta: "dame opciones para desayuno", "alternativas de cena"
   Acción:
     - Genera 2-5 opciones de comidas
     - Mantiene macros similares
     - Considera alergias y restricciones
   ```

4. **`simplify_diet_plan`** - Simplifica dieta
   ```yaml
   Detecta: "muy complicado", "recetas más simples", "menos ingredientes"
   Acción:
     - Reduce complejidad de recetas
     - Disminuye número de ingredientes
     - Facilita preparación
   ```

##### 🔄 GENERAL:

1. **`revert_last_modification`** - Deshace última modificación
   ```yaml
   Detecta: "deshacer último cambio", "volver atrás", "revertir"
   Acción:
     - Recupera estado anterior desde modification_history
     - Restaura current_routine o current_diet
     - Elimina último registro del historial
   ```

#### Palabras Clave Detectadas Automáticamente:
```python
🔥 PESO: "subí", "bajé", "gané", "perdí", "engordé", "adelgacé", "kg", "kilo", "kilos"
🎯 OBJETIVO: "fuerza", "hipertrofia", "volumen", "definir", "definición", "mantener"
💪 DIFICULTAD: "fácil", "difícil", "intensidad", "peso", "demasiado", "necesito"
🎯 ENFOQUE: "enfocar", "más", "brazos", "pecho", "piernas", "glúteos", "espalda"
🏥 LESIONES: "duele", "dolor", "lesión", "lesionado", "molesta", "hombro", "rodilla"
💪 EJERCICIOS: "no me gusta", "odio", "no tengo", "no puedo hacer"
🏋️ EQUIPAMIENTO: "no tengo", "no hay", "máquina", "barra", "mancuernas"
🍎 ALIMENTOS: "no me gusta", "odio", "no quiero", "sustituir", "cambiar"
```

### 4. Servicio de Base de Datos (`app/utils/database_service.py`)
- ✅ Operaciones optimizadas en UNA sola consulta
- ✅ `get_user_complete_data()` - Obtiene todos los datos del usuario
- ✅ `update_user_data()` - Actualiza campos dinámicos
- ✅ `add_modification_record()` - Añade al historial (máx. 50 registros)
- ✅ `get_last_modification()` - Obtiene última modificación
- ✅ `remove_last_modification()` - Elimina última modificación

### 5. Detección de Alergias (`app/utils/allergy_detection.py`)
- ✅ Valida alimentos contra alergias del usuario
- ✅ Genera alternativas seguras
- ✅ Previene sustituciones peligrosas

### 6. Integración con Stripe
- ✅ Webhooks de pagos
- ✅ Sistema freemium (2 preguntas gratis)
- ✅ Upgrade a premium

---

## ❌ FUNCIONALIDADES FALTANTES (Perdidas en git reset)

### 1. Onboarding Avanzado ⚠️ **ESTO ES LO QUE FALTA**

**LO QUE SE PERDIÓ:**
```yaml
Separación de Objetivos:
  - Objetivo de Gimnasio:
      * Fuerza (powerlifting, strength training)
      * Hipertrofia (bodybuilding, ganar masa muscular)
  
  - Objetivo Nutricional:
      * Volumen (superávit calórico, ganar peso)
      * Mantenimiento (calorías de mantenimiento)
      * Definición (déficit calórico, perder grasa)

Selección de Días de Entrenamiento:
  - Checkboxes para cada día:
      [ ] Lunes
      [ ] Martes
      [ ] Miércoles
      [ ] Jueves
      [ ] Viernes
      [ ] Sábado
      [ ] Domingo
  
  - O selector de frecuencia:
      * 3 días/semana
      * 4 días/semana
      * 5 días/semana
      * 6 días/semana

Campos Adicionales:
  - ¿Cuántos días puedes entrenar? (número o checkboxes)
  - Duración aproximada por sesión (30min, 45min, 60min, 90min)
  - Horario preferido (mañana, tarde, noche)
```

**IMPACTO DE LA FALTA:**
```diff
- ❌ No se puede generar rutina adaptada a días específicos
- ❌ No hay diferenciación clara entre objetivos de gym y nutrición
- ❌ El sistema de modificaciones SÍ puede ajustar, pero el plan inicial es genérico
```

### 2. Posibles Mejoras Futuras
```yaml
Dashboard:
  - Visualización de progreso (gráficos)
  - Calendario de entrenamientos
  - Seguimiento de peso/medidas
  
Rutina:
  - Timer de descanso entre series
  - Registro de pesos usados
  - Progresión automática
  
Dieta:
  - Lista de compras automática
  - Sustituciones rápidas en el momento
  - Recetas detalladas con pasos
  
Notificaciones:
  - Recordatorios de entrenamiento
  - Alertas de comidas
  - Sugerencias de ajustes
```

---

## 📂 ARCHIVOS IMPORTANTES

### Backend:
```
Backend/app/
├── main.py                              # Entry point de FastAPI
├── database.py                          # Configuración de SQLAlchemy
├── models.py                            # ✅ Modelos Usuario y Plan
├── schemas.py                           # Schemas de Pydantic
├── auth_utils.py                        # Utilidades de autenticación
│
├── routes/
│   ├── __init__.py
│   ├── auth.py                          # ✅ Registro y Login
│   ├── onboarding.py                    # ⚠️ Onboarding básico (FALTA versión avanzada)
│   ├── chat_modify_optimized.py        # ⭐ Chat con modificaciones dinámicas
│   ├── plan.py                          # Endpoints de planes
│   ├── stripe_routes.py                 # Integración con Stripe
│   └── user_status.py                   # Estado del usuario
│
└── utils/
    ├── function_handlers_optimized.py   # ⭐⭐⭐ Handlers de modificaciones (CORE)
    ├── functions_definitions.py         # ⭐ Definiciones de funciones OpenAI
    ├── database_service.py              # ✅ Servicio centralizado de DB
    ├── gpt.py                            # ✅ Generación de planes con GPT
    ├── allergy_detection.py             # ✅ Validación de alergias
    ├── json_helpers.py                  # Serialización de JSON
    ├── simple_injury_handler.py         # Handler simplificado de lesiones
    └── routine_templates.py             # Templates de rutinas genéricas
```

### Frontend:
```
Backend/app/frontend/
├── login.html                           # Login y registro
├── onboarding.html                      # ⚠️ Formulario básico (FALTA versión avanzada)
├── onboarding.js                        # ⚠️ Lógica básica
├── dashboard.html                       # Dashboard principal
├── rutina.html                          # Vista de rutina
├── tarifas.html                         # Página de precios
├── pago.html                            # Checkout de Stripe
├── auth.js                              # Utilidades de autenticación
├── config.js                            # Configuración del API
└── images/
    └── gym-training-dark.jpg
```

---

## 🔧 CONFIGURACIÓN Y EJECUCIÓN

### Variables de Entorno Necesarias:
```bash
# .env
OPENAI_API_KEY=sk-...
DATABASE_URL=sqlite:///./app/database.db
SECRET_KEY=tu_secret_key_jwt
STRIPE_API_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
ENVIRONMENT=development  # o production
```

### Modelos según Ambiente:
```python
# Configurado en chat_modify_optimized.py
ENVIRONMENT = development → GPT-3.5 Turbo (~$0.0015/1K tokens - 20x más barato)
ENVIRONMENT = production  → GPT-4 Turbo (~$0.03/1K tokens)
```

### Ejecutar:
```bash
# Activar entorno virtual
cd Backend
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servidor
python run_server.py
# o
uvicorn app.main:app --reload --port 8000
```

### Acceder:
```
Frontend: http://localhost:8000/app/frontend/login.html
API Docs: http://localhost:8000/docs
```

---

## 🚨 PROBLEMAS CONOCIDOS

### 1. Error 500 en POST /onboarding (RESUELTO)
```python
# PROBLEMA: db.refresh(nuevo_plan) después de commit
# SOLUCIÓN: Comentar la línea 155 en onboarding.py
# Estado: ✅ RESUELTO
```

### 2. Onboarding Básico vs Avanzado
```yaml
Problema: Se perdió la versión avanzada del onboarding en el git reset
Estado: ⚠️ PENDIENTE REIMPLEMENTAR
Archivos afectados:
  - Backend/app/routes/onboarding.py (agregar campos)
  - Backend/app/frontend/onboarding.html (agregar UI)
  - Backend/app/frontend/onboarding.js (agregar lógica)
  - Backend/app/models.py (posiblemente agregar campos)
```

---

## 🎯 PRÓXIMOS PASOS RECOMENDADOS

### Prioridad Alta:
1. **Reimplementar Onboarding Avanzado**
   - Separar objetivo gym vs nutricional
   - Añadir selección de días de entrenamiento
   - Actualizar backend para manejar estos campos
   - Actualizar generación de planes con GPT

### Prioridad Media:
2. **Dashboard con Visualizaciones**
   - Gráficos de progreso
   - Calendario de entrenamientos
   - Historial de modificaciones visible

3. **Optimización de Tokens**
   - El sistema ya limita historial a 10 mensajes
   - Considerar comprimir contexto
   - Implementar caché de respuestas comunes

### Prioridad Baja:
4. **Testing**
   - Tests unitarios de handlers
   - Tests de integración de API
   - Tests E2E del flujo completo

5. **Deployment**
   - Configurar en Heroku/Railway/Fly.io
   - Cambiar a PostgreSQL en producción
   - Configurar CI/CD

---

## 📞 CONTACTO / NOTAS

**Autor:** Tu equipo de desarrollo  
**Última modificación:** 20 de Octubre de 2025  
**Estado general:** ✅ Sistema de modificaciones 100% funcional, ⚠️ Onboarding básico

### Notas Importantes:
```
1. El sistema de modificaciones dinámicas es el CORE del proyecto y está 100% operativo
2. El onboarding actual es funcional pero básico (falta la versión avanzada)
3. La base de datos está preparada para almacenar todas las modificaciones
4. El sistema detecta cambios automáticamente sin necesidad de comandos especiales
5. Límite de 50 modificaciones en historial (automático)
6. El modelo de IA se selecciona según ENVIRONMENT (dev/prod)
```

---

## 🔍 CÓMO USAR ESTE DOCUMENTO

**Para Claude/AI en futuras conversaciones:**
```
"Hola Claude, aquí está el estado actual de mi proyecto GYMAI.
Por favor, lee el archivo ESTADO_ACTUAL_PROYECTO.md para entender:
- Qué tenemos implementado
- Qué falta por hacer
- Cómo funciona el sistema

[Pegar contenido del archivo o adjuntar]

Mi pregunta es: [tu pregunta específica]"
```

**Para desarrolladores nuevos:**
- Lee este documento completo
- Revisa los archivos marcados con ⭐ (son los más importantes)
- Ejecuta el proyecto localmente
- Prueba el onboarding y el chat de modificaciones

---

## 📋 CHECKLIST DE FUNCIONALIDADES

### Sistema Core:
- [x] Autenticación con JWT
- [x] Base de datos con SQLAlchemy
- [x] Onboarding básico funcional
- [ ] Onboarding avanzado (días + objetivos separados) ⚠️
- [x] Generación de planes con GPT
- [x] Sistema de modificaciones dinámicas ⭐
- [x] Detección automática de cambios ⭐
- [x] Historial de modificaciones
- [x] Validación de alergias
- [x] Integración con Stripe
- [x] Sistema freemium

### Modificaciones de Rutina:
- [x] Adaptar por lesiones
- [x] Enfocar áreas específicas
- [x] Ajustar dificultad
- [x] Sustituir ejercicios
- [x] Adaptar por equipamiento

### Modificaciones de Dieta:
- [x] Recalcular macros por peso
- [x] Recalcular macros por objetivo
- [x] Sustituir alimentos
- [x] Generar alternativas de comidas
- [x] Simplificar plan

### Frontend:
- [x] Login/Registro
- [x] Onboarding básico
- [x] Dashboard
- [x] Vista de rutina
- [x] Chat de modificaciones
- [ ] Calendario de entrenamientos
- [ ] Gráficos de progreso
- [ ] Seguimiento de medidas

---

**FIN DEL DOCUMENTO**

