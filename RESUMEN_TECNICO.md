# 📋 RESUMEN TÉCNICO - YourGains AI

## 🎯 Visión General

**YourGains AI** es una plataforma web de entrenamiento personal y nutrición basada en inteligencia artificial que genera rutinas de entrenamiento y planes nutricionales personalizados utilizando GPT-4o con un sistema RAG (Retrieval Augmented Generation) alimentado por 46 documentos científicos.

---

## 🛠️ Stack Tecnológico

### **Backend**
- **Framework**: FastAPI (Python 3.x)
- **Base de Datos**: SQLite (desarrollo) / PostgreSQL (producción - configurable)
- **ORM**: SQLAlchemy
- **Autenticación**: JWT (JSON Web Tokens) + OAuth2 (Google)
- **Pagos**: Stripe API (Checkout Sessions para suscripciones)
- **Webhooks**: Stripe Webhooks para eventos de pago

### **Frontend**
- **HTML/CSS/JavaScript** vanilla
- **Tailwind CSS** para estilos
- **Responsive Design** (mobile-first)
- **Fonts**: Inter (Google Fonts)

### **IA y Machine Learning**
- **OpenAI API**:
  - **GPT-4o** para generación de planes personalizados
  - **GPT-4o-mini** para chat de asistente
  - **text-embedding-3-small** para embeddings del sistema RAG
- **Sistema RAG**: Vectorstore personalizado con búsqueda semántica

### **Infraestructura**
- **Servidor**: Uvicorn (ASGI)
- **Deployment**: Railway (planificado)
- **Variables de Entorno**: python-dotenv

---

## 🤖 Modelos de IA y RAG

### **Modelos Utilizados**

#### **1. GPT-4o** (Generación de Planes)
- **Uso**: Generación de rutinas de entrenamiento y planes nutricionales personalizados
- **Contexto**: Sistema RAG completo con 46 documentos científicos
- **Costo**:
  - Input: $0.005 por 1K tokens
  - Output: $0.015 por 1K tokens
  - **Costo promedio por plan**: ~$0.015-0.025 USD
- **Características**:
  - Retry logic con exponential backoff (3 intentos)
  - Timeout: 120 segundos
  - Manejo de rate limits y errores temporales

#### **2. GPT-4o-mini** (Chat de Asistente)
- **Uso**: Chat interactivo con usuarios sobre fitness y nutrición
- **Contexto**: RAG limitado (top 5 documentos relevantes)
- **Costo**: Significativamente menor que GPT-4o
- **Características**:
  - Respuestas limitadas a 200 palabras
  - Streaming de respuestas (Server-Sent Events)
  - Temperature: 0.7

#### **3. text-embedding-3-small** (Embeddings RAG)
- **Uso**: Generación de embeddings para búsqueda semántica
- **Costo**: $0.02 por 1M tokens (~$0.000003 por query)
- **Dimensionalidad**: 1536 dimensiones

### **Sistema RAG (Retrieval Augmented Generation)**

#### **Base de Conocimiento**
- **46 documentos científicos** en formato JSON
- **Temas cubiertos**:
  - Hipertrofia y entrenamiento de fuerza
  - Nutrición deportiva y macronutrientes
  - Periodización y programación
  - Recuperación y descanso
  - Lesiones y prevención
  - Técnicas avanzadas (RIR, drop sets, etc.)
  - Tipos de fibras musculares
  - Suplementación

#### **Funcionamiento del RAG**

**Para Generación de Planes:**
1. **Queries Específicas**: Se generan múltiples queries basadas en:
   - Objetivo del usuario (hipertrofia, fuerza, pérdida de grasa)
   - Experiencia (principiante, intermedio, avanzado)
   - Frecuencia de entrenamiento
   - Objetivo nutricional (volumen, definición, mantenimiento)
   - Lesiones y restricciones
   - Alergias alimentarias
   - Materiales disponibles

2. **Búsqueda Semántica**: 
   - Cada query genera un embedding
   - Búsqueda por similitud coseno en el vectorstore
   - Top 1 documento por query (optimizado para tokens)
   - Máximo 6 documentos únicos totales

3. **Inyección de Contexto**:
   - Contexto científico formateado se inyecta en el prompt de GPT-4o
   - Limita contenido a 1000 caracteres por documento
   - Referencias científicas incluidas (PMID cuando disponible)

**Para Chat:**
- Búsqueda más simple: top 5 documentos relevantes al mensaje del usuario
- Contexto limitado para mantener respuestas concisas

#### **Optimizaciones de Costo**
- **Queries en paralelo**: Ejecución asíncrona de múltiples queries RAG
- **Límite de documentos**: Máximo 6 documentos únicos para planes
- **Truncado de contenido**: 1000 caracteres por documento
- **Costo total RAG**: ~$0.000003 por plan (despreciable vs GPT-4o)

---

## 💾 Base de Datos

### **Modelo de Datos**

