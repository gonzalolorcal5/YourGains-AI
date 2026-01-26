#!/usr/bin/env python3
"""
Script de auditoría de la base de datos PostgreSQL en Railway.

Analiza:
- Estado de usuarios premium
- Planes generados
- Inconsistencias entre is_premium, plan_type, y planes en BD
- Usuarios premium sin rutina/plan generado

Uso:
    python scripts/audit_database.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Añadir el directorio raíz al path para imports
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from dotenv import load_dotenv

# Cargar .env si existe
env_path = root_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")

def print_info(msg):
    print(f"{Colors.CYAN}ℹ️  {msg}{Colors.RESET}")

def print_header(msg):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{msg}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")

def get_database_connection():
    """Obtiene conexión a la base de datos"""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print_error("DATABASE_URL no está configurada")
        print_info("Asegúrate de tener DATABASE_URL en tu .env o variables de entorno")
        sys.exit(1)
    
    # Verificar que sea PostgreSQL
    if not (database_url.startswith("postgresql://") or database_url.startswith("postgres://")):
        print_error("DATABASE_URL no apunta a PostgreSQL")
        print_info(f"URL actual: {database_url[:50]}...")
        print_info("Este script solo funciona con PostgreSQL")
        sys.exit(1)
    
    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        # Probar conexión
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print_success("Conexión a PostgreSQL establecida")
        return engine
    except Exception as e:
        print_error(f"Error conectando a PostgreSQL: {e}")
        sys.exit(1)

def audit_usuarios(engine):
    """Audita todos los usuarios con su estado de premium"""
    print_header("AUDITORÍA DE USUARIOS")
    
    query = text("""
        SELECT 
            id, 
            email, 
            is_premium, 
            plan_type,
            stripe_customer_id, 
            stripe_subscription_id, 
            onboarding_completed,
            CASE 
                WHEN current_routine = '{}' OR current_routine IS NULL THEN false
                ELSE true
            END as tiene_rutina
        FROM usuarios
        ORDER BY id DESC
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()
    
    if not rows:
        print_warning("No se encontraron usuarios en la base de datos")
        return []
    
    print_info(f"Total de usuarios: {len(rows)}")
    print(f"\n{Colors.BOLD}{'ID':<6} {'Email':<30} {'Premium':<8} {'Plan Type':<15} {'Onboarding':<10} {'Rutina':<8}{Colors.RESET}")
    print("-" * 90)
    
    usuarios_data = []
    for row in rows:
        usuarios_data.append({
            "id": row[0],
            "email": row[1],
            "is_premium": row[2],
            "plan_type": row[3] or "NULL",
            "stripe_customer_id": row[4],
            "stripe_subscription_id": row[5],
            "onboarding_completed": row[6],
            "tiene_rutina": row[7]
        })
        
        premium_status = "✅" if row[2] else "❌"
        onboarding_status = "✅" if row[6] else "❌"
        rutina_status = "✅" if row[7] else "❌"
        
        print(f"{row[0]:<6} {row[1][:28]:<30} {premium_status:<8} {str(row[3] or 'NULL'):<15} {onboarding_status:<10} {rutina_status:<8}")
    
    return usuarios_data

