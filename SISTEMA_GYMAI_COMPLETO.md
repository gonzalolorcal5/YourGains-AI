# 🏋️ SISTEMA GYMAI - DOCUMENTACIÓN COMPLETA PARA CLAUDE

## 📋 RESUMEN EJECUTIVO

**GymAI** es una aplicación de fitness con IA que genera rutinas y dietas personalizadas, con capacidades de modificación dinámica basadas en conversaciones naturales del usuario. El sistema incluye un modelo freemium con usuarios FREE (contenido genérico) y PREMIUM (contenido personalizado).

---

## 🏗️ ARQUITECTURA DEL SISTEMA

### **Tecnologías Principales:**
- **Backend**: FastAPI (Python)
- **Base de Datos**: SQLite con SQLAlchemy ORM
- **IA**: OpenAI GPT-3.5/GPT-4 con Function Calling
- **Frontend**: HTML/JavaScript vanilla
- **Pagos**: Stripe API
- **Autenticación**: JWT + Supabase (opcional)

### **Estructura de Directorios:**
```
Backend/
├── app/
│   ├── models.py              # Modelos de BD (Usuario, Plan)
│   ├── database.py            # Configuración SQLAlchemy
│   ├── main.py               # Aplicación FastAPI principal
│   ├── auth_utils.py         # Utilidades de autenticación
│   ├── schemas.py            # Esquemas Pydantic
│   ├── routes/               # Endpoints de la API
│   │   ├── onboarding.py     # Proceso de registro inicial
│   │   ├── plan.py          # Gestión de rutinas/dietas
│   │   ├── chat_modify_optimized.py  # Chat con IA + modificaciones
│   │   ├── stripe_routes.py  # Pagos y activación premium
│   │   └── user_status.py    # Estado del usuario
│   └── utils/                # Servicios y utilidades
│       ├── function_handlers_optimized.py  # Lógica de modificaciones
│       ├── functions_definitions.py       # Definiciones para OpenAI
│       ├── database_service.py            # Servicio de BD centralizado
│       ├── routine_templates.py           # Plantillas genéricas
│       └── nutrition_calculator.py        # Cálculos nutricionales
└── frontend/                 # Interfaz de usuario
    ├── dashboard.html        # Dashboard principal
    ├── login.html           # Página de login
    └── onboarding.html      # Formulario de registro
```

---

## 🗄️ ESTRUCTURA DE BASE DE DATOS

### **Tabla `usuarios`:**
```sql
- id (PK)                     # Identificador único
- email (UNIQUE)              # Email del usuario
- hashed_password             # Contraseña hasheada
- is_premium (BOOLEAN)        # Estado premium
- stripe_customer_id          # ID de cliente en Stripe
- plan_type (STRING)          # "FREE" | "PREMIUM"
- chat_uses_free (INTEGER)    # Preguntas gratis restantes
- onboarding_completed (BOOLEAN)  # Si completó el registro
- current_routine (TEXT/JSON) # Rutina actual del usuario
- current_diet (TEXT/JSON)    # Dieta actual del usuario
- injuries (TEXT/JSON)        # Historial de lesiones
- focus_areas (TEXT/JSON)     # Áreas de enfoque
- disliked_foods (TEXT/JSON)  # Alimentos que no le gustan
- modification_history (TEXT/JSON)  # Historial de modificaciones
```

### **Tabla `planes`:**
```sql
- id (PK)                     # Identificador único
- user_id (FK)                # Referencia a usuarios.id
- altura (INTEGER)            # Altura en cm
- peso (STRING)               # Peso en kg
- edad (INTEGER)              # Edad
- sexo (STRING)               # "masculino" | "femenino"
- experiencia (STRING)        # Nivel de experiencia
- objetivo (STRING)           # Objetivo del plan
- materiales (STRING)         # Equipamiento disponible
- tipo_cuerpo (STRING)        # Tipo de cuerpo
- nivel_actividad (STRING)    # Nivel de actividad física
- rutina (TEXT/JSON)          # Rutina generada
- dieta (TEXT/JSON)           # Dieta generada
- motivacion (TEXT)           # Mensaje motivacional
- fecha_creacion (DATETIME)   # Fecha de creación
```

---

## 🎯 FUNCIONALIDADES PRINCIPALES

### **1. Sistema de Onboarding**
- **Formulario avanzado** con objetivos separados (gym vs nutrición)
- **Selector de frecuencia** de entrenamiento (3-6 días/semana)
- **Checkboxes de días específicos** de la semana
- **Generación automática** de plan inicial con GPT
- **Guardado en BD** tanto en `usuarios` como en `planes`

### **2. Sistema Freemium**
- **Usuarios FREE**: Reciben rutinas/dietas genéricas personalizadas con sus datos
- **Usuarios PREMIUM**: Reciben planes completamente personalizados
- **Activación automática** de premium vía Stripe con fallback manual

