// auth.js - Sistema de autenticación unificado con FastAPI
const isLocal = location.hostname === "127.0.0.1" || location.hostname === "localhost" || location.protocol === "file:";
const API_BASE = isLocal ? "http://127.0.0.1:8000" : "https://yourgains-ai-production.up.railway.app";

const msg = document.getElementById("msg");
const loginBtn = document.getElementById("login");
const registerBtn = document.getElementById("register");

// Validación de email mejorada
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email) && email.length <= 254;
}

// Validación de contraseña segura
function isValidPassword(password) {
    return password.length >= 8 && 
           /[A-Z]/.test(password) && 
           /[a-z]/.test(password) && 
           /[0-9]/.test(password);
}

// Manejo seguro de tokens
async function handleAuthSuccess(token, email) {
    if (!token || !email) {
        throw new Error("Token o email inválidos");
    }
    
    // Almacenamiento seguro
    localStorage.setItem("accessToken", token);
    localStorage.setItem("email", email);
    localStorage.setItem("loginTimestamp", Date.now().toString());
    
    // Siembra/actualiza estado del usuario (FREE/PREMIUM, cupos) sin bloquear la UX
    try {
        fetch(`${API_BASE}/user/status?email=${encodeURIComponent(email)}`)
            .catch(() => {});
    } catch {}

    // Redirección después del login exitoso
    window.location.href = "./dashboard.html";
}

// Decodifica JWT (sin validar) para leer el 'exp'.
function decodeJwt(token) {
    try {
        const [, payload] = token.split(".");
        const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
        return JSON.parse(json);
    } catch {
        return null;
    }
}

// Verificar si el token ha expirado usando 'exp' del JWT; fallback a 5 minutos desde login
function isTokenExpired() {
    const token = localStorage.getItem("accessToken");
    const loginTs = parseInt(localStorage.getItem("loginTimestamp") || "0");
    if (!token) return true;

    const decoded = decodeJwt(token);
    if (decoded && typeof decoded.exp === "number") {
        // exp en segundos → ms
        return Date.now() >= decoded.exp * 1000;
    }

    // Fallback: 5 minutos (consistente con backend ACCESS_TOKEN_EXPIRE_MINUTES)
    const fiveMinutes = 5 * 60 * 1000;
    if (!loginTs) return true;
    return (Date.now() - loginTs) > fiveMinutes;
}

// Limpiar datos de autenticación
function clearAuthData() {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("email");
    localStorage.removeItem("loginTimestamp");
}

// Login con validación robusta
if (loginBtn) {
    loginBtn.onclick = async () => {
        const email = document.getElementById("email").value.trim().toLowerCase();
        const password = document.getElementById("password").value;
        
        // Validaciones frontend
        if (!isValidEmail(email)) {
            if (msg) msg.textContent = "Email inválido";
            return;
        }
        
        if (password.length < 6) {
            if (msg) msg.textContent = "La contraseña debe tener al menos 6 caracteres";
            return;
        }
        
        // Deshabilitar botón durante la petición
        loginBtn.disabled = true;
        loginBtn.textContent = "Iniciando sesión...";
        
        try {
            const response = await fetch(`${API_BASE}/login`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ email, password })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || "Error en el login");
            }
            
            if (data.access_token) {
                // Verificar si el usuario tiene planes para decidir a dónde redirigir
                const token = data.access_token;
                localStorage.setItem("accessToken", token);
                localStorage.setItem("email", email);
                localStorage.setItem("loginTimestamp", Date.now().toString());
                
                // Verificar planes para decidir redirección
                fetch(`${API_BASE}/planes`, {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'X-User-Email': email
                    }
                })
                .then(res => res.json())
                .then(plans => {
                    if (plans.length === 0) {
                        // Usuario nuevo sin planes → Onboarding
                        window.location.href = "./onboarding.html";
                    } else {
                        // Usuario con planes → Dashboard
                        window.location.href = "./dashboard.html";
                    }
                })
                .catch(() => {
                    // En caso de error, ir al dashboard
                    window.location.href = "./dashboard.html";
                });
            } else {
                throw new Error("No se recibió token de acceso");
            }
            
        } catch (error) {
            console.error("Error en login:", error);
            if (msg) msg.textContent = error.message;
        } finally {
            loginBtn.disabled = false;
            loginBtn.textContent = "Iniciar sesión";
        }
    };
}

