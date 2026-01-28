from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import stripe
import os
import json
import asyncio
from dotenv import load_dotenv

from app.database import SessionLocal
from app.models import Usuario, ProcessedWebhookEvent
from app.utils.gpt import generar_plan_personalizado

router = APIRouter()
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

# Price IDs para detectar tipo de plan
PRICE_ID_MENSUAL = os.getenv("STRIPE_PRICE_MENSUAL")
PRICE_ID_ANUAL = os.getenv("STRIPE_PRICE_ANUAL")

# Tipos de evento que procesamos (idempotencia por event_id)
WEBHOOK_HANDLED_TYPES = (
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "payment_intent.succeeded",
)


def _is_webhook_event_processed(db: Session, event_id: str) -> bool:
    """Comprueba si ya procesamos este evento (idempotencia frente a retries de Stripe)."""
    return db.query(ProcessedWebhookEvent).filter(
        ProcessedWebhookEvent.stripe_event_id == event_id
    ).first() is not None


def _mark_webhook_event_processed(db: Session, event_id: str) -> None:
    """Marca el evento como procesado. Ignora si ya existe (unique)."""
    try:
        db.add(ProcessedWebhookEvent(stripe_event_id=event_id))
        db.commit()
    except IntegrityError:
        db.rollback()
        # Ya procesado (duplicado) → idempotente, ok


def _user_has_premium_generated_plan(user: Usuario) -> bool:
    """True si el usuario ya tiene plan generado por IA (is_premium_generated en rutina)."""
    r = (user.current_routine or "").strip()
    if not r or r == "{}":
        return False
    return "is_premium_generated" in r

