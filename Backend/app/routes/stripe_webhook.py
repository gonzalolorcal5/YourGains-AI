from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
import stripe
import os
import json
from dotenv import load_dotenv

from app.database import SessionLocal
from app.models import Usuario
from app.utils.gpt import generar_plan_personalizado

router = APIRouter()
# Cargar .env desde la raíz del proyecto Backend
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

async def generate_and_save_ai_plan(db: Session, user_id: int):
    """
    Genera un plan personalizado con IA para un usuario premium
    🔧 FIX: Ahora es async para poder usar await con generar_plan_personalizado
    """
    try:
        user = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not user:
            print(f"❌ Usuario {user_id} no encontrado")
            return
        
        # Obtener datos del onboarding desde la tabla planes
        from app.models import Plan
        plan_data = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.id.desc()).first()
        
        if not plan_data:
            print(f"❌ No hay datos de onboarding para usuario {user_id}")
            return
        
        # Preparar datos del usuario (incluyendo todos los campos necesarios)
        user_info = {
            'altura': plan_data.altura or 175,
            'peso': float(plan_data.peso) if plan_data.peso else 75.0,
            'edad': plan_data.edad or 25,
            'sexo': plan_data.sexo or 'masculino',
            'objetivo': plan_data.objetivo_gym or (plan_data.objetivo or 'ganar_musculo'),
            'gym_goal': plan_data.objetivo_gym or 'ganar_musculo',
            'nutrition_goal': plan_data.objetivo_nutricional or (plan_data.objetivo_dieta or 'mantenimiento'),
            'experiencia': plan_data.experiencia or 'principiante',
            'materiales': plan_data.materiales or 'gym_completo',
            'tipo_cuerpo': plan_data.tipo_cuerpo or 'mesomorfo',
            'alergias': plan_data.alergias or 'Ninguna',
            'restricciones': plan_data.restricciones_dieta or 'Ninguna',
            'lesiones': plan_data.lesiones or 'Ninguna',
            'nivel_actividad': plan_data.nivel_actividad or 'moderado',
            'training_frequency': 4,
            'training_days': ['lunes', 'martes', 'jueves', 'viernes']
        }
        
        print(f"🤖 Generando plan con IA para usuario {user_id}...")
        print(f"📋 Datos: {user_info['sexo']}, {user_info['edad']} años, {user_info['altura']}cm, {user_info['peso']}kg")
        
        # 🔧 FIX: Usar await porque generar_plan_personalizado es async
        plan = await generar_plan_personalizado(user_info)
        
        # Convertir al formato esperado por current_routine y current_diet
        from datetime import datetime
        
        # Convertir rutina de formato "dias" a formato "exercises"
        exercises = []
        if "rutina" in plan and "dias" in plan["rutina"]:
            for dia in plan["rutina"]["dias"]:
                for ejercicio in dia.get("ejercicios", []):
                    exercises.append({
                        "name": ejercicio.get("nombre", ""),
                        "sets": ejercicio.get("series", 3),
                        "reps": ejercicio.get("repeticiones", "10-12"),
                        "weight": "moderado",
                        "day": dia.get("dia", "")
                    })
        
        current_routine = {
            "exercises": exercises,
            "schedule": {},
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
        
        # Convertir dieta al formato current_diet
        # Extraer macros del plan generado (ahora están en plan["dieta"].macros gracias a gpt.py)
        macros_plan = plan["dieta"].get("macros", {})
        # Si no están en el nivel raíz, intentar desde metadata
        if not macros_plan or (isinstance(macros_plan, dict) and len(macros_plan) == 0):
            metadata_macros = plan["dieta"].get("metadata", {}).get("macros_objetivo", {})
            if metadata_macros:
                macros_plan = {
                    "proteina": metadata_macros.get("proteina", 0),
                    "carbohidratos": metadata_macros.get("carbohidratos", 0),
                    "grasas": metadata_macros.get("grasas", 0)
                }
        
        # 🔧 FIX: Normalizar macros a formato consistente (proteinas en plural)
        macros_normalizados = {
            "proteinas": macros_plan.get("proteinas", macros_plan.get("proteina", 0)),
            "carbohidratos": macros_plan.get("carbohidratos", macros_plan.get("carbos", 0)),
            "grasas": macros_plan.get("grasas", macros_plan.get("grasa", 0))
        }
        
        current_diet = {
            "meals": plan["dieta"].get("comidas", []),
            "total_kcal": plan["dieta"].get("total_calorias", plan["dieta"].get("total_kcal", 2200)),
            "macros": macros_normalizados,  # ✅ Usar macros normalizados (proteinas en plural)
            "objetivo": user_info['nutrition_goal'],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
        
        # Guardar en DB - Actualizar current_routine y current_diet
        user.current_routine = json.dumps(current_routine, ensure_ascii=False)
        user.current_diet = json.dumps(current_diet, ensure_ascii=False)
        
        # 🔧 FIX: También actualizar Plan.dieta si existe
        if plan_data:
            plan_data.rutina = json.dumps(plan["rutina"], ensure_ascii=False)
            plan_data.dieta = json.dumps(plan["dieta"], ensure_ascii=False)
            print(f"✅ Plan.dieta y Plan.rutina también actualizados")
        
        db.commit()
        
        print(f"✅ Plan de IA generado y guardado para usuario {user_id}")
        print(f"🏋️ Ejercicios: {len(exercises)}")
        print(f"🍽️ Comidas: {len(current_diet.get('meals', []))}")
        
    except Exception as e:
        print(f"❌ Error generando plan para usuario {user_id}: {e}")
        import traceback
        traceback.print_exc()

def set_customer_id_by_email(db: Session, email: str, customer_id: str):
    user = db.query(Usuario).filter(Usuario.email == email).first()
    if user:
        user.stripe_customer_id = customer_id
        db.commit()

async def set_premium_by_customer(db: Session, customer_id: str, is_premium: bool):
    user = db.query(Usuario).filter(Usuario.stripe_customer_id == customer_id).first()
    if user:
        user.is_premium = is_premium
        user.plan_type = "PREMIUM" if is_premium else "FREE"
        if not is_premium:
            # si baja a FREE, reseteamos las 2 preguntas gratuitas
            user.chat_uses_free = 2
        else:
            # 🔥 NUEVO: Generar plan con IA cuando se hace premium
            print(f"💎 Usuario {user.id} se hizo PREMIUM, regenerando plan con GPT...")
            await generate_and_save_ai_plan(db, user.id)
            print(f"✅ Plan regenerado para usuario premium {user.id}")
        
        db.commit()

@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not endpoint_secret:
        raise HTTPException(status_code=500, detail="Stripe webhook secret no configurado")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        raise HTTPException(status_code=400, detail="Payload inválido")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Firma webhook inválida")

    db = SessionLocal()
    try:
        etype = event["type"]
        obj = event["data"]["object"]

        # Al completar el checkout asociamos el customer al email
        if etype == "checkout.session.completed":
            customer_id = obj.get("customer")
            email = (obj.get("customer_details") or {}).get("email")
            payment_status = obj.get("payment_status")
            
            if customer_id and email:
                set_customer_id_by_email(db, email, customer_id)
                
                # 🔥 NUEVO: Si el pago es exitoso, activar premium inmediatamente
                if payment_status == "paid":
                    print(f"💳 Pago confirmado para {email}, activando premium...")
                    await set_premium_by_customer(db, customer_id, True)

        # Suscripción creada/actualizada → premium si status activo o trial
        elif etype in ("customer.subscription.created", "customer.subscription.updated"):
            status = obj.get("status")          # active, trialing, past_due, canceled...
            customer_id = obj.get("customer")
            if customer_id and status:
                await set_premium_by_customer(db, customer_id, status in ("active", "trialing"))

        # Suscripción cancelada → premium = False
        elif etype == "customer.subscription.deleted":
            customer_id = obj.get("customer")
            if customer_id:
                await set_premium_by_customer(db, customer_id, False)

        # NUEVO: Manejar payment_intent.succeeded (pagos directos)
        elif etype == "payment_intent.succeeded":
            print("=" * 50)
            print(f"🔥 EVENTO DETECTADO: payment_intent.succeeded")
            print(f"📦 Payment Intent ID: {obj.get('id')}")
            print(f"📋 Metadata: {obj.get('metadata')}")
            print("=" * 50)
            
            # Obtener user_id de metadata
            metadata = obj.get('metadata', {})
            user_id = metadata.get('user_id')
            
            print(f"🔍 user_id en metadata: {user_id}")
            
            if user_id:
                try:
                    user_id = int(user_id)
                    user = db.query(Usuario).filter(Usuario.id == user_id).first()
                    
                    if user:
                        print(f"💎 Usuario encontrado! ID={user.id}, Email={user.email}")
                        
                        # Actualizar a premium
                        user.is_premium = True
                        user.plan_type = "PREMIUM"
                        user.chat_uses_free = 999
                        customer_id = obj.get("customer")
                        if customer_id:
                            user.stripe_customer_id = customer_id
                        db.commit()
                        print(f"✅ Usuario {user.id} actualizado a PREMIUM")
                        
                        # Generar plan con IA
                        print(f"🤖 Iniciando generación de plan con IA...")
                        await generate_and_save_ai_plan(db, user.id)
                        print(f"🎉 Plan generado exitosamente para usuario {user.id}")
                    else:
                        print(f"❌ No se encontró usuario con ID: {user_id}")
                except Exception as e:
                    print(f"❌ Error procesando webhook: {e}")
            else:
                print(f"❌ payment_intent no tiene user_id en metadata")
            
            print("=" * 50)

        return {"status": "ok"}
    finally:
        db.close()
