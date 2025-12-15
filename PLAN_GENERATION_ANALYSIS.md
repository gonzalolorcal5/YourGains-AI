# 📋 ANÁLISIS DEL SISTEMA DE GENERACIÓN DE RUTINAS

**Fecha:** 2024  
**Objetivo:** Documentar el sistema actual antes de implementar "Generar rutina nueva"  
**Estado:** ✅ Análisis completo - NO implementar cambios aún

---

## 1. 🔄 FLUJO ACTUAL DE GENERACIÓN DE PLANES

### 1.1 Endpoints del Backend

#### ✅ **`POST /api/plan/generar-rutina`** (CRÍTICO - NO TOCAR)
- **Ubicación:** `Backend/app/routes/plan.py:107`
- **Función:** Genera un plan completo (rutina + dieta + motivación)
- **Autenticación:** Requiere JWT Bearer token
- **Lógica:**
  - Si usuario es **PREMIUM** → Llama a `generar_plan_personalizado()` (GPT)
  - Si usuario es **FREE** → Llama a `_generar_plan_basico_local()` (template local)
- **Guarda en BD:**
  - Crea un nuevo registro en tabla `planes`
  - **NO actualiza** `Usuario.current_routine` ni `Usuario.current_diet`
- **Retorna:** `PlanResponse` con `rutina`, `dieta`, `motivacion`

#### ✅ **`GET /api/user/current-routine`** (CRÍTICO - NO TOCAR)
- **Ubicación:** `Backend/app/routes/plan.py:199`
- **Función:** Obtiene la rutina y dieta actuales del usuario
- **Parámetros:** `user_id` (query param)
- **Lógica compleja:**
  1. Si usuario es **PREMIUM** y tiene `current_routine` → Usa `Usuario.current_routine` y `Usuario.current_diet`
  2. Si usuario es **PREMIUM** sin `current_routine` → Intenta leer desde último `Plan` en tabla `planes`
  3. Si usuario es **FREE** → Genera template genérico usando `get_generic_plan()`
- **Retorna:** 
  ```json
  {
    "success": true,
    "current_routine": {...},
    "current_diet": {...},
    "user_id": 123,
    "is_premium": true
  }
  ```

#### ✅ **`POST /api/onboarding`** (CRÍTICO - NO TOCAR)
- **Ubicación:** `Backend/app/routes/onboarding.py:40`
- **Función:** Procesa onboarding inicial y genera primer plan
- **Protección:** Solo permite una generación por usuario (verifica si ya existe plan)
- **Lógica:**
  - Si usuario es **PREMIUM** → Llama a `generar_plan_personalizado()` (GPT)
  - Guarda en tabla `planes`
  - Actualiza `Usuario.onboarding_completed = True`
- **Retorna:** Plan completo con `rutina`, `dieta`, `motivacion`

#### ✅ **`POST /api/chat/modify`** (CRÍTICO - NO TOCAR)
- **Ubicación:** `Backend/app/routes/chat_modify_optimized.py:437`
- **Función:** Modifica planes existentes mediante chat
- **Lógica:**
  - Usa OpenAI Function Calling para detectar intención
  - Ejecuta handlers específicos (ej: `handle_modify_routine_injury`, `handle_recalculate_macros`)
  - **Actualiza directamente** `Usuario.current_routine` y `Usuario.current_diet`
  - **NO crea** nuevos registros en tabla `planes`
- **Retorna:** `ChatResponse` con `modified`, `changes`, `function_used`

#### ⚠️ **`GET /api/plan/planes`** (LEGACY - Revisar)
- **Ubicación:** `Backend/app/routes/plan.py:165`
- **Función:** Obtiene planes del usuario
- **Nota:** Actualmente devuelve `current_routine` y `current_diet` desde `Usuario`, no desde tabla `planes`
- **Estado:** Parece ser un endpoint legacy que mantiene compatibilidad

---

## 2. 📊 ESTRUCTURA DE BASE DE DATOS

### 2.1 Tabla `usuarios`

**Campos relevantes para generación de planes:**

