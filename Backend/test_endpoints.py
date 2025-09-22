#!/usr/bin/env python3
"""
Script para probar endpoints de Railway
"""
import requests
import json

API_BASE = "https://yourgains-ai-production-d7dd.up.railway.app"

def test_endpoint(url, method="GET", data=None, headers=None):
    """Prueba un endpoint y muestra el resultado"""
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers)
        
        print(f"✅ {method} {url}")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                json_data = response.json()
                print(f"   Response: {json.dumps(json_data, indent=2)[:200]}...")
            except:
                print(f"   Response: {response.text[:200]}...")
        else:
            print(f"   Error: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ {method} {url}")
        print(f"   Error: {e}")
    
    print()

def main():
    print("🧪 Probando endpoints de Railway...")
    print("=" * 50)
    
    # Endpoints básicos
    test_endpoint(f"{API_BASE}/")
    test_endpoint(f"{API_BASE}/__ping")
    test_endpoint(f"{API_BASE}/docs")
    
    # Endpoints HTML
    test_endpoint(f"{API_BASE}/login.html")
    test_endpoint(f"{API_BASE}/dashboard.html")
    test_endpoint(f"{API_BASE}/rutina.html")
    test_endpoint(f"{API_BASE}/onboarding.html")
    test_endpoint(f"{API_BASE}/tarifas.html")
    test_endpoint(f"{API_BASE}/pago.html")
    
    # Endpoints de API (sin autenticación)
    test_endpoint(f"{API_BASE}/register", "POST", {
        "email": "test@example.com",
        "password": "testpassword123"
    })
    
    test_endpoint(f"{API_BASE}/login", "POST", {
        "email": "test@example.com", 
        "password": "testpassword123"
    })
    
    print("✅ Pruebas completadas")

if __name__ == "__main__":
    main()
