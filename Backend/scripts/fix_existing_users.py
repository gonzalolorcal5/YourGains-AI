#!/usr/bin/env python3
"""
Script de migración one-time para corregir inconsistencias en usuarios existentes.

Corrige:
1. Usuarios premium sin current_routine válida
2. Copia rutina y dieta del Plan más reciente si existe
3. Asegura que onboarding_completed = true si tiene Plan

Uso:
    # Modo dry-run (solo muestra qué haría)
    python scripts/fix_existing_users.py
    
    # Modo ejecución real
    python scripts/fix_existing_users.py --execute
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

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

def is_valid_routine(routine_str: Optional[str]) -> bool:
    """Verifica si current_routine es válida (no vacía)"""
    if not routine_str:
        return False
    
    if routine_str.strip() == '{}':
        return False
    
    try:
        routine_data = json.loads(routine_str)
        if isinstance(routine_data, dict):
            # Verificar que tenga contenido válido
            has_exercises = bool(routine_data.get("exercises")) and len(routine_data.get("exercises", [])) > 0
            has_dias = bool(routine_data.get("dias")) and len(routine_data.get("dias", [])) > 0
            return has_exercises or has_dias
        return False
    except (json.JSONDecodeError, AttributeError, KeyError):
        return False

def is_valid_diet(diet_str: Optional[str]) -> bool:
    """Verifica si current_diet es válida (no vacía)"""
    if not diet_str:
        return False
    
    if diet_str.strip() == '{}':
        return False
    
    try:
        diet_data = json.loads(diet_str)
        if isinstance(diet_data, dict):
            # Verificar que tenga contenido válido
            has_comidas = bool(diet_data.get("comidas")) and len(diet_data.get("comidas", [])) > 0
            return has_comidas
        return False
    except (json.JSONDecodeError, AttributeError, KeyError):
        return False

class UserFixer:
    def __init__(self, engine, dry_run: bool = True):
        self.engine = engine
        self.dry_run = dry_run
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        self.fixes_applied: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
    
    def find_problematic_users(self) -> List[Dict[str, Any]]:
        """Busca usuarios premium sin current_routine válida"""
        print_header("BUSCANDO USUARIOS PROBLEMÁTICOS")
        
        query = text("""
            SELECT 
                u.id,
                u.email,
                u.is_premium,
                u.plan_type,
                u.current_routine,
                u.current_diet,
                u.onboarding_completed,
                CASE
                    WHEN EXISTS (SELECT 1 FROM planes WHERE user_id = u.id) THEN true
                    ELSE false
                END as tiene_plan
            FROM usuarios u
            WHERE u.is_premium = true
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query)
            all_premium = result.fetchall()
        
        problematic_users = []
        
        for row in all_premium:
            user_id, email, is_premium, plan_type, current_routine, current_diet, onboarding_completed, tiene_plan = row
            
            has_valid_routine = is_valid_routine(current_routine)
            has_valid_diet = is_valid_diet(current_diet)
            
            # Usuario problemático si:
            # 1. No tiene rutina válida, O
            # 2. Tiene Plan pero onboarding_completed = false
            if not has_valid_routine or not has_valid_diet or (tiene_plan and not onboarding_completed):
                problematic_users.append({
                    "id": user_id,
                    "email": email,
                    "plan_type": plan_type,
                    "has_valid_routine": has_valid_routine,
                    "has_valid_diet": has_valid_diet,
                    "onboarding_completed": onboarding_completed,
                    "tiene_plan": tiene_plan,
                    "current_routine": current_routine,
                    "current_diet": current_diet
                })
        
        print_info(f"Total usuarios premium: {len(all_premium)}")
        print_info(f"Usuarios problemáticos encontrados: {len(problematic_users)}")
        
        return problematic_users
    
    def get_latest_plan(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene el Plan más reciente del usuario"""
        query = text("""
            SELECT 
                id,
                rutina,
                dieta,
                fecha_creacion
            FROM planes
            WHERE user_id = :user_id
            ORDER BY id DESC
            LIMIT 1
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {"user_id": user_id})
            row = result.fetchone()
        
        if row:
            return {
                "id": row[0],
                "rutina": row[1],
                "dieta": row[2],
                "fecha_creacion": row[3]
            }
        return None
    
    def fix_user(self, user_data: Dict[str, Any]) -> bool:
        """Corrige un usuario específico"""
        user_id = user_data["id"]
        email = user_data["email"]
        
        print(f"\n{Colors.BOLD}Usuario ID {user_id} ({email}):{Colors.RESET}")
        
        fixes_needed = []
        
        # Verificar si necesita copiar rutina/dieta del Plan
        if not user_data["has_valid_routine"] or not user_data["has_valid_diet"]:
            if user_data["tiene_plan"]:
                latest_plan = self.get_latest_plan(user_id)
                if latest_plan:
                    fixes_needed.append({
                        "type": "copy_routine_diet",
                        "plan_id": latest_plan["id"],
                        "rutina": latest_plan["rutina"],
                        "dieta": latest_plan["dieta"]
                    })
                    print_info(f"  → Copiar rutina y dieta del Plan ID {latest_plan['id']}")
                else:
                    print_warning(f"  ⚠️  Tiene Plan pero no se pudo obtener")
            else:
                print_warning(f"  ⚠️  No tiene Plan - no se puede copiar rutina/dieta")
        
        # Verificar si necesita actualizar onboarding_completed
        if user_data["tiene_plan"] and not user_data["onboarding_completed"]:
            fixes_needed.append({
                "type": "update_onboarding",
                "value": True
            })
            print_info(f"  → Actualizar onboarding_completed = true")
        
        if not fixes_needed:
            print_info("  ✅ No requiere correcciones")
            return True
        
        # Aplicar fixes
        if self.dry_run:
            print_warning(f"  [DRY-RUN] Se aplicarían {len(fixes_needed)} correcciones")
            self.fixes_applied.append({
                "user_id": user_id,
                "email": email,
                "fixes": fixes_needed,
                "applied": False
            })
            return True
        
        # Ejecutar fixes reales
        try:
            db = self.SessionLocal()
            
            try:
                from app.models import Usuario, Plan
                user = db.query(Usuario).filter(Usuario.id == user_id).first()
                
                if not user:
                    print_error(f"  ❌ Usuario {user_id} no encontrado")
                    self.errors.append({
                        "user_id": user_id,
                        "error": "Usuario no encontrado"
                    })
                    return False
                
                changes_made = []
                
                # Aplicar cada fix
                for fix in fixes_needed:
                    if fix["type"] == "copy_routine_diet":
                        user.current_routine = fix["rutina"]
                        user.current_diet = fix["dieta"]
                        changes_made.append("Rutina y dieta copiadas del Plan")
                        print_success(f"  ✅ Rutina y dieta copiadas del Plan ID {fix['plan_id']}")
                    
                    elif fix["type"] == "update_onboarding":
                        user.onboarding_completed = fix["value"]
                        changes_made.append(f"onboarding_completed = {fix['value']}")
                        print_success(f"  ✅ onboarding_completed actualizado a {fix['value']}")
                
                if changes_made:
                    db.commit()
                    print_success(f"  ✅ Cambios guardados para usuario {user_id}")
                    
                    self.fixes_applied.append({
                        "user_id": user_id,
                        "email": email,
                        "fixes": fixes_needed,
                        "changes": changes_made,
                        "applied": True
                    })
                else:
                    print_warning(f"  ⚠️  No se aplicaron cambios")
                
                return True
                
            except Exception as e:
                db.rollback()
                print_error(f"  ❌ Error aplicando fixes: {e}")
                self.errors.append({
                    "user_id": user_id,
                    "error": str(e)
                })
                return False
            finally:
                db.close()
                
        except Exception as e:
            print_error(f"  ❌ Error en fix_user: {e}")
            self.errors.append({
                "user_id": user_id,
                "error": str(e)
            })
            return False
    
    def run_fix(self):
        """Ejecuta el proceso completo de corrección"""
        print_header("MIGRACIÓN ONE-TIME: CORRECCIÓN DE USUARIOS EXISTENTES")
        
        if self.dry_run:
            print_warning("⚠️  MODO DRY-RUN: No se aplicarán cambios reales")
            print_info("Ejecuta con --execute para aplicar cambios\n")
        else:
            print_warning("🚨 MODO EJECUCIÓN: Se aplicarán cambios reales en la BD\n")
        
        # Buscar usuarios problemáticos
        problematic_users = self.find_problematic_users()
        
        if not problematic_users:
            print_success("✅ No se encontraron usuarios problemáticos")
            return
        
        print(f"\n{Colors.BOLD}Usuarios a corregir:{Colors.RESET}")
        for user in problematic_users:
            issues = []
            if not user["has_valid_routine"]:
                issues.append("sin rutina válida")
            if not user["has_valid_diet"]:
                issues.append("sin dieta válida")
            if user["tiene_plan"] and not user["onboarding_completed"]:
                issues.append("onboarding_completed = false")
            
            print(f"  - ID {user['id']} ({user['email']}): {', '.join(issues)}")
        
        # Confirmar si no es dry-run
        if not self.dry_run:
            print(f"\n{Colors.YELLOW}¿Continuar con la corrección? (s/n): {Colors.RESET}", end="")
            response = input().strip().lower()
            if response != 's' and response != 'y' and response != 'si' and response != 'yes':
                print_warning("Operación cancelada")
                return
        
        # Aplicar fixes
        print_header("APLICANDO CORRECCIONES")
        
        for user_data in problematic_users:
            self.fix_user(user_data)
        
        # Generar reporte
        self.generate_report()
    
    def generate_report(self):
        """Genera un reporte de los cambios realizados"""
        print_header("REPORTE FINAL")
        
        total_fixes = len(self.fixes_applied)
        applied_fixes = sum(1 for f in self.fixes_applied if f.get("applied", False))
        errors_count = len(self.errors)
        
        print_info(f"Total usuarios procesados: {total_fixes}")
        print_info(f"Correcciones aplicadas: {applied_fixes}")
        print_info(f"Errores: {errors_count}")
        
        if self.fixes_applied:
            print(f"\n{Colors.BOLD}Detalle de correcciones:{Colors.RESET}")
            for fix in self.fixes_applied:
                status = "✅ APLICADO" if fix.get("applied", False) else "🔍 DRY-RUN"
                print(f"\n  {status} - Usuario ID {fix['user_id']} ({fix['email']}):")
                for fix_detail in fix["fixes"]:
                    if fix_detail["type"] == "copy_routine_diet":
                        print(f"    - Copiar rutina y dieta del Plan ID {fix_detail['plan_id']}")
                    elif fix_detail["type"] == "update_onboarding":
                        print(f"    - Actualizar onboarding_completed = {fix_detail['value']}")
        
        if self.errors:
            print(f"\n{Colors.RED}{Colors.BOLD}Errores encontrados:{Colors.RESET}")
            for error in self.errors:
                print(f"  - Usuario ID {error['user_id']}: {error['error']}")
        
        # Guardar reporte en archivo
        report_file = root_dir / f"fix_users_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": self.dry_run,
            "total_fixes": total_fixes,
            "applied_fixes": applied_fixes,
            "errors_count": errors_count,
            "fixes": self.fixes_applied,
            "errors": self.errors
        }
        
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
        
        print_info(f"\nReporte guardado en: {report_file}")

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

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description="Corrige inconsistencias en usuarios existentes")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Ejecutar cambios reales (por defecto es dry-run)"
    )
    
    args = parser.parse_args()
    dry_run = not args.execute
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("="*70)
    print("  MIGRACIÓN ONE-TIME: CORRECCIÓN DE USUARIOS EXISTENTES")
    print("="*70)
    print(f"{Colors.RESET}\n")
    
    try:
        # Conectar a la base de datos
        engine = get_database_connection()
        
        # Ejecutar corrección
        fixer = UserFixer(engine, dry_run=dry_run)
        fixer.run_fix()
        
        return 0
        
    except KeyboardInterrupt:
        print_warning("\nOperación interrumpida por el usuario")
        return 1
    except Exception as e:
        print_error(f"Error fatal: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