```python
class Usuario(Base):
    id: int                          # PK
    email: str                       # Único
    is_premium: bool                 # Legacy - usar plan_type
    plan_type: str                   # "FREE" | "PREMIUM_MONTHLY" | "PREMIUM_YEARLY"
    
    # Campos dinámicos (JSON almacenado como Text)
    current_routine: Text            # JSON string → formato current_routine
    current_diet: Text               # JSON string → formato current_diet
    injuries: Text                   # JSON array
    focus_areas: Text                # JSON array
    disliked_foods: Text            # JSON array
    modification_history: Text       # JSON array
    
    # Onboarding
    onboarding_completed: bool
```

**⚠️ IMPORTANTE:**
- `current_routine` y `current_diet` son **Text** (JSON serializado)
- Se actualizan dinámicamente por el chat
- Son la **fuente de verdad** para usuarios PREMIUM

### 2.2 Tabla `planes`

**Campos relevantes:**

```python
class Plan(Base):
    id: int                          # PK
    user_id: int                     # FK → usuarios.id
    
    # Datos físicos del usuario (se pueden modificar)
    altura: int                      # cm
    peso: String                     # kg (String porque puede tener decimales)
    edad: int
    sexo: str                       # "masculino" | "femenino"
    experiencia: str                # "principiante" | "intermedio" | "avanzado"
    
    # Objetivos (se pueden modificar)
    objetivo: str                   # Legacy
    objetivo_gym: str              # "ganar_musculo" | "ganar_fuerza" | "mantener_forma"
    objetivo_dieta: str            # Legacy
    objetivo_nutricional: str      # "volumen" | "definicion" | "mantenimiento" | "recomposicion"
    
    # Configuración de entrenamiento (se pueden modificar)
    materiales: str                # "gym_completo" | "casa" | "peso_libre" | etc.
    tipo_cuerpo: str               # "ectomorfo" | "mesomorfo" | "endomorfo"
    nivel_actividad: str           # "sedentario" | "ligero" | "moderado" | "activo" | "muy_activo"
    dias_entrenamiento: int        # ⚠️ INVESTIGAR: No está en models.py pero aparece en schemas.py
    
    # Preferencias y restricciones (se pueden modificar)
    puntos_fuertes: str
    puntos_debiles: str
    entrenar_fuerte: str
    lesiones: str
    alergias: str
    restricciones_dieta: str
    
    # Planes generados (NO se modifican directamente)
    rutina: Text                   # JSON string → formato GPT (dias[])
    dieta: Text                    # JSON string → formato GPT (comidas[])
    motivacion: Text
    
    fecha_creacion: DateTime
```

**⚠️ DIFERENCIAS CLAVE:**
- Tabla `planes` guarda **historial** de planes generados
- `Usuario.current_routine` y `Usuario.current_diet` son la **versión activa** (para PREMIUM)
- Los formatos JSON son **diferentes**:
  - `Plan.rutina` → Formato GPT: `{"dias": [{"dia": "lunes", "ejercicios": [...]}]}`
  - `Usuario.current_routine` → Formato frontend: `{"exercises": [...], "schedule": {}}`

---

## 3. 🤖 DATOS QUE ACEPTA GPT

### 3.1 Función: `generar_plan_personalizado(datos: Dict[str, Any])`

**Ubicación:** `Backend/app/utils/gpt.py:325`

**Parámetros esperados (según código actual):**

