#!/usr/bin/env python3
"""
Script simple para iniciar YourGains AI
"""
import os
import sys
from pathlib import Path

# Cambiar al directorio Backend
backend_dir = Path(__file__).parent / "Backend"
os.chdir(backend_dir)

# Agregar al path
sys.path.insert(0, str(backend_dir))

print("🚀 Iniciando YourGains AI...")
print(f"📁 Directorio: {backend_dir}")
print("🌐 Servidor: http://127.0.0.1:8000")
print("=" * 50)

# Importar y ejecutar
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)

