"""
Script de diagnóstico para verificar el flujo de planes FREE vs PREMIUM
Ejecutar: python diagnose_user_plan.py <user_id>
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import get_db
from app.models import Usuario, Plan
from sqlalchemy.orm import Session
import json

def diagnose_user(user_id: int):
    db: Session = next(get_db())
    
    try:
        user = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not user:
            print(f"❌ Usuario {user_id} no encontrado")
            return
        
        print("=" * 60)
        print(f"🔍 DIAGNÓSTICO USUARIO {user_id}")
        print("=" * 60)
        
        # 1. Estado del usuario
        print(f"\n1️⃣ ESTADO DEL USUARIO:")
        print(f"   Email: {user.email}")
        print(f"   is_premium: {user.is_premium}")
        print(f"   plan_type: {user.plan_type}")
        print(f"   onboarding_completed: {user.onboarding_completed}")
        
        is_premium = user.is_premium or user.plan_type == "PREMIUM"
        print(f"   ✅ is_premium calculado: {is_premium}")
        
        # 2. current_routine y current_diet
        print(f"\n2️⃣ CURRENT_ROUTINE & CURRENT_DIET:")
        has_current_routine = bool(user.current_routine)
        has_current_diet = bool(user.current_diet)
        print(f"   current_routine existe: {has_current_routine}")
        if has_current_routine:
            print(f"   current_routine length: {len(user.current_routine)} chars")
            try:
                routine_data = json.loads(user.current_routine)
                exercises = routine_data.get('exercises', [])
                print(f"   ✅ Ejercicios en current_routine: {len(exercises)}")
                print(f"   is_generic: {routine_data.get('is_generic', False)}")
            except:
                print(f"   ❌ Error parseando current_routine")
        else:
            print(f"   ❌ current_routine es NULL/vacío")
        
        print(f"   current_diet existe: {has_current_diet}")
        if has_current_diet:
            print(f"   current_diet length: {len(user.current_diet)} chars")
            try:
                diet_data = json.loads(user.current_diet)
                meals = diet_data.get('meals', [])
                print(f"   ✅ Comidas en current_diet: {len(meals)}")
                print(f"   is_generic: {diet_data.get('is_generic', False)}")
            except:
                print(f"   ❌ Error parseando current_diet")
        else:
            print(f"   ❌ current_diet es NULL/vacío")
        
        # 3. Planes en tabla planes
        print(f"\n3️⃣ PLANES EN TABLA PLANES:")
        plans = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.id.desc()).all()
        print(f"   Total planes: {len(plans)}")
        
        if plans:
            latest_plan = plans[0]
            print(f"   📋 Plan más reciente (ID: {latest_plan.id}):")
            print(f"      Fecha: {latest_plan.fecha_creacion}")
            print(f"      Objetivo: {latest_plan.objetivo}")
            print(f"      Rutina existe: {bool(latest_plan.rutina)}")
            print(f"      Dieta existe: {bool(latest_plan.dieta)}")
            
            if latest_plan.rutina:
                try:
                    rutina_data = json.loads(latest_plan.rutina)
                    if "dias" in rutina_data:
                        total_ejercicios = sum(len(dia.get("ejercicios", [])) for dia in rutina_data["dias"])
                        print(f"      ✅ Ejercicios en rutina: {total_ejercicios}")
                except:
                    print(f"      ❌ Error parseando rutina")
            
            if latest_plan.dieta:
                try:
                    dieta_data = json.loads(latest_plan.dieta)
                    comidas = dieta_data.get("comidas", [])
                    print(f"      ✅ Comidas en dieta: {len(comidas)}")
                except:
                    print(f"      ❌ Error parseando dieta")
        
        # 4. ¿Qué vería el frontend?
        print(f"\n4️⃣ ¿QUÉ VERÍA EL FRONTEND?")
        
        if is_premium and has_current_routine:
            print(f"   ✅ MOSTRARÍA: Plan personalizado desde current_routine")
        elif is_premium and not has_current_routine:
            if plans and plans[0].rutina:
                print(f"   ⚠️ MOSTRARÍA: Plan de tabla planes (fallback)")
            else:
                print(f"   ❌ MOSTRARÍA: Template genérico (sin plan disponible)")
        else:
            print(f"   📋 MOSTRARÍA: Template genérico (usuario FREE)")
        
        print("\n" + "=" * 60)
        print("✅ DIAGNÓSTICO COMPLETADO")
        print("=" * 60)
        
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python diagnose_user_plan.py <user_id>")
        sys.exit(1)
    
    user_id = int(sys.argv[1])
    diagnose_user(user_id)

