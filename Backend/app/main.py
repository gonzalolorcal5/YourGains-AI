from fastapi import FastAPI, HTTPException, Request
from dotenv import load_dotenv
import os
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Routers "seguros" (no fallan al importar)
from app.routes import (
    auth,
    oauth,
    plan,
    analisis_cuerpo,
    user_status,
    user,
    chat,
    onboarding,
    bodyscan,
    articles,
    tracking,
    # Importamos Stripe directamente aqui para que si falla, explote y veamos el error
    stripe_routes,
    stripe_webhook,
)

# Intento importar el CLI si existe, si no, no pasa nada
try:
    from app.routes import stripe_webhook_cli
    HAS_STRIPE_CLI = True
except ImportError:
    HAS_STRIPE_CLI = False
    print("[WARN] stripe_webhook_cli no encontrado, ruta /stripe/webhook-cli deshabilitada")


load_dotenv()
app = FastAPI()

# ═══════════════════════════════════════════════════════
# RATE LIMITING - Prevención de abusos
# ═══════════════════════════════════════════════════════
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Handler personalizado para rate limit exceeded
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "error": "Demasiadas solicitudes. Por favor, espera un momento e inténtalo de nuevo.",
            "retry_after": exc.retry_after if hasattr(exc, 'retry_after') else 60
        }
    )


# ═══════════════════════════════════════════════════════
# CONFIGURACIÓN CORS - SEGURIDAD
# ═══════════════════════════════════════════════════════
# En producción: Solo yourgains.ai puede hacer requests
# En desarrollo: Permite localhost para testing
# Variables de entorno:
# - FRONTEND_URL: URL principal del frontend
# - ALLOWED_ORIGINS: Lista separada por comas (opcional)
# ═══════════════════════════════════════════════════════

# Configuración de CORS según entorno
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:8000")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else [FRONTEND_URL]

# Si estamos en desarrollo local, permitir localhost
if "localhost" in FRONTEND_URL or "127.0.0.1" in FRONTEND_URL:
    ALLOWED_ORIGINS.extend([
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5173",  # Vite dev server si se usa
    ])

# Filtrar strings vacíos de la lista
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS if origin.strip()]

