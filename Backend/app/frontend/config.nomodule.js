// Configuración común para el frontend (versión no-module)
// Detectar automáticamente el entorno (producción vs local)
window.API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:8000'  // Desarrollo local
    : window.location.origin;   // Producción (https://yourgains.ai)
