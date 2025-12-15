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
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

# Price IDs para detectar tipo de plan
PRICE_ID_MENSUAL = os.getenv("STRIPE_PRICE_MENSUAL")
PRICE_ID_ANUAL = os.getenv("STRIPE_PRICE_ANUAL")

# ==========================================
# GENERACIÓN DE PLAN CON IA
# ==========================================
async def generate_and_save_ai_plan(db: Session, user_id: int):
    """
    Genera plan personalizado con IA para usuario premium.
    """
    try:
        user = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not user:
            print(f"❌ Usuario {user_id} no encontrado")
            return
        
        # Obtener datos del onboarding
        from app.models import Plan
        plan_data = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.id.desc()).first()
        
        if not plan_data:
            print(f"❌ No hay datos de onboarding para usuario {user_id}")
            return
        
        # Preparar datos del usuario
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
        
        # Usar await porque generar_plan_personalizado es async
        plan = await generar_plan_personalizado(user_info)
        
        from datetime import datetime
        
        # Convertir rutina al formato current_routine
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
        macros_plan = plan["dieta"].get("macros", {})
        if not macros_plan:
            metadata_macros = plan["dieta"].get("metadata", {}).get("macros_objetivo", {})
            if metadata_macros:
                macros_plan = {
                    "proteina": metadata_macros.get("proteina", 0),
                    "carbohidratos": metadata_macros.get("carbohidratos", 0),
                    "grasas": metadata_macros.get("grasas", 0)
                }
        
        # Normalizar macros (proteinas en plural)
        macros_normalizados = {
            "proteinas": macros_plan.get("proteinas", macros_plan.get("proteina", 0)),
            "carbohidratos": macros_plan.get("carbohidratos", macros_plan.get("carbos", 0)),
            "grasas": macros_plan.get("grasas", macros_plan.get("grasa", 0))
        }
        
        current_diet = {
            "meals": plan["dieta"].get("comidas", []),
            "total_kcal": plan["dieta"].get("total_calorias", plan["dieta"].get("total_kcal", 2200)),
            "macros": macros_normalizados,
            "objetivo": user_info['nutrition_goal'],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
        
        # Guardar en BD
        user.current_routine = json.dumps(current_routine, ensure_ascii=False)
        user.current_diet = json.dumps(current_diet, ensure_ascii=False)
        
        # También actualizar Plan.dieta y Plan.rutina
        if plan_data:
            plan_data.rutina = json.dumps(plan["rutina"], ensure_ascii=False)
            plan_data.dieta = json.dumps(plan["dieta"], ensure_ascii=False)
        
        db.commit()
        print(f"✅ Plan de IA generado y guardado para usuario {user_id}")
        
    except Exception as e:
        print(f"❌ Error generando plan para usuario {user_id}: {e}")
        import traceback
        traceback.print_exc()

# ==========================================
# HELPERS DE ACTUALIZACIÓN
# ==========================================
def set_customer_id_by_email(db: Session, email: str, customer_id: str):
    """Asocia customer_id de Stripe con usuario por email"""
    user = db.query(Usuario).filter(Usuario.email == email).first()
    if user:
        user.stripe_customer_id = customer_id
        db.commit()
        print(f"✅ Customer {customer_id} asociado a {email}")

async def set_premium_by_customer(
    db: Session,
    customer_id: str,
    is_premium: bool,
    subscription_id: str = None,
    price_id: str = None
):
    """
    Actualiza estado premium del usuario.
    🆕 Detecta PREMIUM_MONTHLY vs PREMIUM_YEARLY según price_id.
    🆕 Guarda stripe_subscription_id.
    """
    user = db.query(Usuario).filter(Usuario.stripe_customer_id == customer_id).first()
    if not user:
        print(f"⚠️ No se encontró usuario con customer_id {customer_id}")
        return
    
    user.is_premium = is_premium
    
    # 🆕 Guardar subscription_id
    if subscription_id:
        user.stripe_subscription_id = subscription_id
        print(f"✅ Subscription ID guardado: {subscription_id}")
    
    # 🆕 Detectar tipo de plan
    if is_premium and price_id:
        if price_id == PRICE_ID_ANUAL:
            user.plan_type = "PREMIUM_YEARLY"
        elif price_id == PRICE_ID_MENSUAL:
            user.plan_type = "PREMIUM_MONTHLY"
        else:
            user.plan_type = "PREMIUM_MONTHLY"  # Fallback
        print(f"✅ Plan type detectado: {user.plan_type}")
    else:
        user.plan_type = "FREE"
        user.stripe_subscription_id = None
    
    # Resetear usos gratuitos si downgrade
    if not is_premium:
        user.chat_uses_free = 2
    else:
        # Generar plan con IA para usuarios premium
        print(f"💎 Usuario {user.id} → {user.plan_type}, generando plan IA...")
        await generate_and_save_ai_plan(db, user.id)
    
    db.commit()
    print(f"✅ Usuario {user.id} actualizado a {user.plan_type}")

# ==========================================
# WEBHOOK ENDPOINT
# ==========================================
@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Webhook de Stripe para producción.
    Maneja eventos de suscripciones y pagos.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not endpoint_secret:
        raise HTTPException(status_code=500, detail="Stripe webhook secret no configurado")

    # Verificar firma del webhook
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        print(f"✅ Webhook verificado: {event['type']}")
    except ValueError:
        print("❌ Payload inválido")
        raise HTTPException(status_code=400, detail="Payload inválido")
    except stripe.error.SignatureVerificationError:
        print("❌ Firma inválida")
        raise HTTPException(status_code=400, detail="Firma webhook inválida")

    db = SessionLocal()
    try:
        etype = event["type"]
        obj = event["data"]["object"]

        # ==========================================
        # CHECKOUT COMPLETADO
        # ==========================================
        if etype == "checkout.session.completed":
            customer_id = obj.get("customer")
            email = (obj.get("customer_details") or {}).get("email")
            payment_status = obj.get("payment_status")
            subscription_id = obj.get("subscription")
            
            print(f"💳 Checkout completado: {email}, sub: {subscription_id}")
            
            if customer_id and email:
                set_customer_id_by_email(db, email, customer_id)
                
                # Si pago exitoso y hay suscripción, activar premium
                if payment_status == "paid" and subscription_id:
                    try:
                        subscription = stripe.Subscription.retrieve(subscription_id)
                        price_id = subscription.items.data[0].price.id if subscription.items.data else None
                        
                        await set_premium_by_customer(db, customer_id, True, subscription_id, price_id)
                    except Exception as e:
                        print(f"❌ Error obteniendo subscription: {e}")

        # ==========================================
        # SUSCRIPCIÓN CREADA/ACTUALIZADA
        # ==========================================
        elif etype in ("customer.subscription.created", "customer.subscription.updated"):
            status = obj.get("status")
            customer_id = obj.get("customer")
            subscription_id = obj.get("id")
            
            # 🆕 Obtener price_id
            price_id = None
            if obj.get("items") and obj["items"].get("data"):
                price_id = obj["items"]["data"][0]["price"]["id"]
            
            print(f"📋 Suscripción {etype}: {subscription_id}, status: {status}")
            
            if customer_id and status:
                is_active = status in ("active", "trialing")
                await set_premium_by_customer(db, customer_id, is_active, subscription_id, price_id)

        # ==========================================
        # SUSCRIPCIÓN CANCELADA
        # ==========================================
        elif etype == "customer.subscription.deleted":
            customer_id = obj.get("customer")
            subscription_id = obj.get("id")
            
            print(f"❌ Suscripción cancelada: {subscription_id}")
            
            if customer_id:
                await set_premium_by_customer(db, customer_id, False, None, None)

        # ==========================================
        # PAYMENT INTENT EXITOSO
        # ==========================================
        elif etype == "payment_intent.succeeded":
            print("=" * 50)
            print(f"💰 payment_intent.succeeded")
            print(f"📦 Payment Intent ID: {obj.get('id')}")
            print(f"📋 Metadata: {obj.get('metadata')}")
            print("=" * 50)
            
            metadata = obj.get('metadata', {})
            user_id = metadata.get('user_id')
            price_id = metadata.get('price_id')
            
            if user_id:
                try:
                    user_id = int(user_id)
                    user = db.query(Usuario).filter(Usuario.id == user_id).first()
                    
                    if user:
                        print(f"💎 Usuario encontrado! ID={user.id}, Email={user.email}")
                        
                        # 🆕 Detectar tipo de plan
                        if price_id == PRICE_ID_ANUAL:
                            plan_type = "PREMIUM_YEARLY"
                        else:
                            plan_type = "PREMIUM_MONTHLY"
                        
                        user.is_premium = True
                        user.plan_type = plan_type
                        user.chat_uses_free = 999
                        
                        customer_id = obj.get("customer")
                        if customer_id:
                            user.stripe_customer_id = customer_id
                        
                        db.commit()
                        print(f"✅ Usuario {user.id} actualizado a {plan_type}")
                        
                        # Generar plan con IA
                        await generate_and_save_ai_plan(db, user.id)
                        print(f"🎉 Plan generado exitosamente para usuario {user.id}")
                    else:
                        print(f"❌ No se encontró usuario con ID: {user_id}")
                except Exception as e:
                    print(f"❌ Error procesando payment_intent: {e}")
            else:
                print(f"❌ payment_intent sin user_id en metadata")
            
            print("=" * 50)

        return {"status": "ok"}
        
    except Exception as e:
        print(f"❌ Error procesando webhook: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()