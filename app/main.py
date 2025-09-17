from fastapi import FastAPI
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

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

# ----- Paths útiles para estáticos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))         # .../app
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")             # .../app/frontend

# Routers API
app.include_router(auth.router)
app.include_router(plan.router)
app.include_router(stripe_routes.router)
app.include_router(stripe_webhook.router)
app.include_router(analisis_cuerpo.router)
app.include_router(user_status.router)
app.include_router(chat.router)
app.include_router(onboarding.router)

# --------- ENDPOINTS DE DIAGNÓSTICO ---------
@app.get("/__ping")
def __ping():
    return {"ok": True}

@app.get("/__debug_ls")
def __debug_ls():
    try:
        cwd = os.getcwd()
        exists_front = os.path.exists(FRONTEND_DIR)
        files_front = os.listdir(FRONTEND_DIR) if exists_front else []
        here_files = os.listdir(BASE_DIR)
        return {
            "cwd": cwd,
            "BASE_DIR": BASE_DIR,
            "FRONTEND_DIR": FRONTEND_DIR,
            "frontend_exists": exists_front,
            "frontend_files": files_front,
            "app_dir_listing": here_files,
        }
    except Exception as e:
        return {"error": str(e)}

# --------- SERVIR FRONTEND ---------
# montaje normal en raíz
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
# montaje alternativo para pruebas en /_f
app.mount("/_f", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend_alt")

# Redirige "/" a login.html
@app.get("/")
def root_redirect():
    return RedirectResponse(url="/login.html")

# --------- OPENAPI CUSTOM ---------
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