def audit_planes(engine):
    """Audita todos los planes (historial de onboarding)"""
    print_header("AUDITORÍA DE PLANES")
    
    query = text("""
        SELECT 
            id, 
            user_id, 
            fecha_creacion, 
            objetivo_gym, 
            objetivo_nutricional,
            session_duration
        FROM planes
        ORDER BY id DESC
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query)
        rows = result.fetchall()
    
    if not rows:
        print_warning("No se encontraron planes en la base de datos")
        return []
    
    print_info(f"Total de planes: {len(rows)}")
    print(f"\n{Colors.BOLD}{'ID':<6} {'User ID':<8} {'Fecha Creación':<20} {'Objetivo Gym':<20} {'Session':<10}{Colors.RESET}")
    print("-" * 80)
    
    planes_data = []
    for row in rows:
        planes_data.append({
            "id": row[0],
            "user_id": row[1],
            "fecha_creacion": row[2],
            "objetivo_gym": row[3],
            "objetivo_nutricional": row[4],
            "session_duration": row[5]
        })
        
        fecha_str = str(row[2])[:19] if row[2] else "NULL"
        objetivo_gym_str = str(row[3] or "NULL")[:18]
        session_str = str(row[5] or "NULL")[:8]
        
        print(f"{row[0]:<6} {row[1]:<8} {fecha_str:<20} {objetivo_gym_str:<20} {session_str:<10}")
    
    return planes_data

def detectar_inconsistencias(engine, usuarios_data, planes_data):
    """Detecta inconsistencias en los datos"""
    print_header("DETECCIÓN DE INCONSISTENCIAS")
    
    issues = []
    
    # Query para usuarios premium sin plan generado
    query = text("""
        SELECT 
            u.id,
            u.email,
            u.is_premium,
            u.plan_type,
            CASE 
                WHEN u.current_routine = '{}' OR u.current_routine IS NULL THEN 'NO'
                ELSE 'SI'
            END as tiene_rutina,
            CASE
                WHEN EXISTS (SELECT 1 FROM planes WHERE user_id = u.id) THEN 'SI'
                ELSE 'NO'
            END as tiene_plan_tabla,
            u.onboarding_completed
        FROM usuarios u
        WHERE u.is_premium = true
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query)
        premium_users = result.fetchall()
    
    if premium_users:
        print_info(f"Usuarios premium encontrados: {len(premium_users)}")
        print(f"\n{Colors.BOLD}{'ID':<6} {'Email':<30} {'Plan Type':<15} {'Rutina':<8} {'Plan BD':<8} {'Onboarding':<10}{Colors.RESET}")
        print("-" * 90)
        
        for row in premium_users:
            user_id, email, is_premium, plan_type, tiene_rutina, tiene_plan_tabla, onboarding = row
            
            rutina_status = "✅" if tiene_rutina == "SI" else "❌"
            plan_status = "✅" if tiene_plan_tabla == "SI" else "❌"
            onboarding_status = "✅" if onboarding else "❌"
            
            print(f"{user_id:<6} {email[:28]:<30} {str(plan_type or 'NULL'):<15} {rutina_status:<8} {plan_status:<8} {onboarding_status:<10}")
            
            # Detectar problemas
            if tiene_rutina == "NO" and tiene_plan_tabla == "NO":
                issues.append({
                    "tipo": "PREMIUM_SIN_PLAN",
                    "user_id": user_id,
                    "email": email,
                    "descripcion": "Usuario premium sin rutina ni plan en BD"
                })
            
            if tiene_plan_tabla == "SI" and not onboarding:
                issues.append({
                    "tipo": "PLAN_SIN_ONBOARDING",
                    "user_id": user_id,
                    "email": email,
                    "descripcion": "Usuario con plan en BD pero onboarding_completed = false"
                })
            
            if plan_type not in ["PREMIUM_MONTHLY", "PREMIUM_YEARLY", "PREMIUM"] and is_premium:
                issues.append({
                    "tipo": "PLAN_TYPE_INCONSISTENTE",
                    "user_id": user_id,
                    "email": email,
                    "descripcion": f"is_premium=true pero plan_type={plan_type}"
                })
    else:
        print_info("No hay usuarios premium en la base de datos")
    
    # Verificar usuarios con plan pero sin premium
    query2 = text("""
        SELECT DISTINCT u.id, u.email, u.is_premium, u.plan_type
        FROM usuarios u
        WHERE EXISTS (SELECT 1 FROM planes WHERE user_id = u.id)
        AND u.is_premium = false
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query2)
        users_with_plan_not_premium = result.fetchall()
    
    if users_with_plan_not_premium:
        print_warning(f"\n⚠️  Usuarios con plan en BD pero is_premium=false: {len(users_with_plan_not_premium)}")
        for row in users_with_plan_not_premium:
            issues.append({
                "tipo": "PLAN_SIN_PREMIUM",
                "user_id": row[0],
                "email": row[1],
                "descripcion": "Tiene plan en BD pero is_premium=false"
            })
    
    return issues

def generar_reporte(issues, usuarios_data, planes_data):
    """Genera un reporte final con recomendaciones"""
    print_header("REPORTE FINAL")
    
    total_usuarios = len(usuarios_data)
    usuarios_premium = sum(1 for u in usuarios_data if u["is_premium"])
    total_planes = len(planes_data)
    
    print_info(f"Total usuarios: {total_usuarios}")
    print_info(f"Usuarios premium: {usuarios_premium}")
    print_info(f"Total planes: {total_planes}")
    print_info(f"Inconsistencias detectadas: {len(issues)}")
    
    if issues:
        print(f"\n{Colors.RED}{Colors.BOLD}PROBLEMAS DETECTADOS:{Colors.RESET}\n")
        
        for i, issue in enumerate(issues, 1):
            print(f"{Colors.RED}{i}. {issue['tipo']}{Colors.RESET}")
            print(f"   Usuario ID: {issue['user_id']}")
            print(f"   Email: {issue['email']}")
            print(f"   Descripción: {issue['descripcion']}")
            print()
        
        print(f"{Colors.YELLOW}{Colors.BOLD}RECOMENDACIONES:{Colors.RESET}\n")
        
        # Agrupar por tipo de problema
        premium_sin_plan = [i for i in issues if i["tipo"] == "PREMIUM_SIN_PLAN"]
        plan_sin_onboarding = [i for i in issues if i["tipo"] == "PLAN_SIN_ONBOARDING"]
        plan_type_inconsistente = [i for i in issues if i["tipo"] == "PLAN_TYPE_INCONSISTENTE"]
        plan_sin_premium = [i for i in issues if i["tipo"] == "PLAN_SIN_PREMIUM"]
        
        if premium_sin_plan:
            print(f"{Colors.YELLOW}1. Usuarios premium sin plan ({len(premium_sin_plan)}):{Colors.RESET}")
            print("   - Verificar que el webhook de Stripe se ejecutó correctamente")
            print("   - Considerar regenerar el plan manualmente si es necesario")
            print()
        
        if plan_sin_onboarding:
            print(f"{Colors.YELLOW}2. Usuarios con plan pero onboarding_completed=false ({len(plan_sin_onboarding)}):{Colors.RESET}")
            print("   - Esto debería corregirse automáticamente con la nueva lógica")
            print("   - El endpoint /api/user/me ahora verifica Plan en BD primero")
            print()
        
        if plan_type_inconsistente:
            print(f"{Colors.YELLOW}3. Inconsistencias en plan_type ({len(plan_type_inconsistente)}):{Colors.RESET}")
            print("   - Verificar sincronización con Stripe")
            print("   - Usar /subscription-status para sincronizar")
            print()
        
        if plan_sin_premium:
            print(f"{Colors.YELLOW}4. Usuarios con plan pero sin premium ({len(plan_sin_premium)}):{Colors.RESET}")
            print("   - Posible caso de usuario que canceló suscripción")
            print("   - Verificar estado en Stripe")
            print()
    else:
        print_success("¡No se detectaron inconsistencias! La base de datos está en buen estado.")
    
    # Guardar reporte en archivo
    report_file = root_dir / "audit_report.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"REPORTE DE AUDITORÍA - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("="*70 + "\n\n")
        f.write(f"Total usuarios: {total_usuarios}\n")
        f.write(f"Usuarios premium: {usuarios_premium}\n")
        f.write(f"Total planes: {total_planes}\n")
        f.write(f"Inconsistencias: {len(issues)}\n\n")
        
        if issues:
            f.write("PROBLEMAS DETECTADOS:\n")
            f.write("-"*70 + "\n")
            for issue in issues:
                f.write(f"\nTipo: {issue['tipo']}\n")
                f.write(f"Usuario ID: {issue['user_id']}\n")
                f.write(f"Email: {issue['email']}\n")
                f.write(f"Descripción: {issue['descripcion']}\n")
    
    print_info(f"\nReporte guardado en: {report_file}")

def main():
    """Función principal"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("="*70)
    print("  AUDITORÍA DE BASE DE DATOS POSTGRESQL - RAILWAY")
    print("="*70)
    print(f"{Colors.RESET}\n")
    
    try:
        # Conectar a la base de datos
        engine = get_database_connection()
        
        # Ejecutar auditorías
        usuarios_data = audit_usuarios(engine)
        planes_data = audit_planes(engine)
        issues = detectar_inconsistencias(engine, usuarios_data, planes_data)
        
        # Generar reporte
        generar_reporte(issues, usuarios_data, planes_data)
        
        return 0 if not issues else 1
        
    except Exception as e:
        print_error(f"Error durante la auditoría: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