#### **Tabla: `usuarios`**
```python
- id (Integer, PK)
- email (String, unique, indexed)
- hashed_password (String, nullable)  # Para auth tradicional
- google_id (String, nullable)  # OAuth Google
- oauth_provider (String, nullable)
- profile_picture (String, nullable)
- is_premium (Boolean, default=False)
- stripe_customer_id (String, nullable)
- stripe_subscription_id (String, nullable)  # Para Customer Portal
- plan_type (String, default="FREE")  # FREE | PREMIUM_MONTHLY | PREMIUM_YEARLY
- chat_uses_free (Integer, default=2)  # Preguntas gratis restantes
- onboarding_completed (Boolean, default=False)
- current_routine (Text, JSON)  # Rutina actual del usuario
- current_diet (Text, JSON)  # Dieta actual del usuario
- injuries (Text, JSON array)
- focus_areas (Text, JSON array)
- disliked_foods (Text, JSON array)
- modification_history (Text, JSON array)
```

#### **Tabla: `planes`**
```python
- id (Integer, PK)
- user_id (Integer, FK -> usuarios.id)
- altura, peso, edad, sexo
- experiencia (String)
- objetivo_gym (String)  # ganar_musculo, ganar_fuerza, etc.
- objetivo_nutricional (String)  # volumen, definicion, mantenimiento
- materiales (String)
- tipo_cuerpo (String, nullable)
- nivel_actividad (String, default="moderado")
- idioma (String, default="es")
- puntos_fuertes, puntos_debiles (String, nullable)
- entrenar_fuerte (String, nullable)
- lesiones, alergias, restricciones_dieta (String, nullable)
- rutina (Text, JSON)
- dieta (Text, JSON)
- motivacion (Text)
- fecha_creacion (DateTime)
```

### **Relaciones**
- `Usuario` 1:N `Plan` (un usuario puede tener múltiples planes históricos)

---

## 🔐 Autenticación y Seguridad

### **Métodos de Autenticación**
1. **Google OAuth2**: Login social con Google
2. **JWT Tokens**: Tokens Bearer para API requests
3. **Términos y Condiciones**: Aceptación obligatoria antes de registro

### **Seguridad**
- **CORS**: Configurado para desarrollo (abierto) - ajustar para producción
- **HTTPS**: Requerido en producción
- **Variables de Entorno**: Credenciales sensibles en `.env`
- **Stripe**: PCI DSS compliant (no almacenamos datos de tarjetas)

---

## 💳 Sistema de Pagos (Stripe)

### **Flujo de Suscripción**
1. **Checkout Session**: Usuario redirigido a Stripe Hosted Checkout
2. **Webhook**: `checkout.session.completed` activa suscripción
3. **Customer Portal**: Usuarios pueden gestionar/cancelar suscripciones

### **Planes Disponibles**
- **PREMIUM_MONTHLY**: Suscripción mensual
- **PREMIUM_YEARLY**: Suscripción anual
- **FREE**: Plan gratuito con limitaciones

### **Características Premium**
- Generación ilimitada de planes personalizados
- Chat con IA ilimitado
- Acceso completo a rutinas y dietas
- Consejos y estudios científicos

### **Características Free**
- 2 preguntas gratis en el chat
- Plan básico limitado (2 días de rutina)
- Acceso limitado a funcionalidades

---

## 📱 Funcionalidades Principales

### **1. Onboarding**
- Formulario completo de datos del usuario:
  - Datos físicos (altura, peso, edad, sexo)
  - Objetivos (gym y nutricional)
  - Experiencia y nivel de actividad
  - Materiales disponibles
  - Lesiones y alergias
  - Días de entrenamiento preferidos
- Genera primer plan personalizado automáticamente

### **2. Generación de Planes Personalizados**
- **Input**: Datos del usuario + preferencias
- **Proceso**:
  1. Recuperación de contexto RAG (46 documentos científicos)
  2. Generación con GPT-4o
  3. Validación y parsing de JSON
  4. Cálculo nutricional automático
  5. Almacenamiento en BD
- **Output**: Rutina completa + Plan nutricional detallado

### **3. Dashboard Principal**
- **Rutina y Dieta**: Visualización completa del plan actual
- **Chat con IA**: Asistente de fitness con RAG limitado
- **Consejos y Estudios**: Artículos científicos con referencias (PMID)
- **Mis Datos**: Edición de perfil y regeneración de plan
- **Tarifas**: Gestión de suscripción y pago

### **4. Chat con IA**
- Streaming de respuestas (Server-Sent Events)
- Contexto RAG dinámico basado en pregunta
- Límite de 200 palabras por respuesta
- Sistema freemium: 2 preguntas gratis, ilimitado para premium

### **5. Gestión de Suscripciones**
- Stripe Checkout para nuevos pagos
- Stripe Customer Portal para gestión
- Webhooks para sincronización automática
- Manejo de renovaciones y cancelaciones

---

## 📊 Costos Operativos Estimados

### **Por Plan Generado**
- **GPT-4o**: ~$0.015-0.025 USD
  - Input: ~3000 tokens × $0.005/1K = $0.015
  - Output: ~1000 tokens × $0.015/1K = $0.015
