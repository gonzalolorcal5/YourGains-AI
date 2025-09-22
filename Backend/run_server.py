#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Agregar el directorio actual al path de Python
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

import uvicorn

if __name__ == "__main__":
    print("🚀 Iniciando servidor YourGains AI...")
    print(f"📁 Directorio de trabajo: {current_dir}")
    print("🌐 Servidor disponible en: http://127.0.0.1:8000")
    print("📚 Documentación API: http://127.0.0.1:8000/docs")
    print("=" * 50)
    
    uvicorn.run(
        "app.main:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True,
        log_level="info"
    )

