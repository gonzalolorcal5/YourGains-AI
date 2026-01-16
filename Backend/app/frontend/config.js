// Configuración común para el frontend
// Detectar automáticamente el entorno (producción vs local)
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:8000'  // Desarrollo local
    : window.location.origin;   // Producción (https://yourgains.ai)

export { API_BASE };

// Versión no-module para compatibilidad
if (typeof window !== 'undefined') {
  window.API_BASE = API_BASE;
}
