from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
import stripe
import os
import json
from dotenv import load_dotenv
from datetime import datetime

from app.database import SessionLocal
from app.models import Usuario
from app.utils.gpt import generar_plan_personalizado

router = APIRouter()

# =========================================
#   CONFIG STRIPE
# =========================================
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

PRICE_ID_MENSUAL = os.getenv("STRIPE_PRICE_MENSUAL")
PRICE_ID_ANUAL = os.getenv("STRIPE_PRICE_ANUAL")


async def generate_and_save_ai_plan(db: Session, user_id: int):
    """Genera plan con IA para usuario premium"""
    try:
        user = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not user:
            print(f"❌ Usuario {user_id} no encontrado")
            return

        from app.models import Plan
        plan_data = (
            db.query(Plan)
            .filter(Plan.user_id == user_id)
            .order_by(Plan.id.desc())
            .first()
        )

        if not plan_data:
            print(f"⚠️ No hay datos de onboarding para usuario {user_id}")
            return

        user_info = {
            'altura': plan_data.altura or 175,
            'peso': float(plan_data.peso) if plan_data.peso else 75.0,
            'edad': plan_data.edad or 25,
            'sexo': plan_data.sexo or 'masculino',
            'objetivo': plan_data.objetivo_gym or 'ganar_musculo',
            'gym_goal': plan_data.objetivo_gym or 'ganar_musculo',
            'nutrition_goal': plan_data.objetivo_nutricional or 'mantenimiento',
            'experiencia': plan_data.experiencia or 'principiante',
            'materiales': plan_data.materiales or 'gym_completo',
            'tipo_cuerpo': plan_data.tipo_cuerpo or 'mesomorfo',
            'alergias': plan_data.alergias or 'Ninguna',
            'restricciones': plan_data.restricciones_dieta or 'Ninguna',
            'lesiones': plan_data.lesiones or 'Ninguna',
            'nivel_actividad': plan_data.nivel_actividad or 'moderado',
            'training_frequency': 4,
            'training_days': ['lunes', 'martes', 'jueves', 'viernes'],
        }

        print(f"🤖 Generando plan IA para usuario {user_id}...")

        plan = await generar_plan_personalizado(user_info)

        # RUTINA
        exercises = []
        if "rutina" in plan and "dias" in plan["rutina"]:
            for dia in plan["rutina"]["dias"]:
                for ejercicio in dia.get("ejercicios", []):
                    exercises.append({
                        "name": ejercicio.get("nombre", ""),
                        "sets": ejercicio.get("series", 3),
                        "reps": ejercicio.get("repeticiones", "10-12"),
                        "weight": "moderado",
                        "day": dia.get("dia", ""),
                    })

        current_routine = {
            "exercises": exercises,
            "schedule": {},
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0.0",
        }

        # DIETA
        macros_plan = plan["dieta"].get("macros", {})
        if not macros_plan:
            metadata_macros = plan["dieta"].get("metadata", {}).get("macros_objetivo", {})
            if metadata_macros:
                macros_plan = {
                    "proteina": metadata_macros.get("proteina", 0),
                    "carbohidratos": metadata_macros.get("carbohidratos", 0),
                    "grasas": metadata_macros.get("grasas", 0),
                }

        macros_normalizados = {
            "proteinas": macros_plan.get("proteinas", macros_plan.get("proteina", 0)),
            "carbohidratos": macros_plan.get("carbohidratos", 0),
            "grasas": macros_plan.get("grasas", 0),
        }

        current_diet = {
            "meals": plan["dieta"].get("comidas", []),
            "total_kcal": plan["dieta"].get("total_calorias", 2200),
            "macros": macros_normalizados,
            "objetivo": user_info['nutrition_goal'],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "version": "1.0.0",
        }

        user.current_routine = json.dumps(current_routine, ensure_ascii=False)
        user.current_diet = json.dumps(current_diet, ensure_ascii=False)

        if plan_data:
            plan_data.rutina = json.dumps(plan["rutina"], ensure_ascii=False)
            plan_data.dieta = json.dumps(plan["dieta"], ensure_ascii=False)

        db.commit()

        print(
            f"✅ Plan generado: {len(exercises)} ejercicios, "
            f"{len(current_diet.get('meals', []))} comidas"
        )

    except Exception as e:
        print(f"❌ Error generando plan: {e}")
        import traceback
        traceback.print_exc()