```python
datos = {
    # Datos físicos (OBLIGATORIOS)
    'sexo': str,                    # "masculino" | "femenino"
    'altura': int,                  # cm
    'peso': float,                  # kg
    'edad': int,
    
    # Objetivos (OBLIGATORIOS)
    'gym_goal': str,                # "ganar_musculo" | "ganar_fuerza" | "perder_grasa" | "mantener_forma"
    'nutrition_goal': str,          # "volumen" | "definicion" | "mantenimiento" | "recomposicion"
    
    # Experiencia y configuración (OBLIGATORIOS)
    'experiencia': str,             # "principiante" | "intermedio" | "avanzado"
    'materiales': str,              # "gym_completo" | "casa" | "peso_libre" | etc.
    'nivel_actividad': str,         # "sedentario" | "ligero" | "moderado" | "activo" | "muy_activo"
    
    # Frecuencia de entrenamiento (OBLIGATORIO)
    'training_frequency': int,      # Días por semana (ej: 4)
    'training_days': List[str],     # ["lunes", "martes", "jueves", "viernes"]
    
    # Opcionales
    'tipo_cuerpo': str,            # "ectomorfo" | "mesomorfo" | "endomorfo"
    'alergias': str,                # "Ninguna" | "lactosa, gluten"
    'restricciones': str,           # "Ninguna" | "vegetariano"
    'lesiones': str,                # "Ninguna" | "rodilla, hombro"
    'idioma': str,                  # "es" | "en" (default: "es")
    
    # ⚠️ INVESTIGAR: Estos campos aparecen en PlanRequest pero no siempre se pasan a GPT
    'puntos_fuertes': str,
    'puntos_debiles': str,
    'entrenar_fuerte': str,
}
```

### 3.2 Datos que se pueden modificar en el formulario

**✅ Modificables (están en tabla `Plan`):**
- `altura` (int)
- `peso` (String/float)
- `edad` (int)
- `sexo` (str)
- `experiencia` (str)
- `objetivo_gym` (str)
- `objetivo_nutricional` (str)
- `materiales` (str)
- `tipo_cuerpo` (str)
- `nivel_actividad` (str)
- `lesiones` (str)
- `alergias` (str)
- `restricciones_dieta` (str)
- `puntos_fuertes` (str)
- `puntos_debiles` (str)
- `entrenar_fuerte` (str)

**⚠️ INVESTIGAR:**
- `dias_entrenamiento` (int) - Aparece en `PlanRequest` pero no en `models.Plan`
- `training_frequency` y `training_days` - No están en BD, se calculan o se pasan directamente a GPT

### 3.3 Datos NO en BD (contextuales/temporales)

**Estos datos NO se guardan pero se pueden pasar a GPT:**
- `training_frequency` - Se calcula o se pregunta al usuario
- `training_days` - Lista de días específicos (ej: ["lunes", "martes"])
- Preferencias de horario (mañana/tarde/noche) - ⚠️ INVESTIGAR si se usa
- Máquinas disponibles específicas - ⚠️ INVESTIGAR si se diferencia de `materiales`

---

## 4. 📐 ESTRUCTURA DE DATOS ACTUAL

### 4.1 Formato `current_routine` (Usuario.current_routine)

```json
{
  "exercises": [
    {
      "name": "Sentadilla",
      "sets": 3,
      "reps": "8-10",
      "weight": "moderado",
      "day": "lunes"
    },
    // ... más ejercicios
  ],
  "schedule": {},
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00",
  "version": "1.0.0",
  "is_generic": false,              // Solo para FREE
  "titulo": "Rutina Personalizada"  // Opcional
}
```

**Validación:** `Backend/app/utils/json_helpers.py:16-25`

### 4.2 Formato `current_diet` (Usuario.current_diet)

```json
{
  "meals": [
    {
      "nombre": "Desayuno",
      "kcal": 450,
      "alimentos": [
        "250ml leche",
        "40g avena",
        "1 plátano"
      ],
      "macros": {
        "proteinas": 30,
        "hidratos": 55,
        "grasas": 12
      }
    },
    // ... más comidas
  ],
  "total_kcal": 2500,
  "macros": {
    "proteina": 150.0,
    "carbohidratos": 300.0,
    "grasas": 80.0
  },
  "objetivo": "volumen",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00",
  "version": "1.0.0",
  "is_generic": false,              // Solo para FREE
  "titulo": "Plan Nutricional"      // Opcional
}
```

**Validación:** `Backend/app/utils/json_helpers.py:27-38`

### 4.3 Formato GPT `rutina` (Plan.rutina)

```json
{
  "dias": [
    {
      "dia": "lunes",
      "nombre": "Día 1 - Tren Superior",
      "ejercicios": [
        {
          "nombre": "Press banca",
          "series": 4,
          "repeticiones": "8-10",
          "descanso": "90s",
          "notas": "Controlar la fase excéntrica"
        },
        // ... más ejercicios
      ]
    },
    // ... más días
  ],
  "consejos": [
    "Calienta 10 min antes",
    "Progresión: añade peso si completas el rango"
  ],
  "titulo": "Rutina de Hipertrofia"
}
```

