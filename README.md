# YourGains AI 🏋️‍♂️

Una aplicación web de entrenamiento personal con inteligencia artificial que crea planes personalizados de ejercicio y nutrición.

## 🚀 Características

- **Chat con IA**: Entrenador personal virtual disponible 24/7
- **Planes Personalizados**: Rutinas de ejercicio adaptadas a tus objetivos
- **Análisis Corporal**: Evaluación completa de tu tipo de cuerpo
- **Seguimiento de Progreso**: Monitoreo de tu evolución fitness
- **Sistema Freemium**: 2 mensajes gratuitos, planes Pro ilimitados

## 🛠️ Tecnologías

### Backend
- **FastAPI**: Framework web moderno y rápido
- **SQLAlchemy**: ORM para base de datos
- **OpenAI GPT-4**: IA para entrenamiento personalizado
- **Stripe**: Pagos y suscripciones
- **SQLite**: Base de datos ligera

### Frontend
- **HTML5/CSS3**: Interfaz moderna y responsive
- **JavaScript**: Funcionalidad interactiva
- **Tailwind CSS**: Estilos y diseño

## 📋 Requisitos

- Python 3.8+
- pip
- Cuenta de OpenAI (API key)
- Cuenta de Stripe (opcional, para pagos)

## 🚀 Instalación

1. **Clonar el repositorio**:
   ```bash
   git clone https://github.com/tu-usuario/gymai.git
   cd gymai
   ```

2. **Crear entorno virtual**:
   ```bash
   python -m venv venv
   ```

3. **Activar entorno virtual**:
   
   **Windows**:
   ```bash
   venv\Scripts\activate
   ```
   
   **macOS/Linux**:
   ```bash
   source venv/bin/activate
   ```

4. **Instalar dependencias**:
   ```bash
   cd Backend
   pip install -r requirements.txt
   ```

5. **Configurar variables de entorno**:
   Crear archivo `.env` en la carpeta `Backend`:
   ```env
   OPENAI_API_KEY=tu_api_key_aqui
   STRIPE_SECRET_KEY=tu_stripe_secret_key
   STRIPE_PUBLISHABLE_KEY=tu_stripe_publishable_key
   JWT_SECRET_KEY=tu_jwt_secret_key
   ```

6. **Ejecutar la aplicación**:
   ```bash
   python run_server.py
   ```

7. **Abrir en el navegador**:
   ```
   http://localhost:8000
   ```

## 📁 Estructura del Proyecto

```
gymai/
├── Backend/
│   ├── app/
│   │   ├── frontend/          # Archivos HTML/CSS/JS
│   │   ├── routes/            # Endpoints de la API
│   │   ├── models.py          # Modelos de base de datos
│   │   ├── schemas.py         # Esquemas Pydantic
│   │   └── main.py           # Aplicación principal
│   ├── requirements.txt       # Dependencias Python
│   └── run_server.py         # Script de inicio
├── .gitignore
└── README.md
```

## 🔧 Uso

### Funcionalidades Principales

1. **Registro/Login**: Sistema de autenticación con JWT
2. **Onboarding**: Configuración inicial del usuario
3. **Chat con IA**: Conversación con el entrenador virtual
4. **Planes de Ejercicio**: Generación automática de rutinas
5. **Suscripciones**: Sistema freemium con Stripe

### Endpoints Principales

- `POST /auth/register` - Registro de usuario
- `POST /auth/login` - Inicio de sesión
- `POST /chat` - Chat con IA
- `POST /onboarding` - Configuración inicial
- `GET /plan/routine` - Obtener rutina personalizada

## 💳 Sistema de Pagos

- **Plan Gratuito**: 2 mensajes de chat
- **Plan Pro**: Mensajes ilimitados + funciones premium
- Integración con Stripe para pagos seguros

## 🔒 Seguridad

- Autenticación JWT
- Validación de datos con Pydantic
- CORS configurado
- Variables de entorno para claves sensibles

## 📱 Responsive Design

- Optimizado para desktop y móvil
- Interfaz adaptativa
- Experiencia de usuario moderna

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 📞 Contacto

Tu Nombre - [@tu_twitter](https://twitter.com/tu_twitter) - email@ejemplo.com

Link del Proyecto: [https://github.com/tu-usuario/gymai](https://github.com/tu-usuario/gymai)

## 🙏 Agradecimientos

- OpenAI por GPT-4
- FastAPI por el framework web
- Stripe por el sistema de pagos
- La comunidad de desarrolladores