### **3. Chat con IA + Modificaciones Dinámicas**
El sistema permite modificaciones conversacionales usando OpenAI Function Calling:

#### **Modificaciones de Rutina:**
- `modify_routine_injury` - Adaptar por lesiones
- `modify_routine_focus` - Enfocar grupos musculares específicos
- `adjust_routine_difficulty` - Ajustar dificultad (más/menos días)
- `substitute_exercise` - Sustituir ejercicios específicos
- `modify_routine_equipment` - Adaptar por equipamiento disponible

#### **Modificaciones de Dieta:**
- `recalculate_diet_macros` - Recalcular macros por peso/objetivo
- `substitute_disliked_food` - Sustituir alimentos no deseados
- `generate_meal_alternatives` - Generar alternativas de comidas
- `simplify_diet` - Simplificar complejidad de la dieta

#### **Sistema de Control de Calorías Flexible:**
- **Modo 1**: Calorías totales exactas ("Quiero 3500 calorías")
- **Modo 2**: Ajuste personalizado ("Súbeme 200 calorías")
- **Modo 3**: Automático por objetivo (volumen +300, definición -300)

### **4. Sistema de Historial y Snapshots**
- **Registro automático** de todas las modificaciones
- **Snapshots** de rutina/dieta antes de cambios
- **Función de reversión** para deshacer modificaciones
- **Trazabilidad completa** de cambios

---

## 🔧 ENDPOINTS PRINCIPALES

### **Autenticación y Usuario:**
- `POST /register` - Registro de usuario
- `POST /login` - Login
- `GET /user-status` - Estado del usuario
- `GET /user/current-routine` - Obtener rutina actual
- `GET /user/current-diet` - Obtener dieta actual

### **Onboarding:**
- `POST /onboarding` - Proceso de registro inicial
- `GET /onboarding.html` - Formulario de onboarding

### **Chat y Modificaciones:**
- `POST /api/chat/modify` - Chat con IA + modificaciones dinámicas
- `GET /chat/status` - Estado del chat

### **Pagos:**
- `POST /create-checkout-session` - Crear sesión de pago Stripe
- `POST /stripe/activate-premium` - Activar premium (fallback)
- `POST /stripe/webhook` - Webhook de Stripe

### **Planes:**
- `POST /generar-rutina` - Generar nueva rutina
- `GET /planes` - Listar planes del usuario
- `GET /planes/ultimo/pdf` - Descargar PDF del último plan

---

## 🤖 SISTEMA DE IA Y MODIFICACIONES

### **OpenAI Function Calling:**
El sistema usa OpenAI Function Calling para detectar intenciones del usuario y ejecutar modificaciones automáticamente.

**Ejemplo de conversación:**
```
Usuario: "Me lesioné el hombro, no puedo hacer press de banca"
IA: Detecta → modify_routine_injury(body_part="hombro", injury_type="dolor", severity="moderate")
Sistema: Elimina ejercicios de pecho, sustituye por alternativas seguras
```

### **Flujo de Modificación:**
1. **Usuario envía mensaje** al chat
2. **IA analiza** el mensaje y detecta intención
3. **Se ejecuta función** correspondiente con parámetros extraídos
4. **Se modifica** rutina/dieta según la función
5. **Se actualiza** base de datos con cambios
6. **Se registra** en historial de modificaciones
7. **Se responde** al usuario con resumen de cambios

### **Validaciones y Seguridad:**
- **Validación de parámetros** antes de ejecutar funciones
- **Snapshots automáticos** antes de modificaciones
- **Rollback** en caso de errores
- **Límites de uso** para usuarios FREE
- **Validación de datos** con Pydantic

---

## 💰 SISTEMA DE PAGOS Y PREMIUM

### **Modelo Freemium:**
- **FREE**: 2 preguntas de chat, rutinas genéricas personalizadas
- **PREMIUM**: Chat ilimitado, planes completamente personalizados

### **Activación de Premium:**
1. **Usuario paga** vía Stripe Checkout
2. **Stripe redirige** con parámetros de éxito
3. **Frontend detecta** redirect y llama a `/stripe/activate-premium`
4. **Backend verifica** pago y activa premium
5. **Usuario recibe** acceso completo

### **Fallback para Desarrollo:**
- **Endpoint manual** `/stripe/activate-premium` para activar sin webhook
- **Detección automática** de redirects de Stripe
- **Sistema robusto** que funciona en desarrollo y producción

---

## 📊 SISTEMA DE DATOS Y PERSONALIZACIÓN

### **Problema Actual Identificado:**
Los datos físicos del usuario (peso, altura, edad, sexo) están en la tabla `planes` pero las modificaciones se guardan en `usuarios.current_routine/diet`, creando desincronización.

### **Solución Propuesta:**
1. **Añadir campos físicos** a la tabla `usuarios`
2. **Sincronización automática** entre `usuarios` y `planes`
3. **Actualización en tiempo real** de datos durante modificaciones
4. **Historial completo** de cambios físicos

