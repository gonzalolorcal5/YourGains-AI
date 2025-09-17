from fastapi import FastAPI
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse

from app.routes import (
    auth,
    plan,
    stripe_routes,
    stripe_webhook,
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

# Routers API
app.include_router(auth.router)
app.include_router(plan.router)
app.include_router(stripe_routes.router)
app.include_router(stripe_webhook.router)
app.include_router(analisis_cuerpo.router)
app.include_router(user_status.router)
app.include_router(chat.router)
app.include_router(onboarding.router)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # .../app
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")       # .../app/frontend

# --- Test / diagnóstico ---
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

# --- Redirección raíz
@app.get("/")
def root_redirect():
    return RedirectResponse(url="/login.html")

# --- Servir HTMLs (sin conflictos)
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

# --- Assets (css/js/img)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# --- OpenAPI custom
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
