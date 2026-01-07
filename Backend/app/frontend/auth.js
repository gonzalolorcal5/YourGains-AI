// Sistema de autenticación unificado con FastAPI
import { API_BASE } from "./config.js";

function saveAuth(token, email) {
  localStorage.setItem("accessToken", token);
  localStorage.setItem("email", email);
  localStorage.setItem("loginTimestamp", Date.now().toString());
}

export async function doRegister(email, password) {
  const res = await fetch(`${API_BASE}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Error registro: ${res.status}`);
  }
  return await res.json();
}

export async function doLogin(email, password) {
  const res = await fetch(`${API_BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Error login: ${res.status}`);
  }
  const data = await res.json(); // { access_token, token_type, onboarding_completed }
  if (!data.access_token) throw new Error("Sin access_token");
  saveAuth(data.access_token, email);
  
  // Guardar estado de onboarding
  localStorage.setItem("onboarding_completed", data.onboarding_completed ? "true" : "false");
  
  return data;
}

export function getAuthHeaders() {
  const token = localStorage.getItem("accessToken");
  const email = localStorage.getItem("email");
  
  if (!token) {
    console.error("No hay token de autenticación");
    return null;
  }
  
  return {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${token}`,
    "X-User-Email": email || "",
  };
}

export async function checkAuthOrRedirect() {
  // 🎯 Verificar primero si hay parámetros de pago exitoso de Stripe
  const urlParams = new URLSearchParams(window.location.search);
  const successParam = urlParams.get('success');
  const sessionIdParam = urlParams.get('session_id');
  const isStripeSuccess = successParam === '1' && sessionIdParam && sessionIdParam.startsWith('cs_test');
  
  const token = localStorage.getItem("accessToken");
  let email = localStorage.getItem("email");
  
  // Si hay parámetros de pago exitoso y no hay token, permitir acceso temporal
  if (isStripeSuccess && !token) {
    console.log("⚠️ Token no encontrado, pero se permite acceso temporal por verificación de pago activa");
    return true; // Permitir acceso temporal para que checkPaymentSuccess pueda actuar
  }

  // Intentar recuperar email del JWT si falta en localStorage
  if (token && !email) {
    const decoded = decodeJwt(token);
    if (decoded && decoded.email) {
      email = decoded.email;
      localStorage.setItem("email", decoded.email);
    }
  }

  // 🎯 Si se está procesando un pago, ser más flexible con el token
  // Esperar 5 segundos extra antes de redirigir para dar tiempo a sincronización
  const isProcessingPayment = window.isProcessingPayment === true;
  
  if (isProcessingPayment) {
    console.log('💳 Pago en proceso: verificando autenticación con flexibilidad adicional...');
    
    // Si no hay token o email, esperar 5 segundos antes de redirigir
    if (!token || !email) {
      console.log('⏳ Esperando 5 segundos para sincronización durante el pago...');
      await new Promise(resolve => setTimeout(resolve, 5000));
      
      // Verificar de nuevo después de esperar
      const tokenAfterWait = localStorage.getItem("accessToken");
      const emailAfterWait = localStorage.getItem("email") || (tokenAfterWait && decodeJwt(tokenAfterWait)?.email);
      
      if (!tokenAfterWait || !emailAfterWait) {
        if (isStripeSuccess) {
          console.log("⚠️ Token no encontrado, pero se permite acceso temporal por verificación de pago activa");
          return true; // Permitir acceso temporal para que checkPaymentSuccess pueda actuar
        }
        console.log('❌ Sin token después de esperar, redirigiendo a login...');
        logout();
        return false;
      }
      
      // Actualizar variables locales
      token = tokenAfterWait;
      email = emailAfterWait;
    }
    
    // Si el token está "expirado", también esperar antes de redirigir
    if (isTokenExpired()) {
      console.log('⏳ Token aparentemente expirado, esperando 5 segundos adicionales durante pago...');
      await new Promise(resolve => setTimeout(resolve, 5000));
      
      // Verificar de nuevo
      const tokenAfterWait = localStorage.getItem("accessToken");
      const emailAfterWait = localStorage.getItem("email") || (tokenAfterWait && decodeJwt(tokenAfterWait)?.email);
      
      // Si después de esperar sigue expirado o no existe, redirigir
      if (!tokenAfterWait || !emailAfterWait || isTokenExpired()) {
        if (isStripeSuccess) {
          console.log("⚠️ Token no encontrado, pero se permite acceso temporal por verificación de pago activa");
          return true; // Permitir acceso temporal para que checkPaymentSuccess pueda actuar
        }
        console.log('❌ Token aún inválido después de esperar, redirigiendo a login...');
        logout();
        return false;
      }
      
      console.log('✅ Token válido después de esperar, continuando...');
      return true;
    }
  } else {
    // Comportamiento normal: si no hay token o email, o el token está expirado, forzar logout
    // EXCEPTO si hay parámetros de pago exitoso de Stripe
    if (!token || !email || isTokenExpired()) {
      if (isStripeSuccess) {
        console.log("⚠️ Token no encontrado, pero se permite acceso temporal por verificación de pago activa");
        return true; // Permitir acceso temporal para que checkPaymentSuccess pueda actuar
      }
      logout();
      return false;
    }
  }
  
  return true;
}

export function logout() {
  localStorage.clear();
  window.location.href = "./login.html";
}

// Funciones de utilidad para compatibilidad
export function isTokenExpired() {
  const token = localStorage.getItem("accessToken");
  
  if (!token) return true;
  
  try {
    // Intentar decodificar el payload del JWT (segunda parte del token)
    const payloadBase64 = token.split('.')[1];
    if (payloadBase64) {
      const decoded = JSON.parse(atob(payloadBase64));
      // Si el token tiene fecha de expiración (exp), usarla con 1 minuto de margen
      if (decoded && typeof decoded.exp === "number") {
        // Multiplicamos por 1000 porque JWT usa segundos y JS milisegundos
        return Date.now() >= (decoded.exp * 1000) - 60000;
      }
    }
  } catch (e) {
    console.warn("Advertencia: No se pudo verificar expiración del JWT, usando fallback local.", e);
  }
  
  // FALLBACK: Si no podemos leer el token, usar el timestamp local
  // Cambiamos 5 minutos por 24 horas para evitar desconexiones durante el pago
  const loginTs = parseInt(localStorage.getItem("loginTimestamp") || "0");
  const oneDay = 24 * 60 * 60 * 1000; 
  
  if (!loginTs) return false; // Si no hay timestamp, asumimos válido para no bloquear
  return (Date.now() - loginTs) > oneDay;
}

export function decodeJwt(token) {
  try {
    return JSON.parse(atob(token.split('.')[1]));
  } catch (e) {
    return null;
  }
}

// Hacer funciones disponibles globalmente para compatibilidad
if (typeof window !== 'undefined') {
  window.logout = logout;
  window.getAuthHeaders = getAuthHeaders;
  window.checkAuthOrRedirect = checkAuthOrRedirect;
  window.isTokenExpired = isTokenExpired;
  window.decodeJwt = decodeJwt;
  // Inicializar isProcessingPayment en false si no existe
  if (window.isProcessingPayment === undefined) {
    window.isProcessingPayment = false;
  }
}