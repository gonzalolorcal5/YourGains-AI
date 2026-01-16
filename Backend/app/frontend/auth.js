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
  console.log('🔍 [AUTH] Iniciando verificación de autenticación...');
  
  // 🎯 URGENTE: Detectar si estamos en onboarding.html
  const currentPath = window.location.pathname.toLowerCase();
  const isOnboardingPage = currentPath.includes('onboarding.html');
  
  // 🎯 Verificar primero si hay parámetros de pago exitoso de Stripe
  const urlParams = new URLSearchParams(window.location.search);
  const successParam = urlParams.get('success');
  const sessionIdParam = urlParams.get('session_id');
  const isStripeSuccess = successParam === '1' && sessionIdParam && sessionIdParam.startsWith('cs_test');
  
  let token = localStorage.getItem("accessToken");
  let email = localStorage.getItem("email");
  const onboardingCompleted = localStorage.getItem("onboarding_completed");
  
  console.log('🔍 [AUTH] Estado inicial:', {
    hasToken: !!token,
    hasEmail: !!email,
    onboardingCompleted: onboardingCompleted,
    isStripeSuccess: isStripeSuccess,
    isProcessingPayment: window.isProcessingPayment === true,
    isOnboardingPage: isOnboardingPage,
    currentPath: currentPath
  });
  
  // 🟢 PERMISIVIDAD CRÍTICA: Si estamos en onboarding.html y hay token, PERMITIR SIEMPRE
  if (isOnboardingPage && token) {
    console.log('🟢 [AUTH] Permitiendo estancia en onboarding por presencia de token');
    console.log('🟢 [AUTH] NO se ejecutará NINGUNA redirección al login desde onboarding');
    return true; // PERMITIR SIEMPRE en onboarding si hay token
  }
  
  // Si hay parámetros de pago exitoso y no hay token, permitir acceso temporal
  if (isStripeSuccess && !token) {
    console.log("⚠️ [AUTH] Token no encontrado, pero se permite acceso temporal por verificación de pago activa");
    return true; // Permitir acceso temporal para que checkPaymentSuccess pueda actuar
  }

  // Intentar recuperar email del JWT si falta en localStorage
  if (token && !email) {
    console.log('🔍 [AUTH] Intentando recuperar email del JWT...');
    const decoded = decodeJwt(token);
    if (decoded && decoded.email) {
      email = decoded.email;
      localStorage.setItem("email", decoded.email);
      console.log('✅ [AUTH] Email recuperado del JWT:', email);
    } else {
      console.log('⚠️ [AUTH] No se pudo recuperar email del JWT');
    }
  }

  // ============================================
  // PASO 1: VERIFICAR AUTENTICACIÓN (Token válido)
  // ============================================
  console.log('🔍 [AUTH] PASO 1: Verificando autenticación (token válido)...');
  
  const tokenExists = !!token;
  const emailExists = !!email;
  const tokenExpired = isTokenExpired();
  
  console.log('🔍 [AUTH] Resultado verificación token:', {
    tokenExists,
    emailExists,
    tokenExpired,
    tokenLength: token ? token.length : 0
  });
  
  // 🎯 Si se está procesando un pago, ser más flexible con el token
  const isProcessingPayment = window.isProcessingPayment === true;
  
  if (isProcessingPayment) {
    console.log('💳 [AUTH] Pago en proceso: verificando autenticación con flexibilidad adicional...');
    
    // Si no hay token o email, esperar 5 segundos antes de redirigir
    if (!token || !email) {
      console.log('⏳ [AUTH] Esperando 5 segundos para sincronización durante el pago...');
      await new Promise(resolve => setTimeout(resolve, 5000));
      
      // Verificar de nuevo después de esperar
      const tokenAfterWait = localStorage.getItem("accessToken");
      const emailAfterWait = localStorage.getItem("email") || (tokenAfterWait && decodeJwt(tokenAfterWait)?.email);
      
      if (!tokenAfterWait || !emailAfterWait) {
        if (isStripeSuccess || isOnboardingPage) {
          console.log("⚠️ [AUTH] Token no encontrado, pero se permite acceso temporal por verificación de pago activa o estancia en onboarding");
          return true;
        }
        console.log('❌ [AUTH] Sin token después de esperar, redirigiendo a login...');
        logout();
        return false;
      }
      
      // Actualizar variables locales
      token = tokenAfterWait;
      email = emailAfterWait;
    }
    
    // Si el token está "expirado", también esperar antes de redirigir
    if (tokenExpired) {
      console.log('⏳ [AUTH] Token aparentemente expirado, esperando 5 segundos adicionales durante pago...');
      await new Promise(resolve => setTimeout(resolve, 5000));
      
      // Verificar de nuevo
      const tokenAfterWait = localStorage.getItem("accessToken");
      const emailAfterWait = localStorage.getItem("email") || (tokenAfterWait && decodeJwt(tokenAfterWait)?.email);
      
      // Si después de esperar sigue expirado o no existe, redirigir
      if (!tokenAfterWait || !emailAfterWait || isTokenExpired()) {
        if (isStripeSuccess || isOnboardingPage) {
          console.log("⚠️ [AUTH] Token no encontrado, pero se permite acceso temporal por verificación de pago activa o estancia en onboarding");
          return true;
        }
        console.log('❌ [AUTH] Token aún inválido después de esperar, redirigiendo a login...');
        logout();
        return false;
      }
      
      console.log('✅ [AUTH] Token válido después de esperar, continuando...');
      return true;
    }
  } else {
    // Comportamiento normal: verificar autenticación básica
    // 🟢 EXCEPCIÓN: Si estamos en onboarding.html, ya permitimos arriba, no llegamos aquí
    if (!token) {
      console.log('❌ [AUTH] DECISIÓN: No hay token - Redirigiendo a login (razón: token no existe)');
      if (!isStripeSuccess && !isOnboardingPage) {
        logout();
        return false;
      }
      console.log("⚠️ [AUTH] Token no encontrado, pero se permite acceso temporal por verificación de pago activa o estancia en onboarding");
      return true;
    }
    
    if (!email) {
      console.log('❌ [AUTH] DECISIÓN: No hay email - Redirigiendo a login (razón: email no existe)');
      // 🟢 PERMISIVO: Si estamos en onboarding, NO redirigir aunque falte email
      if (!isStripeSuccess && !isOnboardingPage) {
        logout();
        return false;
      }
      console.log("⚠️ [AUTH] Email no encontrado, pero se permite acceso temporal por verificación de pago activa o estancia en onboarding");
      return true;
    }
    
    if (tokenExpired) {
      console.log('❌ [AUTH] DECISIÓN: Token expirado - Redirigiendo a login (razón: token realmente expirado)');
      // 🟢 PERMISIVO: Si estamos en onboarding, NO redirigir aunque el token parezca expirado
      if (!isStripeSuccess && !isOnboardingPage) {
        logout();
        return false;
      }
      console.log("⚠️ [AUTH] Token expirado, pero se permite acceso temporal por verificación de pago activa o estancia en onboarding");
      return true;
    }
  }
  
  // ============================================
  // PASO 2: VERIFICAR INTEGRIDAD DE DATOS (Onboarding)
  // ============================================
  console.log('🔍 [AUTH] PASO 2: Verificando integridad de datos (onboarding)...');
  console.log('🔍 [AUTH] Estado onboarding:', {
    onboardingCompleted: onboardingCompleted,
    isTrue: onboardingCompleted === "true"
  });
  
  // ============================================
  // PASO 3: VERIFICACIÓN OPCIONAL AL SERVIDOR (Solo para validar token)
  // ============================================
  // Hacer una verificación ligera al servidor para validar el token
  // Solo hacer logout si es error 401 (Unauthorized)
  // Si es 500 o 422, solo mostrar error pero NO redirigir
  try {
    console.log('🔍 [AUTH] PASO 3: Verificando token con servidor (opcional)...');
    const verifyResponse = await fetch('/api/user/me', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    if (verifyResponse.status === 401) {
      // Solo 401 (Unauthorized) = token realmente inválido
      // 🟢 PERMISIVO: Si estamos en onboarding, NO redirigir ni siquiera con 401
      console.error('❌ [AUTH] DECISIÓN: Error 401 (Unauthorized) - Token inválido');
      console.error('❌ [AUTH] El servidor confirmó que el token no es válido');
      if (!isStripeSuccess && !isOnboardingPage) {
        console.error('❌ [AUTH] Redirigiendo a login (no estamos en onboarding)');
        logout();
        return false;
      }
      console.log("⚠️ [AUTH] Error 401, pero se permite acceso temporal por verificación de pago activa o estancia en onboarding");
      if (isOnboardingPage) {
        console.log("🟢 [AUTH] Permitiendo estancia en onboarding a pesar de error 401");
      }
      return true;
    } else if (!verifyResponse.ok) {
      // Error 500, 422, u otro error del servidor
      const errorData = await verifyResponse.json().catch(() => ({}));
      console.error('⚠️ [AUTH] Error del servidor al verificar token:', {
        status: verifyResponse.status,
        statusText: verifyResponse.statusText,
        error: errorData
      });
      console.error('⚠️ [AUTH] DECISIÓN: Error del servidor (NO 401) - NO redirigir, permitir acceso');
      console.error('⚠️ [AUTH] El usuario puede quedarse en el dashboard mientras el backend se estabiliza');
      // NO hacer logout, solo mostrar error y continuar
      return true;
    } else {
      // Token válido según el servidor
      console.log('✅ [AUTH] Token verificado con servidor - Válido');
    }
  } catch (error) {
    // Error de red o conexión - NO hacer logout, solo mostrar error
    console.error('⚠️ [AUTH] Error de conexión al verificar token:', error);
    console.error('⚠️ [AUTH] DECISIÓN: Error de conexión - NO redirigir, permitir acceso');
    console.error('⚠️ [AUTH] El usuario puede quedarse en el dashboard mientras se restablece la conexión');
    // NO hacer logout, solo mostrar error y continuar
  }
  
  // ✅ Si el token es válido Y el onboarding está completado, NO redirigir bajo ninguna circunstancia
  // (excepto si el token realmente expira)
  if (onboardingCompleted === "true") {
    console.log('✅ [AUTH] DECISIÓN: Token válido + Onboarding completado - PERMITIR ACCESO (no redirigir)');
    console.log('✅ [AUTH] Autenticación exitosa - Usuario autenticado con onboarding completado');
    return true;
  }
  
  // Si el token es válido pero el onboarding no está completado, también permitir acceso
  // (el usuario puede estar en proceso de completar onboarding)
  console.log('✅ [AUTH] DECISIÓN: Token válido - PERMITIR ACCESO (onboarding pendiente pero token válido)');
  console.log('✅ [AUTH] Autenticación exitosa - Token válido, onboarding pendiente');
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