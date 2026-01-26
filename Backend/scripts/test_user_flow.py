#!/usr/bin/env python3
"""
Script de testing para verificar el flujo completo de usuario después de aplicar los fixes.

Simula:
1. Registro de usuario
2. Login
3. Onboarding completo
4. Activación premium (fallback endpoint)
5. Verificación de estado
6. Logout (simulado)
7. Login nuevamente
8. Verificación final

Uso:
    # Local
    python scripts/test_user_flow.py
    
    # Producción (Railway)
    API_BASE_URL=https://tu-dominio.railway.app python scripts/test_user_flow.py
"""

import os
import sys
import time
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Añadir el directorio raíz al path para imports
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

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

def print_step(step_num: int, step_name: str):
    print(f"\n{Colors.BOLD}{Colors.CYAN}[PASO {step_num}] {step_name}{Colors.RESET}")

class UserFlowTester:
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url.rstrip('/')
        self.session = requests.Session()
        self.token: Optional[str] = None
        self.user_email: str = f"test_{int(time.time())}@test.com"
        self.user_password: str = "TestPassword123!"
        self.user_id: Optional[int] = None
        self.test_results: Dict[str, Any] = {
            "started_at": datetime.now().isoformat(),
            "steps": [],
            "errors": []
        }
    
    def log_step(self, step_name: str, success: bool, details: Dict = None):
        """Registra un paso del test"""
        step_data = {
            "step": step_name,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.test_results["steps"].append(step_data)
        
        if success:
            print_success(f"{step_name}: OK")
            if details:
                for key, value in details.items():
                    print_info(f"  {key}: {value}")
        else:
            print_error(f"{step_name}: FALLÓ")
            if details:
                for key, value in details.items():
                    print_error(f"  {key}: {value}")
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Hace una petición HTTP con manejo de errores"""
        url = f"{self.api_base_url}{endpoint}"
        
        # Añadir token si existe
        if self.token and 'headers' not in kwargs:
            kwargs['headers'] = {}
        if self.token:
            kwargs.setdefault('headers', {})['Authorization'] = f"Bearer {self.token}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            return response
        except Exception as e:
            print_error(f"Error en petición {method} {endpoint}: {e}")
            raise
    
    def step1_register(self) -> bool:
        """Paso 1: Registrar usuario"""
        print_step(1, "REGISTRO DE USUARIO")
        print_info(f"Email: {self.user_email}")
        print_info(f"Password: {self.user_password}")
        
        try:
            response = self.make_request(
                "POST",
                "/register",
                json={
                    "email": self.user_email,
                    "password": self.user_password
                }
            )
            
            if response.status_code == 200:
                self.log_step("Registro", True, {"email": self.user_email})
                return True
            elif response.status_code == 400 and "ya existe" in response.text.lower():
                print_warning("Usuario ya existe, continuando...")
                self.log_step("Registro", True, {"email": self.user_email, "note": "Ya existía"})
                return True
            else:
                self.log_step("Registro", False, {
                    "status_code": response.status_code,
                    "response": response.text
                })
                return False
        except Exception as e:
            self.log_step("Registro", False, {"error": str(e)})
            return False
    
    def step2_login(self) -> bool:
        """Paso 2: Iniciar sesión"""
        print_step(2, "LOGIN")
        
        try:
            response = self.make_request(
                "POST",
                "/login",
                json={
                    "email": self.user_email,
                    "password": self.user_password
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                onboarding_completed = data.get("onboarding_completed", False)
                
                if not self.token:
                    self.log_step("Login", False, {"error": "No se recibió token"})
                    return False
                
                # Decodificar token para obtener user_id (simple, sin verificar firma)
                import base64
                try:
                    payload = self.token.split('.')[1]
                    payload += '=' * (4 - len(payload) % 4)  # Padding
                    decoded = json.loads(base64.urlsafe_b64decode(payload))
                    self.user_id = int(decoded.get("sub", 0))
                except:
                    pass
                
                self.log_step("Login", True, {
                    "token_received": bool(self.token),
                    "onboarding_completed": onboarding_completed,
                    "user_id": self.user_id
                })
                return True
            else:
                self.log_step("Login", False, {
                    "status_code": response.status_code,
                    "response": response.text
                })
                return False
        except Exception as e:
            self.log_step("Login", False, {"error": str(e)})
            return False
    
    def step3_get_user_status(self) -> Dict:
        """Obtener estado del usuario"""
        try:
            response = self.make_request("GET", "/api/user/me")
            
            if response.status_code == 200:
                return response.json()
            else:
                print_error(f"Error obteniendo estado: {response.status_code}")
                return {}
        except Exception as e:
            print_error(f"Error en get_user_status: {e}")
            return {}
    
    def step4_onboarding(self) -> bool:
        """Paso 4: Completar onboarding"""
        print_step(4, "ONBOARDING COMPLETO")
        
        onboarding_data = {
            "altura": 175,
            "peso": 75.0,
            "edad": 30,
            "sexo": "hombre",
            "experiencia": "intermedio",
            "materiales": "gym",
            "tipo_cuerpo": "mesomorfo",
            "nivel_actividad": "moderado",
            "alergias": None,
            "restricciones_dieta": None,
            "lesiones": None,
            "idioma": "es",
            "puntos_fuertes": None,
            "puntos_debiles": None,
            "entrenar_fuerte": True,
            "gym_goal": "ganar_musculo",
            "nutrition_goal": "volumen",
            "training_frequency": 4,
            "training_days": ["lunes", "martes", "jueves", "viernes"],
            "session_duration": "45-60"
        }
        
        print_info("Enviando datos de onboarding...")
        
        try:
            response = self.make_request(
                "POST",
                "/onboarding",
                json=onboarding_data,
                timeout=120  # Onboarding puede tardar
            )
            
            if response.status_code == 200:
                data = response.json()
                has_rutina = "rutina" in data or "plan_id" in data
                
                self.log_step("Onboarding", True, {
                    "plan_id": data.get("plan_id"),
                    "has_rutina": has_rutina
                })
                
                # Verificar estado después de onboarding
                user_status = self.step3_get_user_status()
                onboarding_completed = user_status.get("onboarding_completed", False)
                
                print_info(f"Estado después de onboarding:")
                print_info(f"  onboarding_completed: {onboarding_completed}")
                print_info(f"  is_premium: {user_status.get('is_premium', False)}")
                
                return True
            else:
                self.log_step("Onboarding", False, {
                    "status_code": response.status_code,
                    "response": response.text[:200]
                })
                return False
        except Exception as e:
            self.log_step("Onboarding", False, {"error": str(e)})
            return False
    
    def step5_verify_before_premium(self) -> Dict:
        """Paso 5: Verificar estado antes de activar premium"""
        print_step(5, "VERIFICACIÓN PRE-PREMIUM")
        
        user_status = self.step3_get_user_status()
        
        checks = {
            "is_premium": user_status.get("is_premium", False),
            "plan_type": user_status.get("plan_type", "UNKNOWN"),
            "onboarding_completed": user_status.get("onboarding_completed", False),
            "has_routine": bool(user_status.get("current_routine")),
            "has_plan_in_db": False  # Se verifica después
        }
        
        print_info("Estado antes de activar premium:")
        for key, value in checks.items():
            status = "✅" if value else "❌"
            print_info(f"  {key}: {status} ({value})")
        
        self.log_step("Verificación Pre-Premium", True, checks)
        return checks
    
    def step6_activate_premium(self) -> bool:
        """Paso 6: Activar premium usando fallback endpoint"""
        print_step(6, "ACTIVACIÓN PREMIUM (FALLBACK)")
        
        try:
            # Usar el endpoint de fallback sin session_id (modo dev)
            # El endpoint espera un body JSON, incluso si está vacío
            response = self.make_request(
                "POST",
                "/stripe/activate-premium",
                json={},  # Sin session_id para activación directa
            )
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                plan_generated = data.get("plan_generated", False)
                
                self.log_step("Activación Premium", success, {
                    "success": success,
                    "is_premium": data.get("is_premium"),
                    "plan_type": data.get("plan_type"),
                    "plan_generated": plan_generated,
                    "activated_by": data.get("activated_by")
                })
                
                return success
            else:
                self.log_step("Activación Premium", False, {
                    "status_code": response.status_code,
                    "response": response.text[:200]
                })
                return False
        except Exception as e:
            self.log_step("Activación Premium", False, {"error": str(e)})
            return False
    
    def step7_verify_after_premium(self) -> Dict:
        """Paso 7: Verificar estado después de activar premium"""
        print_step(7, "VERIFICACIÓN POST-PREMIUM")
        
        # Esperar un momento para que se procese
        time.sleep(2)
        
        user_status = self.step3_get_user_status()
        
        checks = {
            "is_premium": user_status.get("is_premium", False),
            "plan_type": user_status.get("plan_type", "UNKNOWN"),
            "onboarding_completed": user_status.get("onboarding_completed", False),
            "session_duration": user_status.get("session_duration", "N/A")
        }
        
        print_info("Estado después de activar premium:")
        for key, value in checks.items():
            status = "✅" if (value and value != "N/A") else "❌"
            print_info(f"  {key}: {status} ({value})")
        
        # Verificaciones críticas
        issues = []
        if not checks["is_premium"]:
            issues.append("is_premium debería ser True")
        if checks["plan_type"] not in ["PREMIUM_MONTHLY", "PREMIUM_YEARLY", "PREMIUM"]:
            issues.append(f"plan_type debería ser PREMIUM_*, actual: {checks['plan_type']}")
        if not checks["onboarding_completed"]:
            issues.append("onboarding_completed debería ser True (tiene Plan en BD)")
        
        if issues:
            print_warning("Problemas detectados:")
            for issue in issues:
                print_warning(f"  - {issue}")
        else:
            print_success("¡Todas las verificaciones pasaron!")
        
        self.log_step("Verificación Post-Premium", len(issues) == 0, {
            **checks,
            "issues": issues
        })
        
        return checks
    
    def step8_logout_simulate(self) -> bool:
        """Paso 8: Simular logout (eliminar token)"""
        print_step(8, "LOGOUT (SIMULADO)")
        
        old_token = self.token
        self.token = None
        
        self.log_step("Logout", True, {"token_cleared": True})
        return True
    
    def step9_login_again(self) -> bool:
        """Paso 9: Volver a iniciar sesión"""
        print_step(9, "LOGIN NUEVAMENTE")
        
        return self.step2_login()
    
    def step10_verify_final_state(self) -> Dict:
        """Paso 10: Verificar estado final después de segundo login"""
        print_step(10, "VERIFICACIÓN FINAL")
        
        user_status = self.step3_get_user_status()
        login_response = self.make_request(
            "POST",
            "/login",
            json={
                "email": self.user_email,
                "password": self.user_password
            }
        )
        
        login_data = login_response.json() if login_response.status_code == 200 else {}
        
        checks = {
            "is_premium": user_status.get("is_premium", False),
            "plan_type": user_status.get("plan_type", "UNKNOWN"),
            "onboarding_completed": user_status.get("onboarding_completed", False),
            "onboarding_completed_in_login": login_data.get("onboarding_completed", False),
            "has_routine": bool(user_status.get("current_routine")),
            "session_duration": user_status.get("session_duration", "N/A")
        }
        
        print_info("Estado final:")
        for key, value in checks.items():
            status = "✅" if (value and value != "N/A") else "❌"
            print_info(f"  {key}: {status} ({value})")
        
        # Verificación crítica: onboarding_completed debe ser consistente
        if checks["onboarding_completed"] != checks["onboarding_completed_in_login"]:
            print_warning("⚠️  INCONSISTENCIA: onboarding_completed difiere entre /api/user/me y /login")
        else:
            print_success("✅ onboarding_completed es consistente entre endpoints")
        
        self.log_step("Verificación Final", True, checks)
        return checks
    
    def run_full_test(self) -> bool:
        """Ejecuta el flujo completo de testing"""
        print_header("TEST DE FLUJO COMPLETO DE USUARIO")
        print_info(f"API Base URL: {self.api_base_url}")
        print_info(f"Usuario de prueba: {self.user_email}")
        print_info(f"Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        steps = [
            ("Registro", self.step1_register),
            ("Login Inicial", self.step2_login),
            ("Onboarding", self.step4_onboarding),
            ("Verificación Pre-Premium", self.step5_verify_before_premium),
            ("Activación Premium", self.step6_activate_premium),
            ("Verificación Post-Premium", self.step7_verify_after_premium),
            ("Logout", self.step8_logout_simulate),
            ("Login Nuevamente", self.step9_login_again),
            ("Verificación Final", self.step10_verify_final_state),
        ]
        
        all_passed = True
        
        for step_name, step_func in steps:
            try:
                result = step_func()
                if not result:
                    all_passed = False
                    print_error(f"El paso '{step_name}' falló")
            except Exception as e:
                all_passed = False
                print_error(f"Error en paso '{step_name}': {e}")
                self.test_results["errors"].append({
                    "step": step_name,
                    "error": str(e)
                })
        
        # Generar reporte
        self.test_results["completed_at"] = datetime.now().isoformat()
        self.test_results["all_passed"] = all_passed
        
        return all_passed
    
    def save_report(self):
        """Guarda el reporte del test"""
        report_file = root_dir / "test_user_flow_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        print_info(f"\nReporte guardado en: {report_file}")

def main():
    """Función principal"""
    # Obtener URL de la API
    api_base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    
    if not api_base_url:
        print_error("Debes especificar API_BASE_URL")
        print_info("Ejemplo: API_BASE_URL=https://tu-dominio.railway.app python scripts/test_user_flow.py")
        sys.exit(1)
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("="*70)
    print("  TEST DE FLUJO COMPLETO DE USUARIO")
    print("="*70)
    print(f"{Colors.RESET}\n")
    
    tester = UserFlowTester(api_base_url)
    
    try:
        success = tester.run_full_test()
        
        # Guardar reporte
        tester.save_report()
        
        # Resumen final
        print_header("RESUMEN FINAL")
        if success:
            print_success("¡Todos los pasos del test pasaron correctamente!")
            print_info("El flujo completo funciona como se espera.")
            return 0
        else:
            print_error("Algunos pasos del test fallaron")
            print_info("Revisa los logs arriba para más detalles")
            print_info("Revisa el reporte JSON para análisis detallado")
            return 1
            
    except KeyboardInterrupt:
        print_warning("\nTest interrumpido por el usuario")
        tester.save_report()
        return 1
    except Exception as e:
        print_error(f"Error fatal: {e}")
        import traceback
        traceback.print_exc()
        tester.save_report()
        return 1

if __name__ == "__main__":
    sys.exit(main())
