#!/usr/bin/env python3
"""
Script para verificar que las variables de entorno estén correctamente configuradas en Railway.

Uso:
    python scripts/verify_railway_env.py

Este script verifica:
1. Que DATABASE_URL apunte a PostgreSQL (no SQLite)
2. Que todas las variables requeridas estén presentes
3. Que los formatos sean correctos
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

# Añadir el directorio raíz al path para imports
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from dotenv import load_dotenv

# Cargar .env si existe (para desarrollo local)
env_path = root_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.RESET}")

def print_header(msg):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{msg}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def verify_database_url():
    """Verifica que DATABASE_URL esté correctamente configurado para PostgreSQL"""
    print_header("VERIFICACIÓN DE DATABASE_URL")
    
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print_error("DATABASE_URL no está definida")
        print_info("En Railway, debe ser: ${{Postgres.DATABASE_URL}}")
        return False
    
    print_info(f"DATABASE_URL encontrada: {database_url[:50]}...")
    
    # Verificar si es la referencia de Railway
    if database_url.startswith("${{Postgres.DATABASE_URL}}"):
        print_success("DATABASE_URL usa la referencia de Railway: ${{Postgres.DATABASE_URL}}")
        print_warning("⚠️  NOTA: Esta referencia se resuelve automáticamente en Railway")
        print_warning("⚠️  En desarrollo local, necesitas una URL real de PostgreSQL")
        return True
    
    # Verificar si es una URL de PostgreSQL
    if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
        print_success("DATABASE_URL apunta a PostgreSQL")
        
        # Parsear la URL para mostrar información
        try:
            parsed = urlparse(database_url)
            print_info(f"  Host: {parsed.hostname}")
            print_info(f"  Puerto: {parsed.port or 5432}")
            print_info(f"  Base de datos: {parsed.path.lstrip('/')}")
            print_info(f"  Usuario: {parsed.username}")
            
            # Verificar que no sea SQLite
            if "sqlite" in database_url.lower():
                print_error("DATABASE_URL contiene 'sqlite' - debe ser PostgreSQL en producción")
                return False
            
            return True
        except Exception as e:
            print_warning(f"No se pudo parsear la URL: {e}")
            return True  # Asumimos que está bien si empieza con postgresql://
    
    # Verificar si es SQLite (no permitido en producción)
    if database_url.startswith("sqlite://"):
        print_error("DATABASE_URL apunta a SQLite - NO permitido en Railway/Producción")
        print_info("En Railway, debe usar: ${{Postgres.DATABASE_URL}}")
        return False
    
    print_warning(f"Formato de DATABASE_URL desconocido: {database_url[:50]}")
    print_info("En Railway, debe ser: ${{Postgres.DATABASE_URL}}")
    return False

def verify_stripe_config():
    """Verifica la configuración de Stripe"""
    print_header("VERIFICACIÓN DE STRIPE")
    
    required_vars = {
        "STRIPE_SECRET_KEY": {
            "prefixes": ["sk_live_", "sk_test_"],
            "description": "Clave secreta de Stripe (sk_live_... o sk_test_...)"
        },
        "STRIPE_PUBLISHABLE_KEY": {
            "prefixes": ["pk_live_", "pk_test_"],
            "description": "Clave pública de Stripe (pk_live_... o pk_test_...)"
        },
        "STRIPE_PRICE_MENSUAL": {
            "prefixes": ["price_"],
            "description": "ID del precio mensual (price_xxxxx)"
        },
        "STRIPE_PRICE_ANUAL": {
            "prefixes": ["price_"],
            "description": "ID del precio anual (price_xxxxx)"
        },
        "STRIPE_WEBHOOK_SECRET": {
            "prefixes": ["whsec_"],
            "description": "Secreto del webhook de Stripe (whsec_xxxxx)"
        }
    }
    
    all_valid = True
    
    for var_name, config in required_vars.items():
        value = os.getenv(var_name)
        
        if not value:
            print_error(f"{var_name} no está definida")
            print_info(f"  {config['description']}")
            all_valid = False
            continue
        
        # Verificar formato
        valid_format = any(value.startswith(prefix) for prefix in config["prefixes"])
        
        if valid_format:
            print_success(f"{var_name}: {value[:20]}...")
        else:
            print_warning(f"{var_name} tiene formato inesperado")
            print_info(f"  Esperado: {', '.join(config['prefixes'])}")
            print_info(f"  Actual: {value[:30]}...")
            all_valid = False
    
    return all_valid

def verify_jwt_config():
    """Verifica la configuración de JWT"""
    print_header("VERIFICACIÓN DE JWT")
    
    secret_key = os.getenv("SECRET_KEY")
    
    if not secret_key:
        print_error("SECRET_KEY no está definida")
        print_info("Debe ser una clave secreta de mínimo 32 caracteres")
        return False
    
    if len(secret_key) < 32:
        print_warning(f"SECRET_KEY es muy corta ({len(secret_key)} caracteres)")
        print_info("Recomendado: mínimo 32 caracteres para seguridad")
        return False
    
    print_success(f"SECRET_KEY configurada ({len(secret_key)} caracteres)")
    
    # Verificar otras variables opcionales
    algorithm = os.getenv("ALGORITHM", "HS256")
    expire_minutes = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080")
    
    print_info(f"ALGORITHM: {algorithm}")
    print_info(f"ACCESS_TOKEN_EXPIRE_MINUTES: {expire_minutes}")
    
    return True

def verify_openai_config():
    """Verifica la configuración de OpenAI"""
    print_header("VERIFICACIÓN DE OPENAI")
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print_warning("OPENAI_API_KEY no está definida")
        print_info("Necesaria para generación de planes y chat")
        return False
    
    if not api_key.startswith("sk-"):
        print_warning("OPENAI_API_KEY no tiene el formato esperado (debe empezar con 'sk-')")
        return False
    
    print_success(f"OPENAI_API_KEY configurada: {api_key[:10]}...")
    
    # Verificar modelo
    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    environment = os.getenv("ENVIRONMENT", "development")
    
    print_info(f"OPENAI_MODEL: {model}")
    print_info(f"ENVIRONMENT: {environment}")
    
    return True

def verify_optional_vars():
    """Verifica variables opcionales pero recomendadas"""
    print_header("VARIABLES OPCIONALES")
    
    optional_vars = {
        "FRONTEND_URL": "URL del frontend (para redirects de Stripe)",
        "SUPABASE_URL": "URL de Supabase (si se usa)",
        "SUPABASE_SERVICE_ROLE_KEY": "Clave de servicio de Supabase (si se usa)"
    }
    
    for var_name, description in optional_vars.items():
        value = os.getenv(var_name)
        if value:
            print_success(f"{var_name}: configurada")
        else:
            print_info(f"{var_name}: no configurada ({description})")

def main():
    """Función principal"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("="*60)
    print("  VERIFICACIÓN DE VARIABLES DE ENTORNO - RAILWAY")
    print("="*60)
    print(f"{Colors.RESET}\n")
    
    results = {
        "DATABASE_URL": verify_database_url(),
        "Stripe": verify_stripe_config(),
        "JWT": verify_jwt_config(),
        "OpenAI": verify_openai_config()
    }
    
    verify_optional_vars()
    
    # Resumen final
    print_header("RESUMEN")
    
    all_passed = all(results.values())
    
    for component, passed in results.items():
        if passed:
            print_success(f"{component}: ✅ Configurado correctamente")
        else:
            print_error(f"{component}: ❌ Requiere atención")
    
    print("\n" + "="*60)
    
    if all_passed:
        print_success("\n🎉 ¡Todas las verificaciones pasaron!")
        print_info("\nPara verificar en Railway:")
        print_info("1. Ve a tu proyecto en Railway")
        print_info("2. Settings → Variables")
        print_info("3. Verifica que DATABASE_URL = ${{Postgres.DATABASE_URL}}")
        print_info("4. Verifica que todas las demás variables estén configuradas")
        return 0
    else:
        print_error("\n⚠️  Algunas verificaciones fallaron")
        print_info("\nPasos para corregir:")
        print_info("1. Ve a Railway → Tu Proyecto → Settings → Variables")
        print_info("2. Añade o corrige las variables que fallaron")
        print_info("3. Para DATABASE_URL, usa: ${{Postgres.DATABASE_URL}}")
        print_info("4. Reinicia el servicio después de cambiar variables")
        return 1

if __name__ == "__main__":
    sys.exit(main())