# ==========================================
# GENERACIÓN DE PLAN CON IA
# ==========================================
# Exportada para uso en stripe_routes.py
async def generate_and_save_ai_plan(db: Session, user_id: int, force: bool = False):
    """
    Genera plan personalizado con IA para usuario premium.
    Incluye protecciones contra duplicados y race conditions (lock + idempotencia).

    Args:
        force: Si True, fuerza regeneración aunque ya exista rutina (upgrade FREE→PREMIUM).
    """
    user = None
    lock_acquired = False

    print(f"\n{'='*60}")
    print(f"INICIANDO GENERACION DE PLAN PARA USER_ID: {user_id} (force={force})")
    print(f"{'='*60}")

    try:
        # ------------------------------------------------------------------
        # PASO 1: Verificar que el usuario existe
        # ------------------------------------------------------------------
        user = db.query(Usuario).filter(Usuario.id == user_id).first()
        if not user:
            print(f"[PASO 1] Usuario {user_id} no encontrado en BD")
            return False
        print(f"[PASO 1] Usuario encontrado: {user.email}")

        # ------------------------------------------------------------------
        # PASO 2: Lock / plan existente — evitar duplicados y concurrencia
        # ------------------------------------------------------------------
        if user.is_generating_plan:
            print(f"[PASO 2] Lock activo: ya se esta generando plan para user_id {user_id}. Esperando...")
            await asyncio.sleep(2)
            db.refresh(user)

            if not force and user.current_routine and user.current_routine != '{}' and \
               user.current_diet and user.current_diet != '{}':
                print(f"[PASO 2] Plan ya generado por otra llamada para user_id {user_id}. Skipping.")
                return True

            max_wait_attempts = 2
            for attempt in range(max_wait_attempts):
                await asyncio.sleep(2)
                db.refresh(user)
                if not user.is_generating_plan:
                    if not force and user.current_routine and user.current_routine != '{}' and \
                       user.current_diet and user.current_diet != '{}':
                        print(f"[PASO 2] Plan ya generado (lock liberado) para user_id {user_id}. Skipping.")
                        return True
                    print(f"[PASO 2] Lock liberado sin plan, procediendo a generar para user_id {user_id}")
                    break
                if not force and user.current_routine and user.current_routine != '{}' and \
                   user.current_diet and user.current_diet != '{}':
                    print(f"[PASO 2] Plan generado durante la espera para user_id {user_id}. Skipping.")
                    return True

            if user.is_generating_plan:
                print(f"[PASO 2] Lock aun activo tras espera para user_id {user_id}. Continuando...")
                if not force and user.current_routine and user.current_routine != '{}' and \
                   user.current_diet and user.current_diet != '{}':
                    print(f"[PASO 2] Plan encontrado antes de forzar. Skipping.")
                    return True

        db.refresh(user)
        if not force and user.current_routine and user.current_routine != '{}' and \
           user.current_diet and user.current_diet != '{}':
            print(f"[PASO 2] Plan ya existe antes de adquirir lock para user_id {user_id}. Skipping.")
            return True

        # ------------------------------------------------------------------
        # PASO 3: Adquirir lock
        # ------------------------------------------------------------------
        user.is_generating_plan = True
        db.commit()
        lock_acquired = True
        print(f"[PASO 3] Lock de generacion activado para user_id {user_id}")

        db.refresh(user)

        # ------------------------------------------------------------------
        # PASO 4: Datos de onboarding y generacion con IA
        # ------------------------------------------------------------------
        from app.models import Plan
        plan_data = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.id.desc()).first()

        if not plan_data:
            print(f"[PASO 4] No hay datos de onboarding para user_id {user_id}. Usuario debe completar onboarding.")
            return False

        # Preparar datos del usuario desde el onboarding
        # Intentar obtener training_days y training_frequency desde el plan si existen
        training_days = ['lunes', 'martes', 'jueves', 'viernes']  # Default
        training_frequency = 4  # Default
        
        # Intentar leer desde rutina del plan si existe
        if plan_data.rutina:
            try:
                import json
                rutina_json = json.loads(plan_data.rutina)
                if isinstance(rutina_json, dict):
                    if 'metadata' in rutina_json:
                        metadata = rutina_json['metadata']
                        if 'training_days' in metadata:
                            training_days = metadata['training_days']
                        if 'training_frequency' in metadata:
                            training_frequency = metadata['training_frequency']
                    # También intentar desde la estructura de días
                    elif 'dias' in rutina_json:
                        training_days = [dia.get('dia', '').lower() for dia in rutina_json['dias'] if dia.get('dia')]
            except Exception as e:
                print(f"⚠️ No se pudieron leer training_days desde plan: {e}")
        
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
            'training_frequency': training_frequency,
            'training_days': training_days
        }
        
        print(f"[PASO 4] Generando plan con IA para user_id {user_id}...")

        plan = await generar_plan_personalizado(user_info)
        
        from datetime import datetime
        
        # Guardar directamente la estructura rica de GPT sin transformaciones destructivas
        rutina_json = plan["rutina"]
        dieta_json = plan["dieta"]
        
        # Asegurar metadatos de versión y timestamp
        if isinstance(rutina_json, dict):
            rutina_json["updated_at"] = datetime.utcnow().isoformat()
            rutina_json["is_premium_generated"] = True
            # Asegurar que versión sea string
            if "version" not in rutina_json:
                rutina_json["version"] = "2.0.0"
        
        # ==========================================
        # AÑADIR total_kcal EN NIVEL RAIZ (Compatibilidad Logs y Frontend)
        # ==========================================
        if isinstance(dieta_json, dict) and "macros" in dieta_json:
            macros = dieta_json.get("macros", {})
            if isinstance(macros, dict):
                # Extraer total_kcal desde macros si no existe en nivel raíz
                if "total_kcal" not in dieta_json:
                    total_kcal_value = macros.get("total_kcal") or macros.get("calorias") or 0
                    if total_kcal_value:
                        dieta_json["total_kcal"] = int(total_kcal_value)
                        print(f"✅ total_kcal añadido en nivel raíz: {dieta_json['total_kcal']} kcal")
                else:
                    # Si ya existe, verificar que sea consistente con macros
                    existing_total_kcal = dieta_json.get("total_kcal", 0)
                    macros_total_kcal = macros.get("total_kcal") or macros.get("calorias") or 0
                    if macros_total_kcal and existing_total_kcal != macros_total_kcal:
                        # Actualizar para mantener consistencia
                        dieta_json["total_kcal"] = int(macros_total_kcal)
                        print(f"🔄 total_kcal actualizado en nivel raíz para consistencia: {dieta_json['total_kcal']} kcal")
        
        # Serializar y guardar en el usuario
        user.current_routine = json.dumps(rutina_json, ensure_ascii=False)
        user.current_diet = json.dumps(dieta_json, ensure_ascii=False)
        
        # Actualizar historial (objeto Plan) también
        if plan_data:
            plan_data.rutina = user.current_routine
            plan_data.dieta = user.current_diet
            # También guardar la motivación si existe
            if "motivacion" in plan:
                plan_data.motivacion = json.dumps(plan["motivacion"], ensure_ascii=False) if isinstance(plan["motivacion"], (dict, list)) else plan["motivacion"]
        
        db.commit()

        _dias = rutina_json.get("dias") if isinstance(rutina_json, dict) else None
        _comidas = dieta_json.get("comidas") if isinstance(dieta_json, dict) else None
        n_dias = len(_dias) if isinstance(_dias, list) else 0
        n_comidas = len(_comidas) if isinstance(_comidas, list) else 0
        print(f"\n{'='*60}")
        print(f"PLAN GENERADO EXITOSAMENTE PARA USER_ID: {user_id}")
        print(f"   Dias de rutina: {n_dias} | Comidas: {n_comidas}")
        print(f"{'='*60}\n")

        return True

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"ERROR CRITICO EN GENERACION DE PLAN")
        print(f"   User ID: {user_id}")
        print(f"   Error: {e}")
        print(f"{'='*60}")
        import traceback
        traceback.print_exc()

        # Cleanup: liberar lock si quedo activo (p. ej. crash antes de lock_acquired=True)
        try:
            u = db.query(Usuario).filter(Usuario.id == user_id).first()
            if u and u.is_generating_plan:
                print(f"[CLEANUP] Liberando lock tras error para user_id {user_id}...")
                u.is_generating_plan = False
                db.commit()
                print(f"[CLEANUP] Lock liberado correctamente")
        except Exception as cleanup_err:
            print(f"[CLEANUP] Error liberando lock: {cleanup_err}")
            try:
                db.rollback()
            except Exception:
                pass

        return False

    finally:
        # PASO 5: Liberar lock SIEMPRE (exito o error)
        if lock_acquired and user:
            try:
                db.refresh(user)
                user.is_generating_plan = False
                db.commit()
                print(f"[PASO 5] Lock liberado para user_id {user_id}")
            except Exception as e1:
                print(f"[PASO 5] Error liberando lock: {e1}")
                try:
                    db.rollback()
                    db.refresh(user)
                    user.is_generating_plan = False
                    db.commit()
                    print(f"[PASO 5] Lock liberado (reintento) para user_id {user_id}")
                except Exception as e2:
                    print(f"[PASO 5] Error critico liberando lock: {e2}")
                    try:
                        db.rollback()
                    except Exception:
                        pass

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
    price_id: str = None,
    generate_plan: bool = False
):
    """
    Actualiza estado premium del usuario.
    🆕 Detecta PREMIUM_MONTHLY vs PREMIUM_YEARLY según price_id.
    🆕 Guarda stripe_subscription_id SIEMPRE que esté disponible.
    
    Args:
        generate_plan: Si es True, genera el plan con IA. Por defecto False para evitar duplicados.
    """
    user = db.query(Usuario).filter(Usuario.stripe_customer_id == customer_id).first()
    if not user:
        print(f"⚠️ No se encontró usuario con customer_id {customer_id}")
        return
    
    user.is_premium = is_premium
    
    # 🆕 Guardar subscription_id SIEMPRE
    if subscription_id:
        user.stripe_subscription_id = subscription_id
        print(f"✅ Subscription ID guardado: {subscription_id}")
    elif is_premium and not user.stripe_subscription_id:
        # Si es premium pero no tiene subscription_id, intentar obtenerlo
        print(f"⚠️ Usuario premium sin subscription_id, consultando Stripe...")
        try:
            subscriptions = stripe.Subscription.list(
                customer=customer_id,
                limit=1,
                status='active'
            )
            if subscriptions.data:
                user.stripe_subscription_id = subscriptions.data[0].id
                print(f"✅ Subscription ID recuperado: {user.stripe_subscription_id}")
        except Exception as e:
            print(f"⚠️ No se pudo obtener subscription_id: {e}")
    
    # 🆕 Detectar tipo de plan SIEMPRE que is_premium=True
    if is_premium:
        if price_id == PRICE_ID_ANUAL:
            user.plan_type = "PREMIUM_YEARLY"
        elif price_id == PRICE_ID_MENSUAL:
            user.plan_type = "PREMIUM_MONTHLY"
        elif price_id:
            # Fallback: Si hay price_id pero no coincide
            user.plan_type = "PREMIUM_MONTHLY"
        else:
            # Sin price_id: intentar inferir desde subscription
            if user.stripe_subscription_id:
                try:
                    sub = stripe.Subscription.retrieve(
                        user.stripe_subscription_id,
                        expand=['items.data.price']
                    )
                    # Acceso compatible v12+
                    items_data = sub.get('items', {}).get('data', [])
                    if items_data and len(items_data) > 0:
                        price_id_from_sub = items_data[0].get('price', {}).get('id')
                        if price_id_from_sub == PRICE_ID_ANUAL:
                            user.plan_type = "PREMIUM_YEARLY"
                        else:
                            user.plan_type = "PREMIUM_MONTHLY"
                    else:
                        user.plan_type = "PREMIUM_MONTHLY"
                    print(f"✅ Plan type inferido: {user.plan_type}")
                except Exception as e:
                    print(f"⚠️ Error inferiendo plan: {e}")
                    user.plan_type = "PREMIUM_MONTHLY"
            else:
                user.plan_type = "PREMIUM_MONTHLY"
        
        print(f"✅ Plan type establecido: {user.plan_type}")
    else:
        user.plan_type = "FREE"
        user.stripe_subscription_id = None
        print(f"✅ Usuario downgradeado a FREE")
    
    # Resetear usos gratuitos si downgrade
    if not is_premium:
        user.chat_uses_free = 2
    
    # ⚠️ IMPORTANTE: Solo generar plan si se solicita explícitamente
    # Esto evita generación duplicada cuando se llama desde múltiples eventos
    if is_premium and generate_plan:
        print(f"💎 Usuario {user.id} → {user.plan_type}, generando plan IA (forzado)...")
        plan_generated = await generate_and_save_ai_plan(db, user.id, force=True)
        if plan_generated:
            print(f"✅ Plan generado exitosamente para usuario {user.id}")
        else:
            print(f"⚠️ No se pudo generar plan para usuario {user.id}, pero el usuario es premium")
    
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
        event_id = event.get("id") or ""

        # 🛡️ IDEMPOTENCIA: Evitar procesar el mismo evento dos veces (retries de Stripe)
        if event_id and etype in WEBHOOK_HANDLED_TYPES and _is_webhook_event_processed(db, event_id):
            print(f"⏭️ Evento {event_id} ya procesado (idempotencia), skipping")
            return {"status": "ok"}

        # ==========================================
        # CHECKOUT COMPLETADO
        # ==========================================
        if etype == "checkout.session.completed":
            customer_id = obj.get("customer")
            email = (obj.get("customer_details") or {}).get("email")
            payment_status = obj.get("payment_status")
            subscription_id = obj.get("subscription")
            
            print(f"💳 Checkout completado:")
            print(f"   customer_id: {customer_id}")
            print(f"   email: {email}")
            print(f"   payment_status: {payment_status}")
            print(f"   subscription_id: {subscription_id}")
            
            if customer_id and email:
                set_customer_id_by_email(db, email, customer_id)
                
                # Si pago exitoso y hay suscripción, activar premium
                if payment_status == "paid" and subscription_id:
                    try:
                        # Expandir items para obtener price_id
                        subscription = stripe.Subscription.retrieve(
                            subscription_id,
                            expand=['items.data.price']
                        )
                        
                        # Obtener price_id de forma robusta (compatible v12+)
                        price_id = None
                        try:
                            items_data = subscription.get('items', {}).get('data', [])
                            if items_data and len(items_data) > 0:
                                price_id = items_data[0].get('price', {}).get('id')
                        except Exception as e:
                            print(f"⚠️ Error obteniendo price_id: {e}")
                        
                        print(f"💎 Activando premium:")
                        print(f"   customer_id: {customer_id}")
                        print(f"   subscription_id: {subscription_id}")
                        print(f"   price_id: {price_id}")
                        print(f"   status: {subscription.get('status', 'unknown')}")
                        
                        # Actualizar estado premium SIN generar plan (evitar duplicados)
                        await set_premium_by_customer(
                            db,
                            customer_id,
                            True,
                            subscription_id,
                            price_id,
                            generate_plan=False,
                        )

                        # 🔥 GENERAR PLAN UNA SOLA VEZ — triple protección frente a duplicados por retries
                        # 1) Idempotencia por event_id (arriba): mismo evento → skip completo.
                        # 2) Plan ya generado (is_premium_generated): skip generación.
                        # 3) Lock is_generating_plan: otra request generando → skip. Lock se libera en finally.
                        user = db.query(Usuario).filter(Usuario.stripe_customer_id == customer_id).first()
                        if user:
                            # 🛡️ PROTECCIÓN 1: Ya existe plan generado por IA para este usuario
                            if _user_has_premium_generated_plan(user):
                                print(f"⚠️ Plan ya existe para user_id {user.id}, skipping generation")
                            # 🛡️ PROTECCIÓN 2: Lock activo — otra request ya está generando
                            elif user.is_generating_plan:
                                print(f"⚠️ Ya se está generando plan para user_id {user.id}, skipping")
                            else:
                                try:
                                    print(f"💎 Generando plan con IA para usuario {user.id} (checkout.session.completed)...")
                                    plan_generated = await generate_and_save_ai_plan(db, user.id, force=True)
                                    if plan_generated:
                                        print(f"✅ Plan generado exitosamente para usuario {user.id}")
                                    else:
                                        print(f"⚠️ No se pudo generar plan para usuario {user.id}, pero el usuario es premium")
                                except Exception as gen_err:
                                    print(f"❌ Error generando plan para user_id {user.id}: {gen_err}")
                                    import traceback
                                    traceback.print_exc()
                                    # Lock se libera en finally de generate_and_save_ai_plan
                                    # Re-raise para devolver 500: no marcamos evento → Stripe reintenta
                                    raise

                        print(f"✅ Premium activado correctamente")
                        
                    except Exception as e:
                        print(f"❌ Error procesando subscription: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"⚠️ Condiciones no cumplidas:")
                    print(f"   payment_status: {payment_status}")
                    print(f"   subscription_id: {subscription_id}")

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
                # ⚠️ IMPORTANTE: Si es "created", NO generar plan aquí porque checkout.session.completed lo hará
                # Solo actualizar estado premium sin generar plan para evitar duplicados
                if etype == "customer.subscription.created":
                    # Solo actualizar estado, el plan se generará en checkout.session.completed
                    await set_premium_by_customer(
                        db, 
                        customer_id, 
                        is_active, 
                        subscription_id, 
                        price_id,
                        generate_plan=False  # NO generar plan aquí
                    )
                    print(f"✅ Estado premium actualizado (plan se generará en checkout.session.completed)")
                else:
                    # Para "updated", usar función normal sin generar plan (solo actualizar estado)
                    await set_premium_by_customer(
                        db, 
                        customer_id, 
                        is_active, 
                        subscription_id, 
                        price_id,
                        generate_plan=False  # NO generar plan en updates
                    )

        # ==========================================
        # SUSCRIPCIÓN CANCELADA
        # ==========================================
        elif etype == "customer.subscription.deleted":
            customer_id = obj.get("customer")
            subscription_id = obj.get("id")
            
            print(f"❌ Suscripción cancelada: {subscription_id}")
            
            if customer_id:
                await set_premium_by_customer(db, customer_id, False, None, None, generate_plan=False)

        # ==========================================
        # PAYMENT INTENT EXITOSO
        # ==========================================
        elif etype == "payment_intent.succeeded":
            print("=" * 50)
            print("⚠️ ADVERTENCIA: payment_intent.succeeded NO debe usarse para suscripciones")
            print("⚠️ Este evento solo debe procesarse en modo de desarrollo o pagos únicos")
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
                        
                        # Generar plan con IA (forzado porque es un pago)
                        await generate_and_save_ai_plan(db, user.id, force=True)
                        print(f"🎉 Plan generado exitosamente para usuario {user.id}")
                    else:
                        print(f"❌ No se encontró usuario con ID: {user_id}")
                except Exception as e:
                    print(f"❌ Error procesando payment_intent: {e}")
            else:
                print(f"❌ payment_intent sin user_id en metadata")
            
            print("=" * 50)

        # 🛡️ Marcar evento como procesado (idempotencia para retries)
        if event_id and etype in WEBHOOK_HANDLED_TYPES:
            _mark_webhook_event_processed(db, event_id)

        return {"status": "ok"}
        
    except Exception as e:
        print(f"❌ Error procesando webhook: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()