### 4.4 Formato GPT `dieta` (Plan.dieta)

```json
{
  "comidas": [
    {
      "nombre": "Desayuno",
      "kcal": 450,
      "macros": {
        "proteinas": 30,
        "hidratos": 55,
        "grasas": 12
      },
      "alimentos": [
        "250ml leche o bebida vegetal",
        "40g avena",
        "1 plátano",
        "10g mantequilla cacahuete"
      ],
      "alternativas": [
        "Yogur con frutos rojos y avena"
      ]
    },
    // ... más comidas
  ],
  "macros": {
    "proteina": 150.0,
    "carbohidratos": 300.0,
    "grasas": 80.0,
    "calorias": 2500
  },
  "metadata": {
    "calorias_objetivo": 2500,
    "macros_objetivo": {
      "proteina": 150.0,
      "carbohidratos": 300.0,
      "grasas": 80.0
    }
  },
  "resumen": "Plan nutricional para volumen muscular"
}
```

**⚠️ CONVERSIÓN CRÍTICA:**
- GPT devuelve formato `dias[]` y `comidas[]`
- Frontend espera formato `exercises[]` y `meals[]`
- La conversión se hace en:
  - `Backend/app/routes/stripe_webhook.py:69-87` (para current_routine)
  - `Backend/app/routes/stripe_webhook.py:89-120` (para current_diet)
  - `Backend/app/routes/plan.py:352-433` (fallback para premium sin current_routine)

---

## 5. 🎨 FUNCIONES FRONTEND CRÍTICAS

### 5.1 `loadUserPlans()` (CRÍTICO - NO TOCAR)

**Ubicación:** `Backend/app/frontend/dashboard.html:2467`

**Función:**
```javascript
async function loadUserPlans() {
    const userId = getCurrentUserId();
    const response = await fetch(`${API_BASE}/user/current-routine?user_id=${userId}`);
    const data = await response.json();
    
    if (data.success && data.current_routine) {
        const plan = {
            rutina: data.current_routine,
            dieta: data.current_diet,
            motivacion: "Rutina actualizada dinámicamente"
        };
        displayPlan(plan, data.is_premium);
    }
}
```

**⚠️ IMPORTANTE:**
- Se llama automáticamente al cargar el dashboard
- Crea un objeto `plan` compatible con `displayPlan()`
- Usa `current_routine` y `current_diet` del endpoint

### 5.2 `displayPlan(plan, isPremium)` (CRÍTICO - REUTILIZAR)

**Ubicación:** `Backend/app/frontend/dashboard.html` (buscar función)

**Función:**
- Renderiza la rutina y dieta en el overlay `rutinaDietaOverlay`
- Recibe objeto `plan` con estructura:
  ```javascript
  {
    rutina: current_routine,  // Formato exercises[]
    dieta: current_diet,       // Formato meals[]
    motivacion: string
  }
  ```
- Muestra diferente contenido según `isPremium`

**✅ REUTILIZAR:** Esta función puede usarse después de generar nueva rutina

### 5.3 `sendMessage()` (CRÍTICO - NO TOCAR)

**Ubicación:** `Backend/app/frontend/dashboard.html:2103`

**Función:**
- Envía mensajes al chat `/api/chat/modify`
- Maneja modificaciones dinámicas de planes
- Actualiza UI después de modificaciones exitosas

**⚠️ NO INTERFERIR:** El nuevo formulario no debe interferir con el chat

### 5.4 `reloadPlan()` (CRÍTICO - REUTILIZAR)

**Ubicación:** `Backend/app/frontend/dashboard.html:2390`

**Función:**
- Recarga el plan actual desde el servidor
- Llama a `loadUserPlans()` y actualiza visualización
- Muestra notificación de éxito

**✅ REUTILIZAR:** Llamar después de generar nueva rutina

---

