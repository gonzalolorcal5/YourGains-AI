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

@app.get("/health")
def health():
    return {
        "message": "GYM AI API",
        "openai_available": bool(os.getenv("OPENAI_API_KEY")),
    }

# --------- SERVIR FRONTEND ---------
# Monta todos los archivos .html directamente
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

# Redirigir "/" a login.html
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