- **RAG Embeddings**: ~$0.000003 USD (despreciable)
- **Total**: ~$0.015-0.025 USD por plan

### **Por Mensaje de Chat**
- **GPT-4o-mini**: ~$0.0001-0.0005 USD (muy económico)
- **RAG Embeddings**: ~$0.000003 USD
- **Total**: ~$0.0001-0.0005 USD por mensaje

### **Costos Mensuales Estimados** (100 usuarios activos)
- **Planes generados**: 100 planes/mes × $0.02 = **$2.00/mes**
- **Chat**: 1000 mensajes/mes × $0.0003 = **$0.30/mes**
- **Total IA**: **~$2.30/mes**
- **Infraestructura**: Railway/Hosting (~$5-20/mes según tráfico)
- **Stripe**: 2.9% + $0.30 por transacción (solo en ventas)

---

## 🚀 Arquitectura del Sistema

### **Estructura de Directorios**
```
Backend/app/
├── routes/          # Endpoints de la API
│   ├── auth.py      # Autenticación
│   ├── oauth.py     # Google OAuth
│   ├── plan.py      # Generación de planes
│   ├── chat.py      # Chat con IA
│   ├── stripe_routes.py  # Pagos
│   └── stripe_webhook.py # Webhooks
├── utils/
│   ├── gpt.py       # Lógica GPT-4o y RAG
│   ├── vectorstore.py  # Sistema RAG
│   └── nutrition_calculator.py  # Cálculos nutricionales
├── knowledge/       # 46 documentos científicos (JSON)
├── models.py        # Modelos SQLAlchemy
├── schemas.py       # Pydantic schemas
└── frontend/        # Archivos HTML/JS/CSS
```

### **Flujo de Generación de Plan**
```
Usuario → Onboarding → Datos del Usuario
    ↓
get_rag_context_for_plan() → 6-10 queries RAG → 6 documentos científicos
    ↓
generar_plan_personalizado() → GPT-4o con contexto RAG
    ↓
Validación JSON → Cálculo nutricional → Almacenamiento BD
    ↓
Respuesta al frontend → Visualización en Dashboard
```

---

## 🔄 Estado Actual del Proyecto

### **✅ Completado**
- ✅ Sistema de autenticación (Google OAuth + JWT)
- ✅ Generación de planes con GPT-4o + RAG
- ✅ Chat con IA (GPT-4o-mini + RAG limitado)
- ✅ Sistema de pagos con Stripe (Checkout + Portal)
- ✅ Dashboard completo con todas las funcionalidades
- ✅ Onboarding completo
- ✅ Términos y Condiciones + Política de Privacidad (RGPD compliant)
- ✅ Sistema freemium funcional
- ✅ Diseño responsive (en proceso de optimización)

### **🔄 En Proceso**
- 🔄 Optimización responsive (mobile + desktop)
- 🔄 Testing de funcionalidades en diferentes dispositivos

### **📋 Pendiente**
- ⏳ Landing page
- ⏳ Migración a Stripe modo producción (después de trámites fiscales)
- ⏳ Deployment a Railway
- ⏳ Optimizaciones de rendimiento
- ⏳ Testing completo end-to-end

---

## 📈 Escalabilidad

### **Limitaciones Actuales**
- SQLite en desarrollo (migrar a PostgreSQL en producción)
- Sin caché de respuestas RAG (mejorable)
- Sin rate limiting en API (añadir para producción)

### **Mejoras Futuras**
- Caché de embeddings RAG para queries comunes
- Rate limiting por usuario
- CDN para assets estáticos
- Base de datos PostgreSQL con pooling
- Monitoring y logging avanzado (Sentry, etc.)

---

## 🔒 Cumplimiento Legal

### **RGPD/GDPR**
- ✅ Política de Privacidad completa
- ✅ Términos y Condiciones completos
- ✅ Derechos del usuario implementados
- ✅ Consentimiento explícito para términos
- ✅ Información sobre procesamiento de datos

### **Pagos**
- ✅ Stripe PCI DSS compliant
- ✅ No almacenamos datos de tarjetas
- ✅ Webhooks seguros con verificación de firma

---

## 📝 Notas Técnicas Importantes

1. **RAG Optimizado**: Sistema diseñado para minimizar tokens manteniendo calidad científica
2. **Retry Logic**: Manejo robusto de errores de OpenAI con exponential backoff
3. **Streaming**: Chat usa Server-Sent Events para mejor UX
4. **Validación**: Parsing y validación estricta de respuestas JSON de GPT
5. **Freemium**: Sistema de límites implementado para usuarios gratuitos

---

## 🎯 Próximos Pasos

1. **Testing Responsive**: Verificar funcionamiento en móvil y desktop
2. **Landing Page**: Página de aterrizaje profesional
3. **Stripe Producción**: Cambiar a claves de producción después de trámites
4. **Deployment Railway**: Configurar y desplegar en Railway
5. **Optimizaciones**: Mejoras de rendimiento y UX

---

**Última actualización**: Diciembre 2024  
**Versión**: 1.0 (Pre-lanzamiento)