## 6. 🔌 PUNTOS DE INTEGRACIÓN

### 6.1 Dónde mostrar el formulario

**Opción recomendada:** Overlay similar a `rutinaDietaOverlay` y `consejosEstudiosOverlay`

**Estructura sugerida:**
```html
<div class="overlay" id="nuevaRutinaOverlay">
    <div class="min-h-screen bg-neutral-950">
        <!-- Header con logo y X -->
        <header>...</header>
        
        <!-- Formulario -->
        <main>
            <form id="nuevaRutinaForm">
                <!-- Campos del formulario -->
            </form>
        </main>
    </div>
</div>
```

**Botón para abrir:**
- Añadir botón en el dashboard principal
- O añadir opción en el menú superior
- O añadir botón dentro de `rutinaDietaOverlay`

### 6.2 Contenedor del formulario

**ID sugerido:** `#nuevaRutinaForm` o `#generarRutinaForm`

**Ubicación en DOM:** Dentro de `#nuevaRutinaOverlay`

### 6.3 Reutilizar `displayPlan()`

**Flujo:**
1. Usuario completa formulario
2. Enviar datos a nuevo endpoint (ej: `POST /api/plan/generar-rutina-nueva`)
3. Backend genera plan con GPT
4. Backend actualiza `Usuario.current_routine` y `Usuario.current_diet`
5. Backend retorna plan generado
6. Frontend llama a `displayPlan(plan, isPremium)`
7. Cerrar overlay de formulario
8. Abrir overlay `rutinaDietaOverlay` con nueva rutina

**Código sugerido:**
```javascript
async function generarNuevaRutina(formData) {
    const response = await fetch(`${API_BASE}/plan/generar-rutina-nueva`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${getToken()}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    });
    
    const data = await response.json();
    
    if (data.success) {
        const plan = {
            rutina: data.current_routine,
            dieta: data.current_diet,
            motivacion: data.motivacion || "Nueva rutina generada"
        };
        
        // Cerrar overlay de formulario
        closeOverlay('nuevaRutinaOverlay');
        
        // Mostrar nueva rutina
        openOverlay('rutinaDietaOverlay');
        displayPlan(plan, data.is_premium);
        
        // Mostrar notificación
        showReloadNotification('Nueva rutina generada exitosamente');
    }
}
```

---

## 7. ⚠️ RESTRICCIONES Y CUIDADOS

### 7.1 Conflictos con el chat actual

**⚠️ PROBLEMA POTENCIAL:**
- El chat modifica `current_routine` y `current_diet` dinámicamente
- Si generamos nueva rutina, **sobrescribimos** los cambios del chat
- El usuario podría perder modificaciones recientes

**✅ SOLUCIÓN:**
- Mostrar advertencia antes de generar: "¿Estás seguro? Esto reemplazará tu rutina actual"
- O guardar backup en `modification_history` antes de generar
- O crear nuevo endpoint que **añada** al historial en lugar de sobrescribir

### 7.2 Sistema Freemium

**⚠️ PROBLEMA POTENCIAL:**
- Usuarios FREE no pueden usar GPT
- El endpoint `/generar-rutina` ya tiene lógica para FREE (template local)
- ¿Permitimos que FREE genere "nueva rutina" con template?

**✅ SOLUCIÓN:**
- Si usuario es FREE → Mostrar mensaje: "Esta función es solo para usuarios Premium"
- O permitir generar con template local (menos personalizado)
- Verificar `plan_type` antes de mostrar botón de "Generar nueva rutina"

### 7.3 Cachés del navegador

**⚠️ PROBLEMA POTENCIAL:**
- `loadUserPlans()` podría cachear datos antiguos
- Después de generar nueva rutina, el frontend podría mostrar datos viejos

**✅ SOLUCIÓN:**
- Llamar a `reloadPlan()` después de generar
- O forzar refresh del endpoint con timestamp: `?t=${Date.now()}`
- Invalidar cualquier caché local antes de mostrar nueva rutina

### 7.4 Estado del usuario (sesión, autenticación)

**⚠️ PROBLEMA POTENCIAL:**
- Token JWT podría expirar durante la generación (puede tardar 30-60s)
- Usuario podría cerrar sesión mientras se genera

