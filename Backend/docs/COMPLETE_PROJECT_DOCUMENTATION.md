# DOCUMENTACIÓN TÉCNICA COMPLETA - YOURGAINS AI

**Versión:** 1.0  
**Fecha:** Enero 2026  
**Propósito:** Documentación exhaustiva para revisión legal, técnica y de configuración antes del lanzamiento en producción

---

## ÍNDICE

1. [Arquitectura General](#1-arquitectura-general)
2. [Base de Datos](#2-base-de-datos)
3. [Modelos de IA y RAG](#3-modelos-de-ia-y-rag)
4. [Sistema Freemium](#4-sistema-freemium)
5. [Autenticación y Seguridad](#5-autenticación-y-seguridad)
6. [Stripe y Pagos](#6-stripe-y-pagos)
7. [Términos y Políticas](#7-términos-y-políticas)
8. [Google Analytics](#8-google-analytics)
9. [Variables de Entorno](#9-variables-de-entorno)
10. [Preparación para Producción](#10-preparación-para-producción)
11. [Puntos Críticos para Revisión](#11-puntos-críticos-para-revisión)

---

## 1. ARQUITECTURA GENERAL

### 1.1 STACK TECNOLÓGICO

#### Backend
- **Lenguaje:** Python 3.13
- **Framework:** FastAPI 0.116.1
- **ORM:** SQLAlchemy 2.0.43
- **Base de datos:** SQLite (desarrollo) / PostgreSQL (producción recomendado)
- **Autenticación:** JWT (python-jose 3.5.0)
- **Hashing:** bcrypt 4.3.0 (passlib 1.7.4)
- **HTTP Client:** httpx 0.28.1
- **Servidor ASGI:** Uvicorn 0.35.0

#### Frontend
- **Tecnologías:** HTML5, CSS3, JavaScript (Vanilla)
- **Sin frameworks:** No usa React, Vue, Angular
- **Estilos:** CSS inline y clases personalizadas
- **Librerías externas:**
  - Tailwind CSS (CDN) - Solo en términos y políticas
  - Google Fonts (Inter)

#### Base de Datos
- **Tipo:** SQLite (archivo `gymai.db`)
- **Ubicación:** `Backend/gymai.db`
- **ORM:** SQLAlchemy con modelos declarativos
- **Migraciones:** Sistema manual en `app/migrations/`

#### APIs Externas
- **OpenAI:** GPT-4o para generación de planes y chat
- **Stripe:** Procesamiento de pagos y suscripciones
- **Google OAuth:** Autenticación social
- **Supabase:** Base de datos vectorial para RAG (opcional, solo si se usa)

#### Hosting
- **Plataforma:** Railway (configurado)
- **Archivo de configuración:** `Procfile`
- **Variables de entorno:** Configuradas en Railway dashboard

### 1.2 ESTRUCTURA DE ARCHIVOS

```
Backend/
├── app/
│   ├── main.py                    # Punto de entrada FastAPI, configuración de rutas
│   ├── models.py                  # Modelos SQLAlchemy (Usuario, Plan)
│   ├── database.py               # Configuración de BD y sesiones
│   ├── auth_utils.py              # Utilidades JWT, hashing, get_current_user
│   ├── schemas.py                 # Pydantic schemas para validación
│   │
│   ├── routes/                    # Endpoints de la API
│   │   ├── auth.py               # POST /register, POST /login
│   │   ├── oauth.py              # GET /auth/google/login, GET /auth/google/callback
│   │   ├── user_status.py        # GET /user/status, GET /api/user/me
│   │   ├── plan.py                # POST /plan/generate, GET /plan/current
│   │   ├── chat.py                # POST /api/chat, POST /api/chat/modify
│   │   ├── onboarding.py          # POST /onboarding/complete
│   │   ├── stripe_routes.py      # POST /create-checkout-session, GET /config
│   │   ├── stripe_webhook.py     # POST /stripe/webhook (webhooks de Stripe)
│   │   └── analisis_cuerpo.py    # Endpoints de análisis corporal
│   │
│   ├── utils/                     # Utilidades del sistema
│   │   ├── gpt.py                 # Generación de planes con GPT-4o + RAG
│   │   ├── vectorstore.py        # Cliente para base de conocimiento vectorial
│   │   ├── supa_client.py        # Cliente HTTP para Supabase
│   │   ├── embeddings.py          # Generación de embeddings
│   │   ├── nutrition_calculator.py # Cálculo de macros y calorías
│   │   ├── routine_templates.py   # Plantillas de rutina para usuarios FREE
│   │   ├── pdf_generator.py       # Generación de PDFs de rutina
│   │   └── json_helpers.py        # Helpers para serialización JSON
│   │
│   ├── routers/                   # Routers adicionales
│   │   └── rag.py                 # Endpoints relacionados con RAG
│   │
│   ├── frontend/                  # Archivos HTML/JS del frontend
│   │   ├── dashboard.html         # Dashboard principal (8000+ líneas)
│   │   ├── login.html             # Página de login
│   │   ├── onboarding.html        # Formulario de onboarding
│   │   ├── tarifas.html           # Página de precios
│   │   ├── terms.html             # Términos y condiciones
│   │   ├── privacy.html           # Política de privacidad
│   │   ├── auth.js                # Lógica de autenticación frontend
│   │   └── config.js               # Configuración de API base
│   │
│   └── knowledge/                 # Base de conocimiento JSON (46 archivos)
│       ├── hipertrofia_basica.json
│       ├── sintesis_proteica.json
│       └── [44 archivos más...]
│
├── static/                        # Archivos estáticos
│   ├── cookie-consent.js          # Gestor de consentimiento de cookies
│   ├── cookies.html               # Página de información de cookies
│   └── public/                    # Imágenes públicas (logo, hero, etc.)
│
├── scripts/                       # Scripts de utilidad
│   ├── check_stripe_subscription.py # Verificar estado de suscripciones
│   └── clean_stripe_ids.py        # Limpiar IDs de Stripe obsoletos
│
├── .env                           # Variables de entorno (NO incluir en git)
├── requirements.txt               # Dependencias Python
├── Procfile                       # Configuración Railway
└── gymai.db                       # Base de datos SQLite
```

### 1.3 DESCRIPCIÓN DE ARCHIVOS PRINCIPALES

#### `app/main.py`
- **Función:** Punto de entrada de FastAPI
- **Responsabilidades:**
  - Configuración de CORS
  - Registro de routers
  - Servir archivos HTML/JS estáticos
  - Middleware anti-caché para archivos públicos
  - Health checks (`/ping`, `/_ping`)

#### `app/routes/auth.py`
- **Endpoints:**
  - `POST /register` - Registro de usuario con email/password
  - `POST /login` - Login tradicional, retorna JWT token
- **Funcionalidad:** Autenticación básica, validación de OAuth puro, generación de tokens JWT

#### `app/routes/oauth.py`
- **Endpoints:**
  - `GET /auth/google/login` - Inicia flujo OAuth de Google
  - `GET /auth/google/callback` - Procesa callback de Google
- **Funcionalidad:** Autenticación social, vinculación de cuentas, creación automática de usuarios

#### `app/routes/user_status.py`
- **Endpoints:**
  - `GET /user/status?email=...` - Verifica estado de usuario (crea si no existe)
  - `GET /api/user/me` - Obtiene datos completos del usuario actual (requiere JWT)
- **Funcionalidad:** Verificación de estado premium, creación automática de usuarios

#### `app/routes/stripe_routes.py`
- **Endpoints:**
  - `POST /create-checkout-session` - Crea sesión de Stripe Checkout
  - `GET /config` - Retorna configuración pública de Stripe (publishable key)
  - `POST /activate-premium` - Activa premium manualmente (desarrollo)
- **Funcionalidad:** Gestión de checkout, creación de customers, activación de premium

#### `app/routes/stripe_webhook.py`
- **Endpoints:**
  - `POST /stripe/webhook` - Recibe webhooks de Stripe
- **Eventos manejados:**
  - `checkout.session.completed`
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `payment_intent.succeeded`
- **Funcionalidad:** Sincronización automática de estado premium, generación de planes con IA

#### `app/routes/chat.py`
- **Endpoints:**
  - `POST /api/chat` - Chat con IA (streaming)
  - `POST /api/chat/modify` - Modificar rutina/dieta existente
- **Funcionalidad:** Chat con GPT-4o, integración RAG, límites para usuarios FREE

#### `app/routes/plan.py`
- **Endpoints:**
  - `POST /plan/generate` - Genera nuevo plan (FREE o PREMIUM)
  - `GET /plan/current` - Obtiene plan actual del usuario
  - `GET /plan/pdf` - Genera PDF de la rutina
- **Funcionalidad:** Generación de planes, diferenciación FREE vs PREMIUM

#### `app/models.py`
- **Clases:**
  - `Usuario` - Modelo de usuario con todos los campos
  - `Plan` - Modelo de plan histórico
- **Relaciones:** Usuario 1:N Plan

#### `app/database.py`
- **Función:** Configuración de SQLAlchemy
- **Responsabilidades:**
  - Creación de engine
  - SessionLocal factory
  - Creación automática de tablas

---

## 2. BASE DE DATOS

### 2.1 ESTRUCTURA COMPLETA

#### Tabla: `usuarios`

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | ID único del usuario |
| `email` | VARCHAR | UNIQUE, NOT NULL, INDEX | Email del usuario (único) |
| `hashed_password` | VARCHAR | NULLABLE | Contraseña hasheada con bcrypt (NULL si solo OAuth) |
| `google_id` | VARCHAR | NULLABLE | ID de Google OAuth |
| `oauth_provider` | VARCHAR | NULLABLE | Proveedor OAuth ('google' o NULL) |
| `profile_picture` | VARCHAR | NULLABLE | URL de foto de perfil (Google) |
| `is_premium` | BOOLEAN | NOT NULL, DEFAULT FALSE | Estado premium (TRUE/FALSE) |
| `stripe_customer_id` | VARCHAR | NULLABLE | ID de customer en Stripe |
| `stripe_subscription_id` | VARCHAR | NULLABLE | ID de suscripción en Stripe |
| `plan_type` | VARCHAR | NOT NULL, DEFAULT 'FREE' | Tipo de plan: 'FREE', 'PREMIUM_MONTHLY', 'PREMIUM_YEARLY' |
| `chat_uses_free` | INTEGER | NOT NULL, DEFAULT 2 | Preguntas gratis restantes (solo FREE) |
| `onboarding_completed` | BOOLEAN | NOT NULL, DEFAULT FALSE | Si completó el onboarding |
| `current_routine` | TEXT | NOT NULL, DEFAULT '{}' | Rutina actual en JSON |
| `current_diet` | TEXT | NOT NULL, DEFAULT '{}' | Dieta actual en JSON |
| `injuries` | TEXT | NOT NULL, DEFAULT '[]' | Lesiones en JSON array |
| `focus_areas` | TEXT | NOT NULL, DEFAULT '[]' | Áreas de enfoque en JSON array |
| `disliked_foods` | TEXT | NOT NULL, DEFAULT '[]' | Alimentos no deseados en JSON array |
| `modification_history` | TEXT | NOT NULL, DEFAULT '[]' | Historial de modificaciones en JSON |
| `is_generating_plan` | BOOLEAN | NOT NULL, DEFAULT FALSE | Lock para evitar generaciones duplicadas |

**Índices:**
- `id` (PRIMARY KEY)
- `email` (UNIQUE INDEX)

**Relaciones:**
- `usuarios.id` → `planes.user_id` (1:N)

#### Tabla: `planes`

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO_INCREMENT | ID único del plan |
| `user_id` | INTEGER | FOREIGN KEY → usuarios.id | Usuario propietario |
| `altura` | INTEGER | NOT NULL | Altura en cm |
| `peso` | VARCHAR | NOT NULL | Peso (puede ser rango) |
| `edad` | INTEGER | NOT NULL | Edad del usuario |
| `sexo` | VARCHAR | NOT NULL | 'M' o 'F' |
| `experiencia` | VARCHAR | NOT NULL | Nivel de experiencia |
| `objetivo` | VARCHAR | NOT NULL | Objetivo legacy |
| `objetivo_gym` | VARCHAR | NULLABLE | Objetivo de entrenamiento |
| `objetivo_dieta` | VARCHAR | NULLABLE | Objetivo nutricional legacy |
| `objetivo_nutricional` | VARCHAR | NULLABLE | Objetivo nutricional actual |
| `materiales` | VARCHAR | NOT NULL | Materiales disponibles |
| `tipo_cuerpo` | VARCHAR | NULLABLE | Tipo de cuerpo |
| `nivel_actividad` | VARCHAR | NOT NULL, DEFAULT 'moderado' | Nivel de actividad física |
| `idioma` | VARCHAR | DEFAULT 'es' | Idioma del plan |
| `puntos_fuertes` | VARCHAR | NULLABLE | Puntos fuertes del usuario |
| `puntos_debiles` | VARCHAR | NULLABLE | Puntos débiles |
| `entrenar_fuerte` | VARCHAR | NULLABLE | Días de entrenamiento fuerte |
| `lesiones` | VARCHAR | NULLABLE | Lesiones del usuario |
| `alergias` | VARCHAR | NULLABLE | Alergias alimentarias |
| `restricciones_dieta` | VARCHAR | NULLABLE | Restricciones dietéticas |
| `rutina` | TEXT | NOT NULL | Rutina en JSON |
| `dieta` | TEXT | NOT NULL | Dieta en JSON |
| `motivacion` | TEXT | NOT NULL | Mensaje motivacional |
| `fecha_creacion` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Fecha de creación |

**Índices:**
- `id` (PRIMARY KEY)
- `user_id` (FOREIGN KEY INDEX)

**Relaciones:**
- `planes.user_id` → `usuarios.id` (N:1)

### 2.2 ESQUEMA VISUAL

```
usuarios
├── id (PK)
├── email (UNIQUE)
├── hashed_password
├── google_id
├── oauth_provider
├── profile_picture
├── is_premium
├── stripe_customer_id
├── stripe_subscription_id
├── plan_type
├── chat_uses_free
├── onboarding_completed
├── current_routine (JSON)
├── current_diet (JSON)
├── injuries (JSON)
├── focus_areas (JSON)
├── disliked_foods (JSON)
├── modification_history (JSON)
└── is_generating_plan
    │
    └── 1:N → planes
        ├── id (PK)
        ├── user_id (FK)
        ├── altura
        ├── peso
        ├── edad
        ├── sexo
        ├── experiencia
        ├── objetivo_gym
        ├── objetivo_nutricional
        ├── materiales
        ├── nivel_actividad
        ├── rutina (JSON)
        ├── dieta (JSON)
        └── fecha_creacion
```

### 2.3 OPTIMIZACIONES

- **Índices:** Email tiene índice único para búsquedas rápidas
- **JSON Storage:** Rutinas y dietas almacenadas como JSON en TEXT para flexibilidad
- **Lock Mechanism:** Campo `is_generating_plan` previene generaciones duplicadas

---

## 3. MODELOS DE IA Y RAG

### 3.1 GENERACIÓN DE RUTINAS

#### ¿Usa RAG?
**SÍ** - El sistema utiliza RAG (Retrieval-Augmented Generation) para enriquecer la generación de rutinas con conocimiento científico.

#### Base de Datos Vectorial
- **Proveedor:** Supabase (PostgreSQL con extensión pgvector)
- **Tabla:** `knowledge_base`
- **Campos:**
  - `id` - ID único
  - `title` - Título del documento
  - `category` - Categoría (entrenamiento, nutrición, etc.)
  - `tags` - Array de tags
  - `level` - Nivel (básico, intermedio, avanzado)
  - `goal` - Array de objetivos relacionados
  - `language` - Idioma ('es')
  - `content` - Contenido del documento
  - `source` - Fuente del conocimiento
  - `embedding` - Vector de embeddings (1536 dimensiones)
  - `references` - Array de referencias científicas

#### Estudios Científicos Indexados
- **Total:** 46 documentos JSON en `app/knowledge/`
- **Temas cubiertos:**
  - Hipertrofia básica y avanzada
  - Síntesis proteica
  - Nutrición deportiva
  - Periodización
  - Técnicas de entrenamiento
  - Fisiología del ejercicio
  - Y más...

#### Proceso de Búsqueda Semántica

1. **Generación de Embedding:**
   - Modelo: `text-embedding-3-small` de OpenAI
   - Input: Query del usuario (objetivos, experiencia, etc.)
   - Output: Vector de 1536 dimensiones

2. **Búsqueda en Supabase:**
   - Función RPC: `match_knowledge`
   - Parámetros:
     - `query_embedding` - Vector de la query
     - `match_count` - Número de resultados (k=5-10)
     - `filter_lang` - 'es'
     - `filter_category` - Opcional
   - Algoritmo: Cosine similarity en pgvector

3. **Selección de Documentos:**
   - Top 5-10 documentos más relevantes
   - Ordenados por similitud (similarity score)
   - Filtrados por idioma y categoría si aplica

#### Proceso de Generación con Contexto Científico

1. **Construcción del Prompt:**
   ```
   Sistema: Eres un entrenador personal experto...
   
   CONTEXTO CIENTÍFICO:
   [Documento 1: Hipertrofia básica]
   [Documento 2: Síntesis proteica]
   [Documento 3: Periodización]
   ...
   
   DATOS DEL USUARIO:
   - Objetivo: ganar_musculo
   - Experiencia: intermedio
   - Materiales: gimnasio completo
   ...
   
   INSTRUCCIONES:
   Genera una rutina de 4-5 días basada en la ciencia...
   ```

2. **Modelo Usado:**
   - **Principal:** GPT-4o
   - **Override:** Variable `OPENAI_MODEL` en .env
   - **Context Window:** 128k tokens
   - **Temperature:** 0.7 (creatividad controlada)

3. **Datos de Entrada del Usuario:**
   - Altura, peso, edad, sexo
   - Nivel de experiencia
   - Objetivo (ganar_musculo, ganar_fuerza, etc.)
   - Materiales disponibles
   - Lesiones y restricciones
   - Nivel de actividad
   - Puntos fuertes/débiles

4. **Formato de Salida (JSON):**
   ```json
   {
     "dias": [
       {
         "nombre": "Día 1 - Push",
         "ejercicios": [
           {
             "nombre": "Press banca",
             "series": 4,
             "repeticiones": "6-8",
             "descanso": "120s",
             "notas": "..."
           }
         ]
       }
     ],
     "consejos": [...],
     "periodizacion": {...}
   }
   ```

### 3.2 GENERACIÓN DE DIETAS

#### Proceso Completo

1. **Cálculo de Macros:**
   - Función: `get_complete_nutrition_plan()` en `utils/nutrition_calculator.py`
   - Inputs:
     - Peso, altura, edad, sexo
     - Nivel de actividad
     - Objetivo nutricional (volumen, definición, mantenimiento)
   - Outputs:
     - Calorías totales
     - Proteínas (g)
     - Carbohidratos (g)
     - Grasas (g)

2. **Generación con GPT-4o:**
   - Modelo: GPT-4o (mismo que rutinas)
   - RAG: **SÍ** - Usa documentos de nutrición deportiva
   - Prompt incluye:
     - Macros calculados
     - Preferencias del usuario
     - Alergias y restricciones
     - Objetivo nutricional

3. **Personalización:**
   - Basada en datos del usuario
   - Considera alimentos no deseados
   - Adapta a restricciones dietéticas
   - Incluye alternativas por comida

4. **Formato de Salida (JSON):**
   ```json
   {
     "total_kcal": 2500,
     "macros": {
       "proteinas": 150,
       "carbohidratos": 300,
       "grasas": 80,
       "total_kcal": 2500
     },
     "comidas": [
       {
         "nombre": "Desayuno",
         "kcal": 500,
         "macros": {...},
         "alimentos": [...],
         "alternativas": [...]
       }
     ]
   }
   ```

### 3.3 CHAT DE MODIFICACIONES

#### Modelo Usado
- **GPT-4o** (mismo que generación de planes)
- **Streaming:** SÍ - Respuestas en tiempo real

#### Context Window
- **Historial:** NO se mantiene historial persistente entre sesiones
- **Contexto actual:** Solo el mensaje actual + contexto RAG
- **Límite de tokens:** 128k (GPT-4o)

#### Límites para Usuarios FREE
- **Preguntas gratis:** 2 (campo `chat_uses_free`)
- **Control:** Backend valida antes de procesar
- **Mensaje de error:** "Has agotado tus 2 preguntas gratis. Actualiza a Premium para chat ilimitado."

#### Cómo se Modifica la Rutina/Dieta Existente

1. **Endpoint:** `POST /api/chat/modify`
2. **Input:**
   - `message` - Solicitud del usuario
   - `user_id` - ID del usuario (del token JWT)
   - `conversation_history` - Opcional, historial de la conversación

3. **Proceso:**
   - Carga rutina/dieta actual del usuario
   - Inyecta en el prompt del sistema
   - Usuario solicita modificación
   - GPT-4o genera nueva versión
   - Se actualiza `current_routine` o `current_diet`

4. **Detección de Cambios:**
   - Comparación JSON antes/después
   - Guarda en `modification_history`
   - No regenera completamente, solo modifica

#### Integración RAG en Chat
- **Función:** `get_rag_context_for_chat()` en `utils/gpt.py`
- **Proceso:**
  1. Genera embedding del mensaje del usuario
  2. Busca top 3-5 documentos relevantes
  3. Inyecta contexto científico en el prompt
  4. GPT-4o responde con base científica

---

## 4. SISTEMA FREEMIUM

### 4.1 DIFERENCIAS FREE vs PREMIUM

| Funcionalidad | FREE | PREMIUM |
|---------------|------|---------|
| **Rutina** | Plantilla básica (2 días) | GPT-4o personalizado completo (4-5 días) |
| **Dieta** | Plantilla básica (2 comidas) | GPT-4o personalizado completo (5 comidas + macros) |
| **Chat modificaciones** | 2 prompts gratis | Ilimitado |
| **Contenido visible** | Blur (primer día visible) | Todo visible sin restricciones |
| **Estudios científicos** | No | Sí (RAG completo) |
| **Generación de planes** | Plantilla local | IA GPT-4o + RAG |
| **Modificaciones IA** | No | Sí (ilimitadas) |
| **PDF de rutina** | No | Sí |
| **Análisis corporal** | Limitado | Completo |

### 4.2 IMPLEMENTACIÓN TÉCNICA DEL BLUR

#### Archivos Involucrados
- **CSS:** `dashboard.html` (líneas ~1239-1270)
- **JavaScript:** `dashboard.html` (función `renderDietHTML()`, `displayRoutineContent()`)

#### CSS Aplicado

```css
.blur-content {
    filter: blur(10px) brightness(0.7) !important;
    pointer-events: none !important;
    user-select: none !important;
    position: relative !important;
    transition: filter 0.3s ease-in;
}

.blur-content::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.2);
    pointer-events: none;
    z-index: 1;
}

body.user-is-premium .blur-content {
    filter: none !important;
    pointer-events: auto !important;
    user-select: auto !important;
}
```

#### Lógica JavaScript

1. **Verificación de Premium Status:**
   - Función: `checkPremiumStatus()` en `dashboard.html`
   - Endpoint: `GET /api/user/me`
   - Verifica: `data.is_premium === true`

2. **Aplicación de Blur:**
   - Si `isPremium === false`:
     - Añade clase `blur-content` al contenido
     - Muestra overlay premium con botón "Desbloquear Premium"
   - Si `isPremium === true`:
     - Elimina clase `blur-content`
     - Muestra todo el contenido sin restricciones

3. **Overlay Premium:**
   - Función: `getPremiumLockHTML(title, subtitle)`
   - Estilos: `.premium-lock-container`, `.premium-lock-card`
   - Botón: Redirige a `./tarifas.html`

#### Endpoint Usado
- **`GET /api/user/me`** - Retorna datos completos del usuario
- **Autenticación:** Requiere JWT token en header `Authorization: Bearer <token>`
- **Respuesta:**
  ```json
  {
    "id": 1,
    "email": "user@example.com",
    "plan_type": "FREE",
    "is_premium": false,
    "onboarding_completed": true,
    "chat_uses_free": 2
  }
  ```

### 4.3 RESTRICCIONES DE CHAT

#### Dónde se Controla
- **Backend:** `app/routes/chat.py` (línea ~100-150)
- **Frontend:** `dashboard.html` (validación antes de enviar)

#### Campo BD
- **`chat_uses_free`** - INTEGER, DEFAULT 2
- **Decremento:** Se resta 1 cada vez que un usuario FREE envía un mensaje
- **Reset:** Se resetea cuando el usuario hace upgrade a Premium

#### Cómo se Resetea al Hacer Upgrade
- **Webhook:** `customer.subscription.created` en `stripe_webhook.py`
- **Acción:** `chat_uses_free = 999` (efectivamente ilimitado)
- **Código:**
  ```python
  user.chat_uses_free = 999  # Ilimitado para premium
  ```

#### Mensajes de Error Mostrados
- **Frontend:** "Has agotado tus 2 preguntas gratis. Actualiza a Premium para chat ilimitado."
- **Backend:** HTTP 403 con mensaje similar

---

## 5. AUTENTICACIÓN Y SEGURIDAD

### 5.1 JWT TOKENS

#### Estructura del Token
```json
{
  "sub": "123",  // user_id como string
  "exp": 1234567890  // Timestamp de expiración
}
```

#### Tiempo de Expiración
- **Configuración:** Variable `ACCESS_TOKEN_EXPIRE_MINUTES` en `auth_utils.py`
- **Valor por defecto:** 10080 minutos (7 días)
- **Override:** Variable de entorno `ACCESS_TOKEN_EXPIRE_MINUTES`

#### SECRET_KEY
- **Ubicación:** Variable de entorno `SECRET_KEY` en `.env`
- **Requisito:** Mínimo 32 caracteres
- **Uso:** Firmado y verificación de tokens JWT

#### Algoritmo Usado
- **HS256** (HMAC-SHA256)
- **Configuración:** Variable `ALGORITHM` en `auth_utils.py` (default: "HS256")

#### Cómo se Valida en Cada Request

1. **Dependency:** `get_current_user()` en `auth_utils.py`
2. **Proceso:**
   ```python
   def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Usuario:
       payload = decode_access_token(token)
       if payload is None:
           raise HTTPException(401, "Token inválido o expirado")
       
       user_id = int(payload["sub"])
       user = db.query(Usuario).filter(Usuario.id == user_id).first()
       if user is None:
           raise HTTPException(401, "Usuario no encontrado")
       return user
   ```

3. **Uso en Endpoints:**
   ```python
   @router.get("/api/user/me")
   async def get_current_user_data(
       current_user: Usuario = Depends(get_current_user)
   ):
       # current_user es el objeto Usuario completo
   ```

### 5.2 GOOGLE OAUTH

#### Configuración Completa

**Variables de Entorno:**
- `GOOGLE_CLIENT_ID` - Client ID de Google Cloud Console
- `GOOGLE_CLIENT_SECRET` - Client Secret de Google Cloud Console
- `GOOGLE_REDIRECT_URI` - URL de callback (ej: `http://localhost:8000/auth/google/callback`)

**URLs de Google:**
- Auth URL: `https://accounts.google.com/o/oauth2/v2/auth`
- Token URL: `https://oauth2.googleapis.com/token`
- UserInfo URL: `https://www.googleapis.com/oauth2/v3/userinfo`

#### Flujo Completo de Autenticación

1. **Usuario click "Login con Google"**
   - Frontend: Redirige a `/auth/google/login`
   - Backend: Genera URL de autorización de Google

2. **Redirect a Google**
   - Parámetros:
     - `client_id` - GOOGLE_CLIENT_ID
     - `redirect_uri` - GOOGLE_REDIRECT_URI
     - `response_type` - "code"
     - `scope` - "openid email profile"
     - `access_type` - "offline"
     - `prompt` - "consent"

3. **Callback a `/auth/google/callback`**
   - Google redirige con `code` en query string
   - Backend intercambia `code` por `access_token`

4. **Creación/Login de Usuario**
   - Obtiene información del usuario de Google (email, google_id, picture)
   - Busca usuario existente por `google_id` o `email`
   - Si no existe, crea nuevo usuario
   - Si existe por email, vincula cuenta con Google

5. **Generación de JWT**
   - Crea token JWT con `{"sub": user_id}`
   - Expiración: 7 días (configurable)

6. **Redirect a Dashboard**
   - URL: `/login.html?token=<jwt>&onboarding=<true/false>`
   - Frontend captura token y lo guarda en `localStorage`
   - Redirige a dashboard o onboarding según corresponda

#### Redirect URIs Necesarios
- Desarrollo: `http://localhost:8000/auth/google/callback`
- Producción: `https://yourgains.ai/auth/google/callback` (o dominio correspondiente)

### 5.3 SEGURIDAD DE CONTRASEÑAS

#### Hashing Usado
- **Algoritmo:** bcrypt
- **Librería:** passlib 1.7.4 con bcrypt 4.3.0
- **Salts:** Automáticos (bcrypt genera salt único por hash)

#### Validación de Contraseñas
- **Función:** `verify_password(plain_password, hashed_password)`
- **Proceso:** bcrypt compara contraseña plana con hash almacenado
- **Seguridad:** Resistente a timing attacks

### 5.4 CONFIGURACIÓN CORS (CROSS-ORIGIN RESOURCE SHARING)

#### ⚠️ CRÍTICO PARA PRODUCCIÓN
**CORS está configurado de forma segura para producción.** No se permite `allow_origins=["*"]` que sería una vulnerabilidad grave.

#### Ubicación
- **Archivo:** `app/main.py` (líneas ~35-65)
- **Middleware:** `CORSMiddleware` de FastAPI

#### Configuración Actual

**Variables de Entorno:**
- `FRONTEND_URL` - URL principal del frontend (default: `http://127.0.0.1:8000`)
- `ALLOWED_ORIGINS` - Lista separada por comas de orígenes permitidos (opcional)

**Lógica de Configuración:**

```python
# Configuración de CORS según entorno
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:8000")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else [FRONTEND_URL]

# Si estamos en desarrollo local, permitir localhost
if "localhost" in FRONTEND_URL or "127.0.0.1" in FRONTEND_URL:
    ALLOWED_ORIGINS.extend([
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5173",  # Vite dev server si se usa
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # ✅ Lista específica de dominios
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
```

#### Comportamiento por Entorno

**Desarrollo (localhost):**
- Permite automáticamente:
  - `http://localhost:8000`
  - `http://127.0.0.1:8000`
  - `http://localhost:5173` (Vite dev server)

**Producción (Railway):**
- Solo permite dominios configurados en:
  - `FRONTEND_URL` (ej: `https://yourgains.ai`)
  - `ALLOWED_ORIGINS` (ej: `https://yourgains.ai,https://www.yourgains.ai`)

#### Configuración Recomendada para Producción

**En Railway Dashboard, configurar:**
```
FRONTEND_URL=https://yourgains.ai
ALLOWED_ORIGINS=https://yourgains.ai,https://www.yourgains.ai
```

**O solo con FRONTEND_URL:**
```
FRONTEND_URL=https://yourgains.ai
```

#### Métodos HTTP Permitidos
- `GET` - Lectura de datos
- `POST` - Creación de recursos
- `PUT` - Actualización de recursos
- `DELETE` - Eliminación de recursos
- `OPTIONS` - Preflight requests (requerido por CORS)

#### Headers Permitidos
- `allow_headers=["*"]` - Permite todos los headers (incluye `Authorization`, `Content-Type`, etc.)

#### Credenciales
- `allow_credentials=True` - Necesario para:
  - Cookies de sesión
  - JWT tokens en headers
  - Autenticación con credenciales

#### Logs de Debugging
Al arrancar el servidor, se muestra en logs:
```
[CORS] Orígenes permitidos: ['https://yourgains.ai', 'https://www.yourgains.ai']
```

#### Seguridad
- ✅ **NO usa `allow_origins=["*"]`** - Previene ataques CSRF
- ✅ **Lista específica de dominios** - Solo dominios autorizados
- ✅ **Validación automática** - FastAPI valida el `Origin` header
- ✅ **Logs de orígenes** - Facilita debugging y auditoría

### 5.5 RATE LIMITING (Prevención de Abusos)

#### ⚠️ CRÍTICO PARA PRODUCCIÓN
**Rate limiting está implementado para prevenir abusos y costos excesivos en APIs externas.**

#### Ubicación
- **Librería:** `slowapi==0.1.9`
- **Configuración principal:** `app/main.py` (líneas ~33-50)
- **Aplicación:** Routers individuales (`auth.py`, `chat.py`, `stripe_routes.py`)

#### Configuración Global

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

#### Límites por Endpoint

| Endpoint | Límite | Razón |
|----------|--------|-------|
| `POST /login` | 10/minuto | Prevenir brute force |
| `POST /register` | 5/minuto | Prevenir spam de registros |
| `POST /api/chat` | 30/minuto | Prevenir abuso de OpenAI API (costos) |
| `POST /api/chat/modify` | 20/minuto | Prevenir abuso de modificaciones |
| `POST /create-checkout-session` | 10/minuto | Prevenir spam de checkout |

#### Cómo Funciona

1. **Identificación por IP:** Usa `get_remote_address` para identificar al cliente por IP
2. **Ventana deslizante:** Los límites se aplican en ventanas de tiempo deslizantes
3. **Respuesta HTTP 429:** Cuando se excede el límite, retorna:
   ```json
   {
     "error": "Demasiadas solicitudes. Por favor, espera un momento e inténtalo de nuevo.",
     "retry_after": 60
   }
   ```

#### Handler Personalizado

```python
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "error": "Demasiadas solicitudes. Por favor, espera un momento e inténtalo de nuevo.",
            "retry_after": exc.retry_after if hasattr(exc, 'retry_after') else 60
        }
    )
```

#### Aplicación en Routers

Cada router que necesita rate limiting:

1. **Importa slowapi:**
   ```python
   from slowapi import Limiter
   from slowapi.util import get_remote_address
   limiter = Limiter(key_func=get_remote_address)
   ```

2. **Aplica decorador:**
   ```python
   @router.post("/login")
   @limiter.limit("10/minute")
   async def login(request: Request, ...):
       # request: Request es OBLIGATORIO para rate limiting
   ```

#### Importante

- ✅ **Siempre añadir `request: Request`** como primer parámetro en endpoints con rate limiting
- ✅ **Límites por IP, no por usuario** - Protege mejor contra ataques distribuidos
- ✅ **HTTP 429** es el código estándar para "Too Many Requests"
- ✅ **No afecta usuarios normales** - Los límites son generosos para uso legítimo

#### Testing

Para probar rate limiting:
```bash
# Hacer múltiples requests rápidas
for i in {1..15}; do curl -X POST http://localhost:8000/login -H "Content-Type: application/json" -d '{"email":"test@test.com","password":"test"}' & done
# Debe retornar 429 después del límite
```

---

## 6. STRIPE Y PAGOS

### 6.1 CONFIGURACIÓN ACTUAL

#### Modo
- **Desarrollo:** Test mode (claves `sk_test_...`, `pk_test_...`)
- **Producción:** Live mode (claves `sk_live_...`, `pk_live_...`)

#### Productos Configurados

**PREMIUM_MONTHLY:**
- Precio: €9.99/mes
- Price ID: Variable `STRIPE_PRICE_MENSUAL` en `.env`
- Formato: `price_xxxxxxxxxxxxx`

**PREMIUM_YEARLY:**
- Precio: Configurable (actualmente no implementado en producción)
- Price ID: Variable `STRIPE_PRICE_ANUAL` en `.env`
- Formato: `price_xxxxxxxxxxxxx`

#### Price IDs
- **Variables:** `STRIPE_PRICE_MENSUAL`, `STRIPE_PRICE_ANUAL`
- **Validación:** Solo estos Price IDs son aceptados en checkout

#### Webhook Secret
- **Variable:** `STRIPE_WEBHOOK_SECRET`
- **Formato:** `whsec_xxxxxxxxxxxxx`
- **Uso:** Verificación de firma de webhooks

#### Customer Portal URL
- **Configuración:** En Stripe Dashboard
- **Uso:** Permite a usuarios gestionar suscripciones directamente

### 6.2 FLUJO COMPLETO DE PAGO

```
1. Usuario → Botón "Upgrade to Premium"
   └─ Frontend: dashboard.html o tarifas.html

2. Frontend → POST /create-checkout-session
   └─ Body: {"price_id": "price_xxx"}
   └─ Header: Authorization: Bearer <token>

3. Backend → Crea sesión en Stripe
   └─ Crea o reutiliza customer
   └─ Crea checkout session
   └─ Retorna: {"url": "https://checkout.stripe.com/..."}

4. Redirect → Stripe Checkout
   └─ Usuario ingresa datos de pago
   └─ Stripe procesa el pago

5. Usuario paga → Stripe procesa
   └─ Tarjeta validada y cobrada

6. Stripe → Webhook customer.subscription.created
   └─ POST /stripe/webhook
   └─ Evento: customer.subscription.created

7. Backend → set_premium_by_customer(is_premium=True)
   └─ Actualiza usuario en BD
   └─ Establece plan_type (PREMIUM_MONTHLY o PREMIUM_YEARLY)
   └─ Guarda stripe_subscription_id

8. Backend → generate_and_save_ai_plan()
   └─ Genera plan con GPT-4o + RAG
   └─ Guarda en current_routine y current_diet
   └─ Resetea chat_uses_free = 999

9. Redirect → Dashboard con success=1
   └─ URL: /dashboard.html?success=1&session_id=xxx

10. Frontend → Poll /user/current-routine
    └─ Verifica si el plan está listo
    └─ Muestra plan premium sin blur
```

### 6.3 WEBHOOKS IMPLEMENTADOS

#### `checkout.session.completed`
- **Cuándo:** Después de que el usuario completa el checkout exitosamente
- **Qué hace:**
  - Verifica que el pago fue exitoso
  - Activa premium si no se activó ya
  - Genera plan con IA si no existe

#### `customer.subscription.created`
- **Cuándo:** Cuando se crea una nueva suscripción
- **Qué hace:**
  - Establece `is_premium = True`
  - Detecta tipo de plan (MONTHLY/YEARLY) desde `price_id`
  - Guarda `stripe_subscription_id`
  - Genera plan con IA (si `generate_plan=True`)
  - Resetea `chat_uses_free = 999`

#### `customer.subscription.updated`
- **Cuándo:** Cuando se actualiza una suscripción (cambio de plan, renovación, etc.)
- **Qué hace:**
  - Actualiza `plan_type` si cambió el `price_id`
  - Mantiene `is_premium = True` si la suscripción sigue activa
  - Actualiza `stripe_subscription_id` si cambió

#### `customer.subscription.deleted`
- **Cuándo:** Cuando se cancela una suscripción
- **Qué hace:**
  - Establece `is_premium = False`
  - Cambia `plan_type = "FREE"`
  - Limpia `stripe_subscription_id` (opcional, puede mantenerse para historial)
  - NO elimina el plan existente (el usuario puede seguir viéndolo)

#### `payment_intent.succeeded`
- **Cuándo:** Cuando un pago individual es exitoso
- **Qué hace:**
  - Usado principalmente para pagos únicos (no implementado actualmente)
  - Para suscripciones, se usa `subscription.created` en su lugar

### 6.4 CANCELACIÓN DE SUSCRIPCIONES

#### Flujo Completo

1. **Usuario cancela en Stripe Customer Portal**
   - Accede al portal desde el dashboard
   - Cancela la suscripción

2. **Webhook que lo Maneja**
   - `customer.subscription.deleted` o
   - `customer.subscription.updated` con `cancel_at_period_end = True`

3. **Cambios en BD**
   - `is_premium = False`
   - `plan_type = "FREE"`
   - `stripe_subscription_id` puede mantenerse o limpiarse

4. **Qué Pasa con el Contenido del Usuario**
   - **Rutina/Dieta:** Se mantienen en `current_routine` y `current_diet`
   - **Visibilidad:** El contenido se muestra con blur (como usuario FREE)
   - **Chat:** Se resetea `chat_uses_free = 2`
   - **Historial:** Se mantiene en tabla `planes`

5. **Cancel at Period End vs Cancelación Inmediata**
   - **Cancel at Period End:** Suscripción activa hasta fin de período, luego se cancela
   - **Cancelación Inmediata:** Suscripción cancelada de inmediato, acceso premium revocado

---

## 7. TÉRMINOS Y POLÍTICAS (PARA REVISIÓN LEGAL)

### 7.1 TÉRMINOS DE SERVICIO

**Archivo:** `app/frontend/terms.html`

**Contenido Completo (texto sin HTML):**

1. **Aceptación de los Términos**
   - Al acceder y utilizar YourGains AI, usted acepta cumplir estos Términos y Condiciones.
   - Si no está de acuerdo, no debe utilizar el Servicio.
   - Estos términos constituyen un acuerdo legalmente vinculante.

2. **Descripción del Servicio**
   - YourGains AI es una plataforma de IA para entrenamiento físico, nutrición y bienestar.
   - Incluye: generación de rutinas personalizadas, planes nutricionales, asesoramiento, seguimiento de progreso, contenido educativo, chat con IA.
   - **IMPORTANTE:** El Servicio proporciona información general. No constituye asesoramiento médico, nutricional o profesional.

3. **Registro y Cuenta de Usuario**
   - Requisitos: Mayor de 18 años o consentimiento de tutor legal.
   - Responsabilidades: Mantener confidencialidad de credenciales, notificar uso no autorizado, proporcionar información veraz.

4. **Suscripciones y Pagos**
   - Planes: Mensual y anual. Precios mostrados en página de tarifas.
   - Procesamiento: Stripe (procesador seguro de terceros).
   - Renovación: Automática al final de cada período.
   - Cancelación: En cualquier momento a través del portal de Stripe.
   - Reembolsos: Todos los pagos son finales, excepto casos excepcionales.

5. **Uso Aceptable**
   - Prohibido: Violar leyes, infringir derechos, interferir con el servicio, transmitir virus, ingeniería inversa, bots, copiar contenido, competir con el servicio.

6. **Propiedad Intelectual**
   - Todo el contenido es propiedad de YourGains AI o sus proveedores.
   - Licencia limitada, no exclusiva, no transferible y revocable para uso personal.

7. **Limitación de Responsabilidad**
   - **ADVERTENCIA MÉDICA:** No constituye asesoramiento médico, nutricional o profesional.
   - Siempre consulte con un profesional de la salud antes de comenzar cualquier programa.
   - YourGains AI no será responsable de daños directos, indirectos, incidentales, especiales, consecuentes o punitivos.

8. **Modificaciones del Servicio**
   - Nos reservamos el derecho de modificar, suspender o discontinuar cualquier aspecto del Servicio.

9. **Cancelación y Terminación**
   - Usuario puede cancelar en cualquier momento.
   - Nos reservamos el derecho de suspender o terminar acceso por violación de términos.

10. **Protección de Datos y Privacidad**
    - Se rige por nuestra Política de Privacidad.
    - Cumplimos con RGPD y leyes de protección de datos aplicables.

11. **Servicios de Terceros**
    - Integramos: Stripe (pagos), Google (OAuth), OpenAI (IA).
    - Acepta términos y condiciones de estos proveedores.

12. **Modificaciones de los Términos**
    - Nos reservamos el derecho de modificar estos términos.
    - Notificación mediante email o notificación visible en el Servicio.

13. **Ley Aplicable y Jurisdicción**
    - Se rigen por las leyes aplicables.
    - Disputas resueltas en tribunales competentes.

14. **Disposiciones Generales**
    - Integridad del acuerdo, divisibilidad, renuncia, cesión.

15. **Contacto**
    - Email: contacto@yourgains.ai
    - Formulario de contacto en el Servicio.

### 7.2 POLÍTICA DE PRIVACIDAD

**Archivo:** `app/frontend/privacy.html`

**Contenido Completo (texto sin HTML):**

1. **Introducción**
   - YourGains AI se compromete a proteger su privacidad y datos personales.
   - Explica cómo recopilamos, utilizamos, almacenamos, protegemos y divulgamos información.
   - Cumple con RGPD y leyes de protección de datos aplicables.

2. **Información que Recopilamos**
   - **Personal Identificable:** Email, nombre, foto de perfil, credenciales OAuth, objetivos, nivel de experiencia, preferencias, restricciones dietéticas, tipo de plan, estado de suscripción.
   - **Uso y Actividad:** Rutinas generadas, planes nutricionales, interacciones con chat, preferencias, datos de progreso, historial de navegación.
   - **Técnica y de Dispositivo:** Tipo de navegador, dispositivo, sistema operativo, IP, cookies.
   - **Pago:** ID de customer/subscription de Stripe, estado de pago, últimos 4 dígitos de tarjeta (NO información completa de tarjetas).

3. **Cómo Utilizamos su Información**
   - Prestación del Servicio: Crear cuenta, procesar pagos, generar rutinas/dietas, proporcionar chat.
   - Mejora y Personalización: Personalizar experiencia, mejorar algoritmos, desarrollar nuevas funcionalidades.
   - Comunicación: Notificaciones importantes, actualizaciones, soporte.
   - Seguridad y Cumplimiento: Detectar fraudes, proteger seguridad, cumplir obligaciones legales.

4. **Base Legal para el Procesamiento (RGPD)**
   - Ejecución de Contrato
   - Consentimiento
   - Interés Legítimo
   - Obligación Legal

5. **Compartir y Divulgación de Información**
   - **Proveedores de Servicios:** Stripe, Google, OpenAI, proveedores de hosting, servicios de análisis.
   - **Cumplimiento Legal:** Cuando sea requerido por leyes, órdenes judiciales, autoridades.
   - **Transferencias Comerciales:** En caso de fusión, adquisición, reorganización.

6. **Seguridad de los Datos**
   - Cifrado SSL/TLS
   - Autenticación segura
   - Control de acceso
   - Monitoreo
   - Copias de seguridad
   - Actualizaciones de seguridad

7. **Retención de Datos**
   - Datos de Cuenta: Mientras esté activa y hasta 2 años después de cancelación.
   - Datos de Suscripción: Según leyes fiscales (generalmente 7 años).
   - Datos de Uso: Hasta 1 año después de última actividad.
   - Datos de Chat: Hasta 90 días después de última interacción.

8. **Sus Derechos (RGPD)**
   - Derecho de Acceso
   - Derecho de Rectificación
   - Derecho de Eliminación ("Derecho al Olvido")
   - Derecho de Oposición
   - Derecho de Limitación del Procesamiento
   - Derecho de Portabilidad de Datos
   - Derecho de Retirar Consentimiento

9. **Cookies y Tecnologías Similares**
   - Cookies Esenciales: Necesarias para funcionamiento.
   - Cookies de Funcionalidad: Recuerdan preferencias.
   - Cookies de Análisis: Entienden interacciones (datos agregados y anonimizados).

10. **Servicios de Terceros**
    - Google OAuth: Comparte información según configuración de privacidad de Google.
    - Stripe: Procesa pagos, información sujeta a Política de Privacidad de Stripe.
    - OpenAI: Procesa mensajes según su Política de Privacidad.

11. **Transferencias Internacionales de Datos**
    - Implementamos salvaguardias apropiadas: cláusulas contractuales estándar, certificaciones de adecuación.

12. **Privacidad de Menores**
    - Servicio no dirigido a menores de 18 años.
    - No recopilamos intencionalmente información de menores.

13. **Cambios a esta Política de Privacidad**
    - Podemos actualizar ocasionalmente.
    - Notificación mediante email o notificación visible.

14. **Contacto y Consultas**
    - Email: contacto@yourgains.ai
    - Formulario de contacto en el Servicio.

### 7.3 DATOS QUE RECOPILAMOS

#### Lista Exhaustiva

**Datos de Autenticación:**
- Email (único, requerido)
- Contraseña hasheada (bcrypt, nullable si solo OAuth)
- Google ID (nullable)
- OAuth provider ('google' o NULL)
- Profile picture URL (nullable, desde Google)

**Datos Personales del Onboarding:**
- Altura (cm)
- Peso (kg o rango)
- Edad (años)
- Sexo ('M' o 'F')
- Nivel de experiencia
- Objetivo de entrenamiento (ganar_musculo, ganar_fuerza, etc.)
- Objetivo nutricional (volumen, definicion, mantenimiento, etc.)
- Materiales disponibles
- Tipo de cuerpo
- Nivel de actividad (sedentario, ligero, moderado, activo, muy_activo)
- Puntos fuertes
- Puntos débiles
- Días de entrenamiento fuerte
- Lesiones
- Alergias alimentarias
- Restricciones dietéticas
- Alimentos no deseados
- Áreas de enfoque

**Datos de Uso:**
- `chat_uses_free` - Preguntas gratis restantes
- `modification_history` - Historial de modificaciones de rutina/dieta (JSON array)
- `current_routine` - Rutina actual (JSON)
- `current_diet` - Dieta actual (JSON)
- `onboarding_completed` - Si completó el onboarding

**Datos de Pago:**
- `stripe_customer_id` - ID de customer en Stripe
- `stripe_subscription_id` - ID de suscripción en Stripe
- `plan_type` - Tipo de plan (FREE, PREMIUM_MONTHLY, PREMIUM_YEARLY)
- `is_premium` - Estado premium (boolean)

**Datos de Planes Históricos:**
- Tabla `planes` con todos los datos del onboarding y planes generados
- `fecha_creacion` - Timestamp de creación

**Cookies:**
- `access_token` - JWT token (localStorage, no cookie HTTP)
- `yg_cookie_consent` - Consentimiento de cookies (localStorage)
- Cookies de Google Analytics (si se acepta)

**Analytics:**
- Google Analytics 4 (ID: G-XC85YN9Z36)
- Solo si el usuario acepta cookies analíticas
- IPs anonimizadas

### 7.4 CÓMO USAMOS LOS DATOS

#### Para qué se Usa Cada Tipo de Dato

**Email:**
- Autenticación y login
- Comunicación con el usuario
- Identificación única

**Contraseña:**
- Autenticación (nunca se almacena en texto plano)

**Datos del Onboarding:**
- Generación de rutinas personalizadas
- Cálculo de macros y calorías
- Personalización de planes

**Datos de Uso:**
- Control de límites FREE vs PREMIUM
- Historial de modificaciones
- Mejora del servicio

**Datos de Pago:**
- Gestión de suscripciones
- Verificación de estado premium
- Facturación

#### Con quién se Comparten

**Stripe:**
- Email (para crear customer)
- Metadata (user_id)
- NO información de tarjetas completas

**Google:**
- Email, nombre, foto de perfil (solo para OAuth)
- Según configuración de privacidad de Google

**OpenAI:**
- Mensajes del chat
- Datos del usuario para generación de planes
- NO información personal identificable más allá de lo necesario

**Supabase (si se usa):**
- Embeddings y contenido de documentos (base de conocimiento)
- NO datos personales de usuarios

#### Cuánto Tiempo se Almacenan

- **Datos de cuenta:** Mientras esté activa + 2 años después de cancelación
- **Datos de suscripción:** 7 años (requisitos fiscales)
- **Datos de uso:** 1 año después de última actividad
- **Datos de chat:** 90 días después de última interacción

#### Derechos del Usuario (GDPR)

**Acceso:**
- Usuario puede solicitar copia de todos sus datos
- Endpoint: Contactar a contacto@yourgains.ai

**Rectificación:**
- Usuario puede actualizar datos a través del dashboard
- O contactar para correcciones

**Eliminación:**
- Usuario puede solicitar eliminación de cuenta
- Se eliminarán datos personales (sujeto a obligaciones legales de retención)

**Portabilidad:**
- Usuario puede solicitar exportación de datos en formato estructurado

### 7.5 CONSENTIMIENTO DE COOKIES

#### ¿Hay Banner de Cookies?
**SÍ** - Implementado en `static/cookie-consent.js`

#### Qué Hace el Banner
- Muestra banner en primera visita
- Permite aceptar todas, rechazar no esenciales, o personalizar
- Guarda preferencias en `localStorage` (clave: `yg_cookie_consent`)
- Expira después de 365 días

#### Cookies Esenciales vs No Esenciales

**Esenciales (siempre activas):**
- Autenticación (JWT token en localStorage)
- Preferencias de sesión
- No se pueden desactivar

**No Esenciales:**
- Google Analytics (solo si se acepta)
- Carga dinámicamente solo con consentimiento

#### Cumplimiento GDPR/LOPDGDD
- ✅ Banner de consentimiento visible
- ✅ Opción de rechazar cookies no esenciales
- ✅ Información clara sobre tipos de cookies
- ✅ Página de información de cookies (`/cookies.html`)
- ✅ Anonimización de IPs en Google Analytics
- ✅ Consentimiento explícito antes de cargar analytics

---

## 8. GOOGLE ANALYTICS

### ¿Está Implementado?
**SÍ** - Implementado con consentimiento explícito

### Configuración

**ID de Propiedad:** `G-XC85YN9Z36` (GA4)

**Qué Eventos se Trackean:**
- Page views (automático)
- Eventos personalizados (si se implementan)

**Configuración de Privacidad:**
- `anonymize_ip: true` - IPs anonimizadas
- `cookie_flags: 'SameSite=None;Secure'` - Cookies seguras

**Opt-out Disponible:**
- Sí, el usuario puede rechazar cookies analíticas en el banner
- Si rechaza, Google Analytics no se carga

**Carga Dinámica:**
- Solo se carga si el usuario acepta cookies analíticas
- Implementado en `static/cookie-consent.js` (función `loadGoogleAnalytics()`)

---

## 9. VARIABLES DE ENTORNO (.env)

### Lista Completa de Variables Necesarias

**Base de Datos:**
```env
DATABASE_URL=sqlite:///./gymai.db
# O para PostgreSQL:
# DATABASE_URL=postgresql://user:password@host:port/dbname
```

**JWT:**
```env
SECRET_KEY=[GENERADO ALEATORIAMENTE - MÍNIMO 32 CARACTERES]
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

**OpenAI:**
```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
```

**Stripe TEST:**
```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_MENSUAL=price_...
STRIPE_PRICE_ANUAL=price_...
```

**Stripe LIVE (para producción):**
```env
STRIPE_SECRET_KEY_LIVE=sk_live_...
STRIPE_PUBLISHABLE_KEY_LIVE=pk_live_...
STRIPE_WEBHOOK_SECRET_LIVE=whsec_...
# Usar mismos Price IDs o crear nuevos en modo live
```

**Google OAuth:**
```env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
# Producción: https://yourgains.ai/auth/google/callback
```

**Supabase (opcional, solo si se usa RAG):**
```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

**CORS (Seguridad Crítica):**
```env
FRONTEND_URL=http://127.0.0.1:8000
# Producción: https://yourgains.ai

# Opcional: Lista de orígenes permitidos (separados por comas)
ALLOWED_ORIGINS=https://yourgains.ai,https://www.yourgains.ai
# Si no se especifica, usa solo FRONTEND_URL
# En desarrollo local, se añaden automáticamente localhost:8000 y localhost:5173
```

**NOTA IMPORTANTE:**
- **NUNCA** incluir valores reales en documentación o repositorio
- Usar `.env.example` con placeholders
- Configurar en Railway dashboard para producción

---

## 10. PREPARACIÓN PARA PRODUCCIÓN

### 10.1 CHECKLIST DE STRIPE LIVE

- [ ] Cuenta Stripe activada y verificada
- [ ] Información de negocio completa en Stripe Dashboard
- [ ] Productos creados en modo **live** (no test)
- [ ] Price IDs de **live** configurados en `.env` de producción
- [ ] Webhook endpoint configurado en Stripe Dashboard:
  - URL: `https://yourgains.ai/stripe/webhook`
  - Eventos: `checkout.session.completed`, `customer.subscription.*`, `payment_intent.succeeded`
- [ ] Webhook secret de **live** en variables de entorno de producción
- [ ] Customer Portal configurado y habilitado
- [ ] Configuración de facturación y emails de Stripe
- [ ] Probar checkout completo en modo live con tarjeta de prueba
- [ ] Verificar que webhooks se reciben correctamente

### 10.2 CHECKLIST DE GOOGLE OAUTH

- [ ] Proyecto de Google Cloud configurado
- [ ] OAuth consent screen **publicado** (no en "Testing")
- [ ] Redirect URIs de producción añadidos:
  - `https://yourgains.ai/auth/google/callback`
- [ ] Dominios autorizados configurados:
  - `yourgains.ai`
  - `www.yourgains.ai` (si aplica)
- [ ] Client ID y Secret de **producción** en variables de entorno
- [ ] Probar flujo completo de OAuth en producción

### 10.3 CHECKLIST DE RAILWAY

- [ ] Variables de entorno configuradas en Railway dashboard
- [ ] **CORS configurado correctamente:**
  - [ ] `FRONTEND_URL` configurado con dominio de producción (ej: `https://yourgains.ai`)
  - [ ] `ALLOWED_ORIGINS` configurado si hay múltiples dominios (ej: `https://yourgains.ai,https://www.yourgains.ai`)
  - [ ] Verificar en logs que solo se permiten dominios autorizados (no `["*"]`)
- [ ] **Rate Limiting verificado:**
  - [ ] `slowapi==0.1.9` instalado (verificar en `requirements.txt`)
  - [ ] Probar que `/login` bloquea después de 10 intentos por minuto
  - [ ] Verificar que endpoints críticos tienen rate limiting aplicado
  - [ ] Confirmar que usuarios normales no son afectados por los límites
- [ ] Base de datos persistente configurada (PostgreSQL recomendado para producción)
- [ ] Dominio custom configurado (`yourgains.ai`)
- [ ] SSL/HTTPS funcionando (automático con Railway)
- [ ] Logs monitorizados
- [ ] Health checks funcionando (`/ping`)
- [ ] Procfile correcto para Railway
- [ ] Variables de entorno de producción (no desarrollo) configuradas

### 10.4 CHECKLIST ADICIONAL

- [ ] Términos y condiciones actualizados con información real
- [ ] Política de privacidad actualizada
- [ ] Email de contacto funcionando (`contacto@yourgains.ai`)
- [ ] Google Analytics configurado con dominio de producción
- [ ] Pruebas de carga realizadas
- [ ] Backup de base de datos configurado
- [ ] Monitoreo de errores configurado (opcional: Sentry, etc.)

---

## 11. PUNTOS CRÍTICOS PARA REVISIÓN

### 11.1 SEGURIDAD

#### ¿Hay Rate Limiting en Endpoints Sensibles?
**SÍ IMPLEMENTADO** - Rate limiting configurado con `slowapi`:
- ✅ `/login` - 10 intentos por minuto
- ✅ `/register` - 5 registros por minuto
- ✅ `/api/chat` - 30 mensajes por minuto
- ✅ `/api/chat/modify` - 20 modificaciones por minuto
- ✅ `/create-checkout-session` - 10 intentos por minuto
- **Librería:** `slowapi==0.1.9`
- **Ubicación:** Configurado en `app/main.py` y aplicado en routers individuales
- **Método:** Límites por IP usando `get_remote_address`
- **Respuesta:** HTTP 429 (Too Many Requests) con mensaje personalizado
- **Handler:** Exception handler personalizado en `app/main.py`

#### ¿Se Validan Todos los Inputs de Usuario?
**SÍ** - Usando Pydantic schemas:
- `PlanRequest` - Valida datos de onboarding
- `ChatRequestBody` - Valida mensajes de chat
- Validación de tipos y rangos

#### ¿Las Contraseñas Están Hasheadas Correctamente?
**SÍ** - Usando bcrypt con salts automáticos
- Función: `get_password_hash()` en `auth_utils.py`
- Verificación: `verify_password()` resistente a timing attacks

#### ¿Los Tokens Expiran Adecuadamente?
**SÍ** - Configuración:
- Expiración: 7 días (10080 minutos)
- Configurable mediante `ACCESS_TOKEN_EXPIRE_MINUTES`
- Validación en cada request

#### ¿CORS Está Configurado de Forma Segura?
**SÍ** - Configuración segura implementada:
- ✅ **NO usa `allow_origins=["*"]`** - Previene ataques CSRF
- ✅ Lista específica de dominios permitidos
- ✅ Configuración basada en variables de entorno (`FRONTEND_URL`, `ALLOWED_ORIGINS`)
- ✅ Permite localhost automáticamente solo en desarrollo
- ✅ En producción solo permite dominios autorizados
- ✅ Logs muestran orígenes permitidos al arrancar
- **Ubicación:** `app/main.py` (líneas ~35-65)
- **Verificación:** Revisar logs al arrancar servidor: `[CORS] Orígenes permitidos: [...]`

### 11.2 PRIVACIDAD

#### ¿Los Términos y Políticas Cubren Todo?
**SÍ** - Términos y Política de Privacidad completos en `terms.html` y `privacy.html`
- Cubren: Recopilación, uso, compartir, derechos, cookies, servicios de terceros
- Cumplen con RGPD

#### ¿Hay Consentimiento Explícito para Cookies No Esenciales?
**SÍ** - Banner de cookies implementado
- Opción de aceptar/rechazar/personalizar
- Google Analytics solo se carga con consentimiento

#### ¿Se Puede Eliminar Cuenta y Datos?
**PARCIALMENTE** - No hay endpoint automático
- Usuario debe contactar a `contacto@yourgains.ai`
- Se puede implementar endpoint `/api/user/delete` para auto-eliminación

#### ¿Cumple GDPR/LOPDGDD?
**SÍ** - Implementado:
- ✅ Consentimiento explícito para cookies
- ✅ Política de privacidad completa
- ✅ Derechos del usuario documentados
- ✅ Base legal para procesamiento documentada
- ✅ Retención de datos especificada
- ✅ Transferencias internacionales con salvaguardias

### 11.3 PAGOS

#### ¿Los Webhooks Están Bien Manejados?
**SÍ** - Implementación robusta:
- Verificación de firma con `STRIPE_WEBHOOK_SECRET`
- Manejo de eventos: `created`, `updated`, `deleted`
- Lock mechanism para evitar generaciones duplicadas
- Manejo de errores y logging

#### ¿Hay Gestión de Errores en Pagos?
**SÍ** - Implementado:
- Try-catch en todos los endpoints de Stripe
- Logging de errores
- Mensajes de error claros al usuario
- Fallbacks cuando es posible

#### ¿Las Cancelaciones Funcionan Correctamente?
**SÍ** - Webhook `customer.subscription.deleted` maneja:
- Cambio de `is_premium = False`
- Cambio de `plan_type = "FREE"`
- Mantiene contenido del usuario (solo cambia visibilidad)

#### ¿Se Sincronizan Stripe y BD Siempre?
**SÍ** - Múltiples puntos de sincronización:
- Webhook `subscription.created` - Activa premium
- Webhook `subscription.updated` - Actualiza estado
- Webhook `subscription.deleted` - Desactiva premium
- Endpoint `/activate-premium` - Sincronización manual (desarrollo)

---

## CONCLUSIÓN

Este documento proporciona una visión completa y exhaustiva del proyecto YourGains AI. Todas las secciones han sido documentadas en detalle para facilitar la revisión legal, técnica y de configuración antes del lanzamiento en producción.

**Última actualización:** Enero 2026  
**Mantenido por:** Equipo de desarrollo YourGains AI  
**Contacto:** contacto@yourgains.ai

