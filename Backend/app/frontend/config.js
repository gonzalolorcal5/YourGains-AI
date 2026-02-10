// Configuración de API inteligente para YourGains AI
const isLocalhost = window.location.hostname === 'localhost' ||
                    window.location.hostname === '127.0.0.1' ||
                    window.location.hostname === '';

// Local: backend en 127.0.0.1:8000 | Producción: yourgains.ai
export const API_BASE = isLocalhost
  ? 'http://127.0.0.1:8000'
  : 'https://yourgains.ai';

// Log para verificar en la consola del navegador
console.log(`[CONFIG] API_BASE: ${API_BASE}`);

// Exponer también como global para scripts inline (dashboard.html, etc.)
if (typeof window !== 'undefined') {
  window.API_BASE = API_BASE;
}