def set_customer_id_by_email(db: Session, email: str, customer_id: str):
    """Asocia customer_id a usuario por email"""
    user = db.query(Usuario).filter(Usuario.email == email).first()
    if user:
        user.stripe_customer_id = customer_id
        db.commit()


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Webhook de Stripe - ACTUALIZADO para método manual
    
    FLUJO NUEVO:
    1. payment_intent.succeeded → Activar premium + crear subscription recurrente
    2. invoice.payment_succeeded → Renovaciones automáticas
    3. customer.subscription.deleted → Cancelaciones
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not endpoint_secret:
        raise HTTPException(status_code=500, detail="Webhook secret no configurado")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        raise HTTPException(status_code=400, detail="Payload inválido")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Firma inválida")

    db = SessionLocal()
    try:
        etype = event["type"]
        obj = event["data"]["object"]

        # =====================================================
        #   🔥 PAYMENT_INTENT.SUCCEEDED - PRIMER PAGO
        # =====================================================
        if etype == "payment_intent.succeeded":
            payment_intent_id = obj.get("id")
            customer_id = obj.get("customer")
            metadata = obj.get("metadata", {})
            integration_type = metadata.get("integration_type")
            
            print("=" * 50)
            print(f"🔥 WEBHOOK: payment_intent.succeeded")
            print(f"💳 PaymentIntent ID: {payment_intent_id}")
            print(f"💳 Customer: {customer_id}")
            print(f"📋 Integration type: {integration_type}")
            print("=" * 50)
            
            # Solo procesar si es de nuestro flujo manual
            if integration_type == "manual_subscription":
                user_id = metadata.get("user_id")
                price_id = metadata.get("price_id")
                plan_type = metadata.get("plan_type", "monthly")
                
                if not user_id or not price_id:
                    print("❌ Faltan metadatos esenciales")
                    return {"status": "ok"}
                
                user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
                
                if not user:
                    print(f"❌ Usuario {user_id} no encontrado")
                    return {"status": "ok"}
                
                print(f"💎 Usuario encontrado: {user.id} ({user.email})")
                
                # Activar premium
                user.is_premium = True
                user.plan_type = "PREMIUM"
                user.subscription_type = plan_type
                user.subscription_start_date = datetime.utcnow()
                user.chat_uses_free = 999
                db.commit()
                
                print(f"✅ Usuario {user.id} → PREMIUM ({plan_type})")
                
                # Crear subscription recurrente para renovaciones automáticas
                try:
                    print(f"📝 Creando subscription recurrente...")
                    
                    # Obtener payment method del payment_intent
                    payment_method = obj.get("payment_method")
                    
                    subscription = stripe.Subscription.create(
                        customer=customer_id,
                        items=[{"price": price_id}],
                        default_payment_method=payment_method,
                        metadata={
                            "user_id": str(user_id),
                            "plan_type": plan_type
                        }
                    )
                    
                    print(f"✅ Subscription recurrente creada: {subscription.id}")
                    
                except Exception as e:
                    print(f"⚠️ Error creando subscription recurrente: {e}")
                    # No es crítico, el usuario ya es premium
                
                # Generar plan IA
                print("🤖 Generando plan IA...")
                try:
                    await generate_and_save_ai_plan(db, user.id)
                    print("✅ Plan generado")
                except Exception as e:
                    print(f"⚠️ Error generando plan (no crítico): {e}")
                
                print("=" * 50)

        # =====================================================
        #   invoice.payment_succeeded - RENOVACIONES
        # =====================================================
        elif etype == "invoice.payment_succeeded":
            customer_id = obj.get("customer")
            subscription_id = obj.get("subscription")
            
            print("=" * 50)
            print(f"🔥 WEBHOOK: invoice.payment_succeeded")
            print(f"💳 Customer: {customer_id}")
            print(f"📦 Subscription: {subscription_id}")
            print("=" * 50)
            
            if subscription_id:  # Es una renovación de subscription
                user = db.query(Usuario).filter(Usuario.stripe_customer_id == customer_id).first()
                
                if user and not user.is_premium:
                    print(f"♻️ Reactivando usuario {user.id} (renovación exitosa)")
                    user.is_premium = True
                    user.plan_type = "PREMIUM"
                    user.chat_uses_free = 999
                    db.commit()
                    print("✅ Usuario reactivado")
            
            print("=" * 50)

        # =====================================================
        #   customer.subscription.deleted - CANCELACIONES
        # =====================================================
        elif etype == "customer.subscription.deleted":
            subscription_id = obj.get("id")
            customer_id = obj.get("customer")

            print("=" * 50)
            print(f"🔥 WEBHOOK: customer.subscription.deleted")
            print(f"📦 Subscription ID: {subscription_id}")
            print(f"💳 Customer: {customer_id}")
            print("=" * 50)

            if not customer_id:
                print("❌ No customer_id en subscription")
                return {"status": "ok"}

            user = db.query(Usuario).filter(Usuario.stripe_customer_id == customer_id).first()
            if not user:
                print(f"❌ Usuario no encontrado para customer {customer_id}")
                return {"status": "ok"}

            print(f"💎 Usuario encontrado: {user.id} ({user.email})")

            # Desactivar premium
            user.is_premium = False
            user.plan_type = "FREE"
            user.subscription_type = None
            user.chat_uses_free = 2

            db.commit()
            print(f"✅ Usuario {user.id} → FREE (subscription cancelada)")
            print("=" * 50)

        return {"status": "ok"}

    except Exception as e:
        print(f"❌ Error crítico en webhook: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "ok"}

    finally:
        db.close()