### **Campos Propuestos para `usuarios`:**
```sql
- peso (STRING)               # Peso actual
- altura (INTEGER)           # Altura en cm
- edad (INTEGER)             # Edad actual
- sexo (STRING)              # Sexo
- objetivo_nutricional (STRING)  # Objetivo nutricional actual
- objetivo_gym (STRING)      # Objetivo de gimnasio actual
- nivel_actividad (STRING)   # Nivel de actividad actual
```

---

## 🔄 FLUJO DE MODIFICACIONES

### **Ejemplo: Usuario dice "Subí 2 kilos"**

1. **IA detecta**: `recalculate_diet_macros(weight_change_kg=2)`
2. **Sistema obtiene**: Peso actual del usuario
3. **Calcula**: Nuevo peso = peso_actual + 2
4. **Actualiza**: Campo `peso` en tabla `usuarios`
5. **Recalcula**: TMB, TDEE, macros con nuevo peso
6. **Ajusta**: Cantidades de alimentos proporcionalmente
7. **Guarda**: Nueva dieta en `usuarios.current_diet`
8. **Registra**: Modificación en historial
9. **Responde**: "Dieta actualizada para tu nuevo peso de X kg"

### **Sistema de Snapshots:**
```json
{
  "modification_history": [
    {
      "id": "mod_123",
      "type": "diet_recalculate",
      "timestamp": "2024-01-15T10:30:00Z",
      "changes": {
        "peso_antes": 75.0,
        "peso_despues": 77.0,
        "calorias_antes": 2500,
        "calorias_despues": 2600,
        "modo_ajuste": "automatico"
      },
      "previous_diet": { /* snapshot de dieta anterior */ }
    }
  ]
}
```

---

## 🎨 FRONTEND Y UX

### **Dashboard Principal:**
- **Visualización** de rutina y dieta actual
- **Chat integrado** para modificaciones
- **Indicadores** de estado premium
- **Historial** de modificaciones
- **Botones** de activación premium

### **Sistema de Notificaciones:**
- **Feedback visual** de modificaciones exitosas
- **Mensajes de error** claros y útiles
- **Indicadores** de progreso durante modificaciones
- **Confirmaciones** de cambios importantes

### **Responsive Design:**
- **Mobile-first** approach
- **Adaptación** a diferentes tamaños de pantalla
- **Interfaz intuitiva** para todos los dispositivos

---

## 🚀 ESTADO ACTUAL Y PRÓXIMOS PASOS

### **✅ Funcionalidades Completadas:**
- Sistema de onboarding avanzado
- Chat con IA y modificaciones dinámicas
- Sistema freemium funcional
- Activación de premium vía Stripe
- 15+ funciones de modificación implementadas
- Sistema de historial y snapshots
- Control flexible de calorías
- Plantillas genéricas personalizadas

### **🔧 Mejoras Pendientes:**
1. **Sincronización de datos físicos** entre `usuarios` y `planes`
2. **Migración de BD** para añadir campos físicos a `usuarios`
3. **Sistema de notificaciones** más robusto
4. **Optimización** de rendimiento en consultas
5. **Tests automatizados** para funciones críticas
6. **Dashboard de administración** para monitoreo

### **🎯 Objetivos a Corto Plazo:**
- Implementar sincronización de datos físicos
- Mejorar precisión de recomendaciones
- Añadir más funciones de modificación
- Optimizar experiencia de usuario
- Preparar para escalabilidad

---

## 📝 NOTAS TÉCNICAS IMPORTANTES

### **Configuración de Entorno:**
- **Desarrollo**: Usa GPT-3.5 Turbo (20x más barato)
- **Producción**: Usa GPT-4 Turbo (mayor precisión)
- **Base de datos**: SQLite para desarrollo, PostgreSQL para producción
- **Pagos**: Stripe en modo test para desarrollo

### **Seguridad:**
- **Validación** de todos los inputs del usuario
- **Sanitización** de datos antes de guardar en BD
- **Autenticación** JWT con tokens seguros
- **Rate limiting** para endpoints críticos

### **Rendimiento:**
- **Caché** de consultas frecuentes
- **Paginación** en listas largas
- **Optimización** de consultas SQL
- **Compresión** de respuestas JSON

---

## 🤝 COLABORACIÓN CON CLAUDE

Este documento proporciona una visión completa del sistema GymAI para que Claude pueda:

1. **Entender** la arquitectura y funcionalidades actuales
2. **Identificar** áreas de mejora y optimización
3. **Proponer** soluciones para problemas específicos
4. **Implementar** nuevas funcionalidades de manera consistente
5. **Mantener** la coherencia del sistema existente

**El sistema está 95% completo y funcional**, con solo algunas mejoras pendientes en sincronización de datos y optimización de rendimiento.

---

*Documento generado el 22 de octubre de 2024 - Versión 1.0*