**✅ SOLUCIÓN:**
- Verificar token antes de enviar formulario
- Mostrar loading state durante generación
- Manejar errores 401/403 y redirigir a login si es necesario
- Usar timeout adecuado en fetch (ej: 120s para GPT)

### 7.5 Conversión de formatos

**⚠️ PROBLEMA POTENCIAL:**
- GPT devuelve formato `dias[]` y `comidas[]`
- Frontend espera `exercises[]` y `meals[]`
- La conversión debe hacerse correctamente

**✅ SOLUCIÓN:**
- Reutilizar lógica de conversión existente:
  - `Backend/app/routes/stripe_webhook.py:69-120`
  - O crear función helper compartida: `convert_gpt_plan_to_current_format()`

### 7.6 Actualización de tabla `planes`

**⚠️ INVESTIGAR:**
- ¿Debemos crear nuevo registro en tabla `planes` al generar nueva rutina?
- ¿O solo actualizar `Usuario.current_routine` y `Usuario.current_diet`?
- El endpoint `/generar-rutina` actual **SÍ crea** registro en `planes`
- El chat **NO crea** registro en `planes`

**✅ RECOMENDACIÓN:**
- Crear nuevo registro en `planes` para mantener historial
- Actualizar `Usuario.current_routine` y `Usuario.current_diet` para versión activa
- Esto permite al usuario ver historial de planes generados

### 7.7 Campos faltantes en formulario

**⚠️ INVESTIGAR:**
- `dias_entrenamiento` aparece en `PlanRequest` pero no en `models.Plan`
- `training_frequency` y `training_days` no están en BD
- ¿Cómo obtener estos datos del usuario actual?

**✅ SOLUCIÓN:**
- Preguntar en el formulario: "¿Cuántos días quieres entrenar por semana?"
- Calcular `training_days` automáticamente según frecuencia
- O permitir seleccionar días específicos en el formulario

### 7.8 Validación de datos

**⚠️ PROBLEMA POTENCIAL:**
- Usuario podría enviar datos inválidos (peso negativo, edad imposible, etc.)
- GPT podría fallar con datos inconsistentes

**✅ SOLUCIÓN:**
- Validar en frontend antes de enviar
- Validar en backend usando Pydantic (`PlanRequest`)
- Mostrar errores claros al usuario

---

## 8. 🔍 PUNTOS A INVESTIGAR

### 8.1 ⚠️ Campo `dias_entrenamiento`

**Pregunta:** ¿Existe en la BD o solo en `PlanRequest`?

**Ubicación:** 
- `Backend/app/schemas.py:14` → `PlanRequest.dias_entrenamiento: int`
- `Backend/app/models.py` → **NO aparece en `Plan`**

**Acción:** Verificar si se usa o si es legacy

### 8.2 ⚠️ Cálculo de `training_frequency` y `training_days`

**Pregunta:** ¿Cómo se obtienen estos valores actualmente?

**Ubicación:**
- `Backend/app/routes/stripe_webhook.py:58` → `'training_frequency': 4` (hardcoded)
- `Backend/app/routes/stripe_webhook.py:59` → `'training_days': ['lunes', 'martes', 'jueves', 'viernes']` (hardcoded)

**Acción:** Determinar si debemos preguntar al usuario o calcular automáticamente

### 8.3 ⚠️ Preferencias de horario

**Pregunta:** ¿Se usa información de horario preferido para generar rutinas?

**Acción:** Buscar en código si existe lógica relacionada

### 8.4 ⚠️ Máquinas disponibles específicas

**Pregunta:** ¿`materiales` es suficiente o necesitamos más detalle?

**Acción:** Verificar si GPT usa información más específica de equipamiento

### 8.5 ⚠️ Endpoint `/api/plan/planes` (LEGACY)

**Pregunta:** ¿Se usa actualmente o es código legacy?

**Acción:** Verificar si el frontend llama a este endpoint

---

## 9. 📝 RESUMEN EJECUTIVO

### 9.1 Flujo actual