// Registro con validación robusta
if (registerBtn) {
    registerBtn.onclick = async () => {
        const email = document.getElementById("email").value.trim().toLowerCase();
        const password = document.getElementById("password").value;
        
        // Validaciones frontend
        if (!isValidEmail(email)) {
            if (msg) msg.textContent = "Email inválido";
            return;
        }
        
        if (!isValidPassword(password)) {
            if (msg) msg.textContent = "La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula y un número";
            return;
        }
        
        // Deshabilitar botón durante la petición
        registerBtn.disabled = true;
        registerBtn.textContent = "Registrando...";
        
        try {
            const response = await fetch(`${API_BASE}/register`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ email, password })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || "Error en el registro");
            }
            
            if (msg) {
                msg.textContent = "Registro exitoso. Redirigiendo al formulario...";
                msg.style.color = "#84cc16"; // Verde
            }
            
            // Auto-login después del registro y redirigir al onboarding
            setTimeout(async () => {
                try {
                    const loginResponse = await fetch(`${API_BASE}/login`, {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({ email, password })
                    });
                    
                    const loginData = await loginResponse.json();
                    
                    if (loginResponse.ok && loginData.access_token) {
                        // Guardar datos de sesión
                        localStorage.setItem("accessToken", loginData.access_token);
                        localStorage.setItem("email", email);
                        localStorage.setItem("loginTimestamp", Date.now().toString());
                        
                        // Redirigir directamente al onboarding
                        window.location.href = "./onboarding.html";
                    }
                } catch (error) {
                    console.error("Error en auto-login:", error);
                    if (msg) {
                        msg.textContent = "Registro exitoso. Ahora puedes iniciar sesión.";
                    }
                }
            }, 2000);
            
        } catch (error) {
            console.error("Error en registro:", error);
            if (msg) {
                msg.textContent = error.message;
                msg.style.color = "#ef4444"; // Rojo
            }
        } finally {
            registerBtn.disabled = false;
            registerBtn.textContent = "Registrarse";
        }
    };
}

// Verificar autenticación al cargar la página
window.addEventListener('load', () => {
    const token = localStorage.getItem("accessToken");
    const email = localStorage.getItem("email");
    
    // Si estamos en páginas que requieren auth y no hay token válido
    const requiresAuth = ['dashboard.html', 'rutina.html', 'tarifas.html'].some(page => 
        location.pathname.includes(page)
    );
    
    if (requiresAuth) {
        if (!token || !email || isTokenExpired()) {
            clearAuthData();
            window.location.href = "./login.html";
            return;
        }
    }
    
    // Si estamos en login y ya hay sesión válida, mostrar mensaje pero no redirigir automáticamente
    if (location.pathname.includes('login.html') && token && !isTokenExpired()) {
        // Mostrar mensaje de que ya hay una sesión activa
        const msg = document.getElementById('msg');
        const logoutSection = document.getElementById('logoutSection');
        if (msg) {
            msg.textContent = 'Ya tienes una sesión activa. Haz clic en "Iniciar sesión" para continuar.';
            msg.style.color = '#84cc16'; // Verde
        }
        if (logoutSection) {
            logoutSection.style.display = 'block';
        }
    }
});

// Función global para logout
window.logout = function() {
    clearAuthData();
    window.location.href = "./login.html";
};

// Event listener para el botón de logout en login
document.addEventListener('DOMContentLoaded', function() {
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function() {
            clearAuthData();
            location.reload(); // Recargar la página para limpiar el estado
        });
    }
});

// Función global para obtener headers de autenticación
window.getAuthHeaders = function() {
    const token = localStorage.getItem("accessToken");
    const email = localStorage.getItem("email");
    
    if (!token || isTokenExpired()) {
        clearAuthData();
        window.location.href = "./login.html";
        return null;
    }
    
    return {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
        "X-User-Email": email
    };
};