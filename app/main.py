from fastapi import FastAPI
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directorio absoluto de frontend (robusto para Railway)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Routers para API
app.include_router(auth.router)
app.include_router(plan.router)
app.include_router(stripe_routes.router)
app.include_router(stripe_webhook.router)
app.include_router(analisis_cuerpo.router)
app.include_router(user_status.router)
app.include_router(chat.router)
app.include_router(onboarding.router)

@app.get("/")
def root():
    return {
        "message": "GYM AI API",
        "openai_available": bool(os.getenv("OPENAI_API_KEY")),
    }

# Servir archivos HTML específicos
@app.get("/dashboard.html")
async def serve_dashboard():
    return FileResponse(os.path.join(FRONTEND_DIR, "dashboard.html"))

@app.get("/login.html")
async def serve_login():
    return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))

@app.get("/rutina.html")
async def serve_rutina():
    return FileResponse(os.path.join(FRONTEND_DIR, "rutina.html"))

@app.get("/onboarding.html")
async def serve_onboarding_html():
    return FileResponse(os.path.join(FRONTEND_DIR, "onboarding.html"))

@app.get("/tarifas.html")
async def serve_tarifas():
    return FileResponse(os.path.join(FRONTEND_DIR, "tarifas.html"))

@app.get("/pago.html")
async def serve_pago():
    return FileResponse(os.path.join(FRONTEND_DIR, "pago.html"))

# Montar archivos estáticos para CSS, JS, imágenes
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

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