# Log de orígenes permitidos (para debugging)
print(f"[CORS] Orígenes permitidos: {ALLOWED_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # ✅ Lista específica de dominios
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Middleware para NO-CACHE en archivos /public/
from starlette.middleware.base import BaseHTTPMiddleware

class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/public/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

app.add_middleware(NoCacheMiddleware)

# --------- incluir routers ---------
app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(plan.router)
app.include_router(analisis_cuerpo.router)
app.include_router(user_status.router)
app.include_router(user.router)
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(bodyscan.router, prefix="/api", tags=["BodyScan"])
app.include_router(articles.router, prefix="/api", tags=["Articles"])
app.include_router(tracking.router)
app.include_router(onboarding.router)

# --------- STRIPE ROUTERS (Sin try-except gigante) ---------
# Estos son CRITICOS para que tarifas.html funcione.
app.include_router(stripe_routes.router)
app.include_router(stripe_webhook.router)

if HAS_STRIPE_CLI:
     app.include_router(stripe_webhook_cli.router, prefix="/stripe", tags=["stripe-cli"])

print("[INFO] Stripe routes enabled")


# --------- paths de frontend (absolutos para que funcionen en local/Windows) ---------
# main.py está en Backend/app/main.py → _base = Backend/app
_base = Path(__file__).resolve().parent
BASE_DIR = _base
# HTMLs están en Backend/app/frontend/ → usar _base / "frontend"
_candidate = _base / "frontend"
if (_candidate / "login.html").exists():
    FRONTEND_DIR = _candidate
else:
    _fallback = _base.parent / "frontend"
    FRONTEND_DIR = _fallback if (_fallback / "login.html").exists() else _candidate
STATIC_DIR = _base.parent / "static"
PUBLIC_DIR = STATIC_DIR / "public"

# --------- MOUNTS PRIMERO: estáticos antes que cualquier catch-all ---------
# Así /public/*, /static/* y /images/* nunca caen en "redirect a login"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
IMAGES_DIR = FRONTEND_DIR / "images"
if IMAGES_DIR.exists():
    app.mount("/images", StaticFiles(directory=str(IMAGES_DIR)), name="images")
if PUBLIC_DIR.exists():
    app.mount("/public", StaticFiles(directory=str(PUBLIC_DIR)), name="public")

# --------- health & debug ---------
@app.get("/ping")
@app.get("/_ping")
@app.get("/__ping")
def __ping():
    return {"ok": True}

@app.get("/health/env")
def health_check_env():
    """
    Verifica que las variables de entorno estén correctamente configuradas.
    NO expone valores sensibles, solo indica si están presentes y tienen el formato correcto.
    """
    from urllib.parse import urlparse
    
    checks = {
        "database": {
            "configured": False,
            "is_postgres": False,
            "is_railway_ref": False,
            "message": ""
        },
        "stripe": {
            "secret_key": False,
            "publishable_key": False,
            "price_mensual": False,
            "price_anual": False,
            "webhook_secret": False
        },
        "jwt": {
            "secret_key": False,
            "secret_key_length": 0
        },
        "openai": {
            "api_key": False
        }
    }
    
    # Verificar DATABASE_URL
    database_url = os.getenv("DATABASE_URL", "")
    if database_url:
        checks["database"]["configured"] = True
        
        # Verificar si es referencia de Railway
        if database_url.startswith("${{Postgres.DATABASE_URL}}"):
            checks["database"]["is_railway_ref"] = True
            checks["database"]["message"] = "Usando referencia de Railway (correcto)"
        # Verificar si es PostgreSQL
        elif database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
            checks["database"]["is_postgres"] = True
            try:
                parsed = urlparse(database_url)
                checks["database"]["message"] = f"PostgreSQL en {parsed.hostname}"
            except:
                checks["database"]["message"] = "PostgreSQL (URL válida)"
        # Verificar si es SQLite (no permitido en producción)
        elif database_url.startswith("sqlite://"):
            checks["database"]["message"] = "SQLite detectado (no recomendado para producción)"
        else:
            checks["database"]["message"] = "Formato desconocido"
    else:
        checks["database"]["message"] = "No configurada"
    
    # Verificar Stripe
    stripe_secret = os.getenv("STRIPE_SECRET_KEY", "")
    if stripe_secret:
        checks["stripe"]["secret_key"] = stripe_secret.startswith("sk_live_") or stripe_secret.startswith("sk_test_")
    
    stripe_publishable = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    if stripe_publishable:
        checks["stripe"]["publishable_key"] = stripe_publishable.startswith("pk_live_") or stripe_publishable.startswith("pk_test_")
    
    checks["stripe"]["price_mensual"] = bool(os.getenv("STRIPE_PRICE_MENSUAL", "").startswith("price_"))
    checks["stripe"]["price_anual"] = bool(os.getenv("STRIPE_PRICE_ANUAL", "").startswith("price_"))
    checks["stripe"]["webhook_secret"] = bool(os.getenv("STRIPE_WEBHOOK_SECRET", "").startswith("whsec_"))
    
    # Verificar JWT
    secret_key = os.getenv("SECRET_KEY", "")
    if secret_key:
        checks["jwt"]["secret_key"] = True
        checks["jwt"]["secret_key_length"] = len(secret_key)
    
    # Verificar OpenAI
    checks["openai"]["api_key"] = bool(os.getenv("OPENAI_API_KEY", "").startswith("sk-"))
    
    # Calcular estado general
    all_ok = (
        checks["database"]["configured"] and 
        (checks["database"]["is_postgres"] or checks["database"]["is_railway_ref"]) and
        all(checks["stripe"].values()) and
        checks["jwt"]["secret_key"] and
        checks["jwt"]["secret_key_length"] >= 32
    )
    
    return {
        "status": "ok" if all_ok else "warning",
        "checks": checks,
        "recommendations": {
            "database_url": "Debe ser ${{Postgres.DATABASE_URL}} en Railway" if not checks["database"]["is_railway_ref"] else None,
            "stripe": "Verifica todas las claves de Stripe" if not all(checks["stripe"].values()) else None,
            "jwt": "SECRET_KEY debe tener mínimo 32 caracteres" if checks["jwt"]["secret_key_length"] < 32 else None
        }
    }

@app.get("/__debug_ls")
def __debug_ls():
    try:
        return {
            "BASE_DIR": BASE_DIR,
            "FRONTEND_DIR": FRONTEND_DIR,
            "frontend_exists": os.path.exists(FRONTEND_DIR),
            "frontend_files": os.listdir(FRONTEND_DIR) if os.path.exists(FRONTEND_DIR) else [],
        }
    except Exception as e:
        return {"error": str(e)}

# --------- servir HTMLs (CON ANTI-CACHE y DEBUG) ---------

def _html(name: str):
    """
    Función helper para servir HTMLs con debug y sin caché
    """
    file_path = os.path.join(FRONTEND_DIR, name)
    
    # --- DEBUG: EL CHIVATO ---
    print(f"--- [REQUEST HTML] ---")
    print(f"📄 Solicitado: {name}")
    print(f"📂 Buscando en: {file_path}")
    print(f"✅ Existe: {os.path.exists(file_path)}")
    print(f"----------------------")

    # Crear respuesta
    response = FileResponse(file_path)
    
    # --- ANTI-CACHE: BOMBA NUCLEAR ---
    # Obliga al navegador a revalidar siempre y no guardar nada
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return response

@app.get("/")
def root():
    """Raíz: landing/index si existen; si no, login.html (nunca 404)."""
    for name in ("landing.html", "index.html"):
        p = os.path.join(FRONTEND_DIR, name)
        if os.path.exists(p):
            return _html(name)
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        response = FileResponse(index_path)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    # Sin landing/index: servir login directamente (evitar 404)
    login_path = os.path.join(FRONTEND_DIR, "login.html")
    if os.path.exists(login_path):
        return _html("login.html")
    return RedirectResponse(url="/login")

@app.get("/login.html")
def _login(): return _html("login.html")

@app.get("/login")
def _login_route(): return _html("login.html")

@app.get("/dashboard")
@app.get("/dashboard.html")
def _dashboard():
    return _html("dashboard.html")

@app.get("/rutina.html")
def _rutina(): return _html("rutina.html")

@app.get("/onboarding.html")
def _onboarding(): return _html("onboarding.html")

@app.get("/tarifas.html")
def _tarifas(): return _html("tarifas.html")

@app.get("/stripe-config")
def _stripe_config():
    """Endpoint para obtener la clave pública de Stripe"""
    import os
    stripe_key = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    
    if not stripe_key:
        print("[ERROR] STRIPE_PUBLISHABLE_KEY no está configurada")
        raise HTTPException(
            status_code=500, 
            detail="Stripe no configurado correctamente"
        )
    
    return {
        "publishableKey": stripe_key
    }

@app.get("/pago.html")
def _pago(): return _html("pago.html")

@app.get("/terms.html")
def _terms(): return _html("terms.html")

@app.get("/privacy.html")
def _privacy(): return _html("privacy.html")

@app.get("/cookies.html")
def _cookies():
    """Servir página de cookies desde static"""
    cookies_path = os.path.join(STATIC_DIR, "cookies.html")
    if os.path.exists(cookies_path):
        response = FileResponse(cookies_path)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    raise HTTPException(status_code=404, detail="Cookies page not found")

# Servir archivos JS (mismo origen que el HTML → sin CORS; anti-cache para dev)
def _serve_js_no_cache(filename):
    path = os.path.join(FRONTEND_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Script not found: {filename}")
    response = FileResponse(path, media_type="application/javascript; charset=utf-8")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response

@app.get("/auth.js")
def _auth_js(): return _serve_js_no_cache("auth.js")

@app.get("/config.js")
def _config_js(): return _serve_js_no_cache("config.js")

@app.get("/onboarding.js")
def _onboarding_js(): return _serve_js_no_cache("onboarding.js")

@app.get("/cookie-consent.js")
def _cookie_consent_js():
    """Servir cookie-consent.js desde static"""
    cookie_js_path = os.path.join(STATIC_DIR, "cookie-consent.js")
    if os.path.exists(cookie_js_path):
        response = FileResponse(cookie_js_path, media_type="application/javascript")
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    raise HTTPException(status_code=404, detail="Cookie consent script not found")

# Servir imágenes de public con anti-caché
def _serve_public_image(filename: str):
    """Servir imágenes de /public con headers anti-caché"""
    image_path = os.path.join(PUBLIC_DIR, filename)
    if os.path.exists(image_path):
        response = FileResponse(image_path)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    raise HTTPException(status_code=404, detail="Image not found")

# Endpoints específicos para imágenes de la landing page
@app.get("/public/logo.png")
def _logo(): return _serve_public_image("logo.png")

@app.get("/public/hero-bg.jpg")
def _hero_bg(): return _serve_public_image("hero-bg.jpg")

@app.get("/public/mobile-hero.png")
def _mobile_hero(): return _serve_public_image("mobile-hero.png")

@app.get("/public/mobile-rutina.png")
def _mobile_rutina(): return _serve_public_image("mobile-rutina.png")

@app.get("/public/mobile-dieta.png")
def _mobile_dieta(): return _serve_public_image("mobile-dieta.png")

# --------- Fallback SPA: ÚLTIMA ruta registrada (catch-all) ---------
# Nunca devolver redirect a login para peticiones de archivos estáticos (.js, .css, imágenes)
STATIC_EXTENSIONS = (".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2", ".webp")

@app.get("/{path:path}")
def _spa_fallback(path: str):
    # Excluir rutas de sistema
    if path.startswith(("__", "_")):
        raise HTTPException(status_code=404, detail="Not Found")
    path_lower = path.lower()
    if path_lower.startswith(("api/", "static/", "public/", "images/")):
        raise HTTPException(status_code=404, detail="Not found")
    if path in ("auth.js", "config.js", "onboarding.js", "cookie-consent.js",
                "ping", "_ping", "__ping", "health", "docs", "openapi.json", "redoc"):
        raise HTTPException(status_code=404, detail="Not found")
    # No enviar HTML de login para peticiones que piden un archivo estático
    if path_lower.endswith(STATIC_EXTENSIONS):
        raise HTTPException(status_code=404, detail="Not found")
    return RedirectResponse(url="/login", status_code=302)

# --------- openapi custom ---------
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Gym AI API",
        version="1.0",
        description="API de entrenamiento y dieta con IA",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# log de rutas al arrancar (aparece en Deploy Logs)
@app.on_event("startup")
async def _print_routes():
    try:
        paths = sorted({getattr(r, "path", "") for r in app.routes})
        print("[ROUTES]", paths)
        login_path = FRONTEND_DIR / "login.html"
        print(f"[STARTUP] FRONTEND_DIR = {FRONTEND_DIR}")
        print(f"[STARTUP] login.html existe: {login_path.exists()}")
    except Exception as e:
        print("[ROUTES-ERROR]", e)