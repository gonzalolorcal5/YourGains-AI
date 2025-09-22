#!/usr/bin/env python3
"""
Script para iniciar YourGains AI desde cualquier ubicación
"""
import sys
import os
from pathlib import Path

if __name__ == "__main__":
    # Obtener el directorio del script
    script_dir = Path(__file__).parent
    backend_dir = script_dir / "Backend"

    # Cambiar al directorio Backend
    os.chdir(backend_dir)

    # Agregar el directorio Backend al path de Python
    sys.path.insert(0, str(backend_dir))

    print("🚀 Iniciando YourGains AI...")
    print(f"📁 Directorio: {backend_dir}")
    print("🌐 Servidor: http://127.0.0.1:8000")
    print("📚 API Docs: http://127.0.0.1:8000/docs")
    print("=" * 50)

    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False, log_level="info")