1. **Onboarding inicial** → `POST /api/onboarding` → Genera plan → Guarda en `planes`
2. **Modificaciones via chat** → `POST /api/chat/modify` → Actualiza `Usuario.current_routine/diet`
3. **Visualización** → `GET /api/user/current-routine` → Lee `Usuario.current_routine/diet` (PREMIUM) o genera template (FREE)

### 9.2 Flujo propuesto (NUEVA FUNCIONALIDAD)

1. **Usuario hace click en "Generar rutina nueva"**
2. **Se abre overlay con formulario** (pre-llenado con datos actuales)
3. **Usuario modifica campos deseados**
4. **Frontend envía a nuevo endpoint** → `POST /api/plan/generar-rutina-nueva`
5. **Backend genera plan con GPT** (usando `generar_plan_personalizado()`)
6. **Backend actualiza:**
   - Crea nuevo registro en `planes` (historial)
   - Actualiza `Usuario.current_routine` y `Usuario.current_diet` (versión activa)
7. **Backend retorna plan generado**
8. **Frontend muestra nueva rutina** usando `displayPlan()`

### 9.3 Endpoints a crear

**NUEVO:** `POST /api/plan/generar-rutina-nueva`
- Similar a `/generar-rutina` pero:
  - Pre-llena datos desde último `Plan` o `Usuario`
  - Permite modificar solo campos seleccionados
  - Actualiza `Usuario.current_routine/diet` además de crear `Plan`
  - Retorna formato compatible con `displayPlan()`

### 9.4 Funciones a crear/modificar

**NUEVO (Frontend):**
- `openNuevaRutinaForm()` - Abre overlay con formulario
- `generarNuevaRutina(formData)` - Envía datos y muestra resultado
- `prefillFormWithCurrentData()` - Pre-llena formulario con datos actuales

**MODIFICAR (Backend):**
- Crear endpoint `POST /api/plan/generar-rutina-nueva`
- Reutilizar `generar_plan_personalizado()` de `gpt.py`
- Reutilizar lógica de conversión de formatos

**REUTILIZAR (Frontend):**
- `displayPlan()` - Para mostrar nueva rutina
- `reloadPlan()` - Para refrescar después de generar
- `closeOverlay()` / `openOverlay()` - Para navegación

---

## 10. ✅ CHECKLIST DE IMPLEMENTACIÓN

### Fase 1: Backend
- [ ] Crear endpoint `POST /api/plan/generar-rutina-nueva`
- [ ] Implementar función para obtener datos actuales del usuario
- [ ] Implementar función para pre-llenar datos del formulario
- [ ] Reutilizar `generar_plan_personalizado()` para generar plan
- [ ] Implementar conversión de formato GPT → current_routine/diet
- [ ] Actualizar `Usuario.current_routine` y `Usuario.current_diet`
- [ ] Crear nuevo registro en tabla `planes` (historial)
- [ ] Validar datos con Pydantic
- [ ] Manejar errores y timeouts de GPT

### Fase 2: Frontend
- [ ] Crear overlay `nuevaRutinaOverlay` en `dashboard.html`
- [ ] Crear formulario con todos los campos modificables
- [ ] Implementar `prefillFormWithCurrentData()` para pre-llenar
- [ ] Implementar `generarNuevaRutina()` para enviar datos
- [ ] Añadir botón "Generar rutina nueva" en dashboard
- [ ] Mostrar loading state durante generación
- [ ] Manejar errores y mostrar mensajes al usuario
- [ ] Integrar con `displayPlan()` para mostrar resultado
- [ ] Añadir confirmación antes de sobrescribir rutina actual

### Fase 3: Testing
- [ ] Probar con usuario PREMIUM
- [ ] Probar con usuario FREE (debe mostrar mensaje o usar template)
- [ ] Probar con datos inválidos
- [ ] Probar timeout de GPT
- [ ] Verificar que no se rompe el chat actual
- [ ] Verificar que se mantiene historial en tabla `planes`
- [ ] Verificar conversión de formatos correcta

---

**FIN DEL ANÁLISIS** ✅

**Próximos pasos:** Revisar este documento y comenzar implementación según checklist.

