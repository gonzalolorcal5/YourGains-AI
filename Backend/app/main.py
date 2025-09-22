from fastapi import FastAPI
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse

# Routers "seguros" (no fallan al importar)
from app.routes import (
    auth,
    plan,
    analisis_cuerpo,
    user_status,
    chat,
    onboarding,
)

load_dotenv()
app = FastAPI()

# CORS abierto mientras probamos
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------- incluir routers ---------
app.include_router(auth.router)
app.include_router(plan.router)
app.include_router(analisis_cuerpo.router)
app.include_router(user_status.router)
app.include_router(chat.router)
app.include_router(onboarding.router)

# Stripe (protegido por si faltan variables)
try:
    from app.routes import stripe_routes, stripe_webhook
    app.include_router(stripe_routes.router)
    app.include_router(stripe_webhook.router)
    print("[INFO] Stripe routes enabled")
except Exception as e:
    print("[WARN] Stripe routes disabled:", e)

# --------- paths de frontend ---------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # .../app
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")       # .../app/frontend

# --------- health & debug ---------
@app.get("/ping")
@app.get("/_ping")
@app.get("/__ping")
def __ping():
    return {"ok": True}

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

# --------- servir HTMLs (sin conflictos) ---------
@app.get("/")
def root_redirect():
    return RedirectResponse(url="/login.html")

def _html(name: str):
    return FileResponse(os.path.join(FRONTEND_DIR, name))

@app.get("/login.html")
def _login(): return _html("login.html")

@app.get("/dashboard.html")
def _dashboard(): return _html("dashboard.html")

@app.get("/rutina.html")
def _rutina(): return _html("rutina.html")

@app.get("/onboarding.html")
def _onboarding(): return _html("onboarding.html")

@app.get("/tarifas.html")
def _tarifas(): return _html("tarifas.html")

@app.get("/pago.html")
def _pago(): return _html("pago.html")

# Servir archivos JS específicos
@app.get("/auth.js")
def _auth_js(): return FileResponse(os.path.join(FRONTEND_DIR, "auth.js"), media_type="application/javascript")

@app.get("/config.js")
def _config_js(): return FileResponse(os.path.join(FRONTEND_DIR, "config.js"), media_type="application/javascript")

@app.get("/onboarding.js")
def _onboarding_js(): return FileResponse(os.path.join(FRONTEND_DIR, "onboarding.js"), media_type="application/javascript")

# estáticos (css/js/img) si los tienes en la misma carpeta
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# Montar carpeta de imágenes específicamente
IMAGES_DIR = os.path.join(FRONTEND_DIR, "images")
if os.path.exists(IMAGES_DIR):
    app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")

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
    except Exception as e:
        print("[ROUTES-ERROR]", e)
