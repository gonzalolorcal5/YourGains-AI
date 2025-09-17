// Configuración común para el frontend
export const API_BASE = "https://yourgains-ai-production-d7dd.up.railway.app";

// Versión no-module para compatibilidad
if (typeof window !== 'undefined') {
  window.API_BASE = API_BASE;
}
