// Configuración común para el frontend
export const API_BASE = "http://127.0.0.1:8000";

// Versión no-module para compatibilidad
if (typeof window !== 'undefined') {
  window.API_BASE = API_BASE;
}
