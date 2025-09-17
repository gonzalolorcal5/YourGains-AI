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
  const data = await res.json(); // { access_token, token_type }
  if (!data.access_token) throw new Error("Sin access_token");
  saveAuth(data.access_token, email);
  return data;
}

export function getAuthHeaders() {
  const token = localStorage.getItem("accessToken");
  const email = localStorage.getItem("email");
  return {
    "Content-Type": "application/json",
    "Authorization": token ? `Bearer ${token}` : "",
    "X-User-Email": email || "",
  };
}

export function checkAuthOrRedirect() {
  const token = localStorage.getItem("accessToken");
  const email = localStorage.getItem("email");
  if (!token || !email) {
    window.location.href = "./login.html";
    return false;
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
  const loginTs = parseInt(localStorage.getItem("loginTimestamp") || "0");
  
  if (!token) { return true; }
  
  try {
    const decoded = JSON.parse(atob(token.split('.')[1]));
    if (decoded && typeof decoded.exp === "number") {
      return Date.now() >= decoded.exp * 1000;
    }
  } catch (e) {
    console.warn("Error decodificando JWT:", e);
  }
  
  const fiveMinutes = 5 * 60 * 1000;
  if (!loginTs) return true;
  return (Date.now() - loginTs) > fiveMinutes;
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
}