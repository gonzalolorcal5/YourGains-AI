// Configuración de API inteligente para YourGains AI
const isLocalhost = window.location.hostname === 'localhost' || 
                    window.location.hostname === '127.0.0.1' ||
                    window.location.hostname === '';

// Detectar si el backend está en un subdominio o mismo dominio
const getApiBase = () => {
  if (isLocalhost) {
    // Desarrollo local - puerto del backend
    return 'http://localhost:8000';
  }
  
  // 🔥 PRODUCCIÓN: Siempre devolver https://yourgains.ai
  return 'https://yourgains.ai';
};

export const API_BASE = getApiBase();

// Log para verificar en la consola del navegador
console.log(`[CONFIG] Entorno detectado: ${isLocalhost ? 'LOCAL' : 'PRODUCCIÓN'}`);
console.log(`[CONFIG] Hostname: ${window.location.hostname}`);
console.log(`[CONFIG] API_BASE apuntando a: ${API_BASE}`);
