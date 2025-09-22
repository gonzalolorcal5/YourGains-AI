#!/usr/bin/env python3
import uvicorn

if __name__ == "__main__":
    print("Iniciando servidor YourGains AI...")
    uvicorn.run(
        "app.main:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True,
        log_level="info"
    )


