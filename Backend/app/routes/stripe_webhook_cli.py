"""
Webhook de Stripe CLI para testing local
Endpoint: /stripe/webhook
"""
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
import stripe
import os
import json
from dotenv import load_dotenv

from app.database import SessionLocal
from app.models import Usuario, Plan
from app.utils.gpt import generar_plan_personalizado

router = APIRouter()

# Cargar .env
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

async def generate_and_save_ai_plan(db: Session, user_id: int):
    """
    Asciende el plan existente (template FREE) a plan personalizado con IA.
    NUNCA crea un nuevo Plan: solo busca el plan del usuario en tabla planes
    y actualiza rutina/dieta. Si no hay plan, retorna sin crear (usuario debe completar onboarding).
    """
    try:
        user = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not user:
            print(f"❌ Usuario {user_id} no encontrado")
            return
        
        # Plan existente (el que rellenó siendo FREE) — no se crea uno nuevo
        plan_data = db.query(Plan).filter(Plan.user_id == user_id).first()
        if not plan_data:
            print(f"❌ No hay plan en tabla planes para usuario {user_id}. Debe completar onboarding.")
            return
        
        # Preparar datos del usuario
        user_info = {
            'altura': plan_data.altura or 175,
            'peso': float(plan_data.peso) if plan_data.peso else 75.0,
            'edad': plan_data.edad or 25,
            'sexo': plan_data.sexo or 'masculino',
            'objetivo': plan_data.objetivo or 'ganar_musculo',
            'experiencia': plan_data.experiencia or 'principiante',
            'materiales': plan_data.materiales or 'gym_completo',
            'tipo_cuerpo': plan_data.tipo_cuerpo or 'mesomorfo',
            'alergias': plan_data.alergias or 'Ninguna',
            'restricciones': plan_data.restricciones_dieta or 'Ninguna',
            'lesiones': plan_data.lesiones or 'Ninguna'
        }
        
        print(f"🤖 Generando plan con IA para usuario {user_id}...")
        print(f"📋 Datos: {user_info['sexo']}, {user_info['edad']} años, {user_info['altura']}cm, {user_info['peso']}kg")
        
        # Generar plan con GPT usando la función existente - AÑADIR await
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
        
        current_diet = {
            "meals": plan["dieta"].get("comidas", []),
            "total_kcal": plan["dieta"].get("total_calorias", 2200),
            "macros": macros_plan,  # ✅ Usar macros del plan generado en lugar de {}
            "objetivo": user_info['objetivo'],
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
        
        # Guardar en DB
        user.current_routine = json.dumps(current_routine, ensure_ascii=False)
        user.current_diet = json.dumps(current_diet, ensure_ascii=False)
        
        # Actualizar plan existente (ascender template → IA), sin db.add(Plan)
        plan_data.rutina = json.dumps(plan["rutina"], ensure_ascii=False)
        plan_data.dieta = json.dumps(plan["dieta"], ensure_ascii=False)
        
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
        print(f"🔗 Customer ID {customer_id} asociado al email {email}")

async def set_premium_by_customer(db: Session, customer_id: str, is_premium: bool):
    user = db.query(Usuario).filter(Usuario.stripe_customer_id == customer_id).first()
    if user:
        user.is_premium = is_premium
        user.plan_type = "PREMIUM" if is_premium else "FREE"
        if not is_premium:
            user.chat_uses_free = 2
        else:
            print(f"💎 Usuario {user.id} se hizo PREMIUM, generando plan con IA...")
            await generate_and_save_ai_plan(db, user.id)
        
        db.commit()
        print(f"✅ Usuario {user.id} actualizado a {'PREMIUM' if is_premium else 'FREE'}")

@router.post("/webhook")
async def stripe_webhook_cli(request: Request):
    """
    Webhook endpoint para Stripe CLI testing
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    print(f"\n🔔 WEBHOOK RECIBIDO:")
    print(f"   Payload size: {len(payload)} bytes")
    print(f"   Signature header: {sig_header[:20] if sig_header else 'None'}...")
    
    if not endpoint_secret:
        print("❌ STRIPE_WEBHOOK_SECRET no configurado")
        raise HTTPException(status_code=500, detail="Stripe webhook secret no configurado")

    try:
        # Validar firma del webhook
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        print(f"✅ Firma válida")
    except ValueError as e:
        print(f"❌ Payload inválido: {e}")
        raise HTTPException(status_code=400, detail="Payload inválido")
    except stripe.error.SignatureVerificationError as e:
        print(f"❌ Firma inválida: {e}")
        raise HTTPException(status_code=400, detail="Firma webhook inválida")

    # Mostrar datos del evento
    print(f"\n📊 DATOS DEL EVENTO:")
    print(f"   Tipo: {event['type']}")
    print(f"   ID: {event['id']}")
    print(f"   Creado: {event['created']}")
    
    obj = event["data"]["object"]
    print(f"   Objeto ID: {obj.get('id', 'N/A')}")
    
    db = SessionLocal()
    try:
        etype = event["type"]
        
        # Al completar el checkout asociamos el customer al email
        if etype == "checkout.session.completed":
            customer_id = obj.get("customer")
            email = (obj.get("customer_details") or {}).get("email")
            payment_status = obj.get("payment_status")
            
            print(f"\n💳 CHECKOUT COMPLETADO:")
            print(f"   Customer ID: {customer_id}")
            print(f"   Email: {email}")
            print(f"   Payment Status: {payment_status}")
            
            if customer_id and email:
                set_customer_id_by_email(db, email, customer_id)
                
                # Si el pago es exitoso, activar premium inmediatamente
                if payment_status == "paid":
                    print(f"💰 Pago confirmado para {email}, activando premium...")
                    await set_premium_by_customer(db, customer_id, True)

        # Suscripción creada/actualizada → premium si status activo o trial
        elif etype in ("customer.subscription.created", "customer.subscription.updated"):
            status = obj.get("status")
            customer_id = obj.get("customer")
            
            print(f"\n📋 SUSCRIPCIÓN ACTUALIZADA:")
            print(f"   Status: {status}")
            print(f"   Customer ID: {customer_id}")
            
            if customer_id and status:
                await set_premium_by_customer(db, customer_id, status in ("active", "trialing"))

        # Suscripción cancelada → premium = False
        elif etype == "customer.subscription.deleted":
            customer_id = obj.get("customer")
            
            print(f"\n❌ SUSCRIPCIÓN CANCELADA:")
            print(f"   Customer ID: {customer_id}")
            
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

        print(f"\n✅ Webhook procesado exitosamente")
        return {"status": "ok", "event_type": etype}
        
    except Exception as e:
        print(f"❌ Error procesando webhook: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
    finally:
        db.close()

@router.get("/webhook/test")
async def test_webhook():
    """
    Endpoint de prueba para verificar que el webhook está funcionando
    """
    return {
        "status": "ok",
        "message": "Webhook endpoint funcionando",
        "endpoint_secret_configured": bool(endpoint_secret),
        "stripe_api_key_configured": bool(stripe.api_key)
    }
