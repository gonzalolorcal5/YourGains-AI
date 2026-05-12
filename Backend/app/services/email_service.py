import os
import resend
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

resend.api_key = os.getenv("RESEND_API_KEY", "")

REMITENTE = "YourGains AI <contacto@yourgains.ai>"
APP_URL = os.getenv("FRONTEND_URL", "https://yourgains.ai")


def _extraer_nombre(email: str) -> str:
    """Extrae el nombre del email con fallback a 'atleta'."""
    try:
        parte = email.split('@')[0]
        parte = parte.rstrip('0123456789')
        for sep in ['.', '-', '_']:
            if sep in parte:
                parte = parte.split(sep)[0]
                break
        nombre = parte.capitalize()
        if len(nombre) > 12 or len(nombre) < 3:
            return "atleta"
        return nombre
    except Exception:
        return "atleta"


def _send(to: str, subject: str, html: str) -> bool:
    """Wrapper de envío. Devuelve True si OK, False si error."""
    try:
        resend.Emails.send({
            "from": REMITENTE,
            "to": to,
            "subject": subject,
            "html": html,
        })
        return True
    except Exception as e:
        print(f"❌ [EMAIL] Error enviando a {to}: {e}")
        return False


def send_day1(email: str) -> bool:
    nombre = _extraer_nombre(email)
    subject = f"Bienvenido/a a YourGains, {nombre} 💪"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; 
                background: #0a0a0a; color: #e5e5e5; padding: 32px; border-radius: 12px;">
        <div style="text-align: center; margin-bottom: 28px;">
            <span style="font-size: 32px;">🏋️</span>
            <h1 style="color: #84cc16; font-size: 22px; margin: 8px 0;">YourGains AI</h1>
        </div>
        <p style="font-size: 16px; line-height: 1.6;">Hola {nombre},</p>
        <p style="font-size: 15px; line-height: 1.7; color: #d4d4d4;">
            Soy Gonzalo, creador de YourGains AI. Me alegra que estés aquí.
        </p>
        <p style="font-size: 15px; line-height: 1.7; color: #d4d4d4;">
            Tu plan personalizado ya está listo. Esto es lo que puedes hacer desde hoy:
        </p>
        <div style="background: #1a1a1a; border-radius: 10px; padding: 20px; margin: 20px 0;">
            <p style="margin: 8px 0; font-size: 15px;">1️⃣ <strong style="color: #84cc16;">Ve a tu rutina</strong> — empieza a entrenar</p>
            <p style="margin: 8px 0; font-size: 15px;">2️⃣ <strong style="color: #84cc16;">Registra tu primera serie</strong> — activa tu racha</p>
            <p style="margin: 8px 0; font-size: 15px;">3️⃣ <strong style="color: #84cc16;">Vuelve mañana</strong> — mantén la racha viva</p>
        </div>
        <div style="text-align: center; margin: 28px 0;">
            <a href="{APP_URL}/dashboard" 
               style="background: #84cc16; color: #000; text-decoration: none; 
                      padding: 14px 32px; border-radius: 25px; font-weight: 700; 
                      font-size: 15px; display: inline-block;">
                Ver mi rutina →
            </a>
        </div>
        <p style="font-size: 14px; color: #737373; margin-top: 28px;">
            Cualquier pregunta, responde a este email.<br><br>
            Gonzalo<br>
            <span style="color: #84cc16;">Fundador de YourGains AI</span>
        </p>
    </div>
    """
    return _send(email, subject, html)


def send_day3(email: str, tiene_entrenos: bool = False) -> bool:
    nombre = _extraer_nombre(email)
    subject = f"¿Cómo va el entreno, {nombre}? 🔥"
    if tiene_entrenos:
        cuerpo = f"""
        <p style="font-size: 15px; line-height: 1.7; color: #d4d4d4;">
            ¡Buen trabajo registrando tus primeros entrenamientos! Sigue así.
        </p>
        <p style="font-size: 15px; line-height: 1.7; color: #d4d4d4;">
            Recuerda: con YourGains puedes ver cómo evoluciona tu fuerza semana a semana.
            Cada serie que registras cuenta.
        </p>
        """
        cta_texto = "Ver mi progresión →"
    else:
        cuerpo = f"""
        <p style="font-size: 15px; line-height: 1.7; color: #d4d4d4;">
            Todavía no has registrado tu primer entreno. No pasa nada — 
            hoy es el día perfecto para empezar.
        </p>
        <p style="font-size: 15px; line-height: 1.7; color: #d4d4d4;">
            Solo tienes que abrir YourGains, ir a <strong style="color: #84cc16;">Entreno</strong> 
            y guardar una serie. Eso ya activa tu racha. 🔥
        </p>
        """
        cta_texto = "Registrar mi primer entreno →"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto;
                background: #0a0a0a; color: #e5e5e5; padding: 32px; border-radius: 12px;">
        <div style="text-align: center; margin-bottom: 28px;">
            <span style="font-size: 32px;">🔥</span>
            <h1 style="color: #84cc16; font-size: 22px; margin: 8px 0;">YourGains AI</h1>
        </div>
        <p style="font-size: 16px; line-height: 1.6;">Hola {nombre},</p>
        {cuerpo}
        <div style="text-align: center; margin: 28px 0;">
            <a href="{APP_URL}/dashboard"
               style="background: #84cc16; color: #000; text-decoration: none;
                      padding: 14px 32px; border-radius: 25px; font-weight: 700;
                      font-size: 15px; display: inline-block;">
                {cta_texto}
            </a>
        </div>
        <p style="font-size: 14px; color: #737373; margin-top: 28px;">
            Gonzalo<br>
            <span style="color: #84cc16;">Fundador de YourGains AI</span>
        </p>
    </div>
    """
    return _send(email, subject, html)


def send_day7(email: str, num_sesiones: int, racha_actual: int) -> bool:
    nombre = _extraer_nombre(email)
    subject = f"Tu primera semana en YourGains 💪"

    if num_sesiones > 0:
        stats_html = f"""
        <div style="background: #1a1a1a; border-radius: 10px; padding: 20px; margin: 20px 0;
                    display: flex; gap: 16px; text-align: center;">
            <div style="flex: 1;">
                <div style="font-size: 28px; font-weight: 800; color: #84cc16;">{num_sesiones}</div>
                <div style="font-size: 12px; color: #737373; text-transform: uppercase; 
                            letter-spacing: 0.5px;">entrenamientos</div>
            </div>
            <div style="flex: 1;">
                <div style="font-size: 28px; font-weight: 800; color: #84cc16;">{racha_actual} 🔥</div>
                <div style="font-size: 12px; color: #737373; text-transform: uppercase;
                            letter-spacing: 0.5px;">días de racha</div>
            </div>
        </div>
        <p style="font-size: 15px; line-height: 1.7; color: #d4d4d4;">
            Buen trabajo esta semana. Cada entreno que registras queda guardado — 
            cuando seas Premium podrás ver exactamente cómo evoluciona tu fuerza.
        </p>
        """
        cta_texto = "Ver mi dashboard →"
    else:
        stats_html = f"""
        <p style="font-size: 15px; line-height: 1.7; color: #d4d4d4;">
            Llevas una semana con YourGains pero todavía no has registrado ningún entreno.
            No te preocupes — el mejor momento para empezar es ahora.
        </p>
        <p style="font-size: 15px; line-height: 1.7; color: #d4d4d4;">
            Tu rutina personalizada te está esperando. 
            Empieza hoy y activa tu primera racha. 🔥
        </p>
        """
        cta_texto = "Empezar ahora →"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto;
                background: #0a0a0a; color: #e5e5e5; padding: 32px; border-radius: 12px;">
        <div style="text-align: center; margin-bottom: 28px;">
            <span style="font-size: 32px;">📊</span>
            <h1 style="color: #84cc16; font-size: 22px; margin: 8px 0;">YourGains AI</h1>
        </div>
        <p style="font-size: 16px; line-height: 1.6;">Hola {nombre},</p>
        <p style="font-size: 15px; line-height: 1.7; color: #d4d4d4;">
            Llevas una semana con YourGains.
        </p>
        {stats_html}
        <div style="text-align: center; margin: 28px 0;">
            <a href="{APP_URL}/dashboard"
               style="background: #84cc16; color: #000; text-decoration: none;
                      padding: 14px 32px; border-radius: 25px; font-weight: 700;
                      font-size: 15px; display: inline-block;">
                {cta_texto}
            </a>
        </div>
        <p style="font-size: 14px; color: #737373; margin-top: 28px;">
            Gonzalo<br>
            <span style="color: #84cc16;">Fundador de YourGains AI</span>
        </p>
    </div>
    """
    return _send(email, subject, html)


def send_day18(email: str, num_sesiones: int, mejor_racha: int,
               ejercicio_top: str = None, peso_inicial: float = None,
               peso_actual: float = None) -> bool:
    nombre = _extraer_nombre(email)
    subject = f"{nombre}, tu progreso de estas semanas 📈"

    progresion_html = ""
    if ejercicio_top and peso_inicial and peso_actual and peso_actual > peso_inicial:
        progresion_html = f"""
        <div style="background: rgba(132,204,22,0.08); border: 1px solid rgba(132,204,22,0.2);
                    border-radius: 10px; padding: 16px; margin: 8px 0;">
            <div style="font-size: 13px; color: #84cc16; font-weight: 700; margin-bottom: 4px;">
                💪 {ejercicio_top}
            </div>
            <div style="font-size: 14px; color: #d4d4d4;">
                {peso_inicial}kg → <strong style="color: #84cc16;">{peso_actual}kg</strong>
                <span style="color: #84cc16; font-size: 13px;">
                    (+{round(peso_actual - peso_inicial, 1)}kg)
                </span>
            </div>
        </div>
        """

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto;
                background: #0a0a0a; color: #e5e5e5; padding: 32px; border-radius: 12px;">
        <div style="text-align: center; margin-bottom: 28px;">
            <span style="font-size: 32px;">📈</span>
            <h1 style="color: #84cc16; font-size: 22px; margin: 8px 0;">YourGains AI</h1>
        </div>
        <p style="font-size: 16px; line-height: 1.6;">Hola {nombre},</p>
        <p style="font-size: 15px; line-height: 1.7; color: #d4d4d4;">
            Llevas 18 días en YourGains. Estos son tus números:
        </p>
        <div style="background: #1a1a1a; border-radius: 10px; padding: 20px; margin: 20px 0;">
            <p style="margin: 8px 0; font-size: 15px;">
                🏋️ <strong style="color: #84cc16;">{num_sesiones} entrenamientos</strong> registrados
            </p>
            <p style="margin: 8px 0; font-size: 15px;">
                🔥 Mejor racha: <strong style="color: #84cc16;">{mejor_racha} días</strong>
            </p>
            {progresion_html}
        </div>
        <p style="font-size: 15px; line-height: 1.7; color: #d4d4d4;">
            Todos tus datos de progresión están guardados. Hazte Premium para ver 
            cómo evoluciona tu fuerza semana a semana con gráficas detalladas.
        </p>
        <div style="text-align: center; margin: 28px 0;">
            <a href="{APP_URL}/tarifas.html"
               style="background: #84cc16; color: #000; text-decoration: none;
                      padding: 14px 32px; border-radius: 25px; font-weight: 700;
                      font-size: 15px; display: inline-block;">
                Ver mi progresión completa →
            </a>
        </div>
        <p style="font-size: 14px; color: #737373; margin-top: 28px;">
            Gonzalo<br>
            <span style="color: #84cc16;">Fundador de YourGains AI</span>
        </p>
    </div>
    """
    return _send(email, subject, html)


def check_and_send_emails(db: Session):
    """
    Ejecutado diariamente por el scheduler.
    Recorre todos los usuarios y envía los emails que correspondan.
    """
    from app.models import Usuario, Plan, EntrenamientoSession, EntrenamientoSet

    ahora = datetime.utcnow()

    # Usuarios con plan (onboarding completado) y emails pendientes
    usuarios = db.query(Usuario).join(
        Plan, Plan.user_id == Usuario.id
    ).filter(
        Plan.fecha_creacion.isnot(None)
    ).all()

    enviados = 0

    for user in usuarios:
        try:
            # Calcular días desde que completó el onboarding
            plan = db.query(Plan).filter(Plan.user_id == user.id).first()
            if not plan or not plan.fecha_creacion:
                continue

            dias = (ahora - plan.fecha_creacion).days

            # Contar sesiones del usuario
            num_sesiones = db.query(EntrenamientoSession).filter(
                EntrenamientoSession.user_id == user.id
            ).count()

            # ── EMAIL DÍA 1 ──────────────────────────
            if dias >= 1 and not user.email_day1_sent:
                if send_day1(user.email):
                    user.email_day1_sent = True
                    enviados += 1
                    print(f"✅ [EMAIL] Día 1 enviado a {user.email}")

            # ── EMAIL DÍA 3 ──────────────────────────
            elif dias >= 3 and not user.email_day3_sent:
                tiene_entrenos = num_sesiones > 0
                if send_day3(user.email, tiene_entrenos):
                    user.email_day3_sent = True
                    enviados += 1
                    print(f"✅ [EMAIL] Día 3 enviado a {user.email}")

            # ── EMAIL DÍA 7 ──────────────────────────
            elif dias >= 7 and not user.email_day7_sent:
                racha = getattr(user, 'racha_actual', 0) or 0
                if send_day7(user.email, num_sesiones, racha):
                    user.email_day7_sent = True
                    enviados += 1
                    print(f"✅ [EMAIL] Día 7 enviado a {user.email}")

            # ── EMAIL DÍA 18 ─────────────────────────
            elif dias >= 18 and not user.email_day18_sent:
                # No enviar a usuarios ya Premium
                if user.is_premium or user.plan_type in ("PREMIUM_MONTHLY", "PREMIUM_YEARLY"):
                    user.email_day18_sent = True  # Marcar como enviado para no procesarlo más
                    continue

                mejor_racha = getattr(user, 'mejor_racha', 0) or 0

                # Buscar ejercicio con mayor progresión
                ejercicio_top = None
                peso_inicial = None
                peso_actual = None

                try:
                    sets = db.query(
                        EntrenamientoSet.ejercicio_nombre,
                        func.min(EntrenamientoSet.peso).label("peso_min"),
                        func.max(EntrenamientoSet.peso).label("peso_max")
                    ).join(
                        EntrenamientoSession,
                        EntrenamientoSet.session_id == EntrenamientoSession.id
                    ).filter(
                        EntrenamientoSession.user_id == user.id,
                        EntrenamientoSet.peso.isnot(None),
                        EntrenamientoSet.peso > 0
                    ).group_by(
                        EntrenamientoSet.ejercicio_nombre
                    ).all()

                    if sets:
                        mejor = max(sets, key=lambda x: (x.peso_max or 0) - (x.peso_min or 0))
                        if mejor.peso_max and mejor.peso_min and mejor.peso_max > mejor.peso_min:
                            ejercicio_top = mejor.ejercicio_nombre
                            peso_inicial = mejor.peso_min
                            peso_actual = mejor.peso_max
                except Exception as e:
                    print(f"⚠️ [EMAIL] Error calculando progresión para {user.email}: {e}")

                if send_day18(user.email, num_sesiones, mejor_racha,
                              ejercicio_top, peso_inicial, peso_actual):
                    user.email_day18_sent = True
                    enviados += 1
                    print(f"✅ [EMAIL] Día 18 enviado a {user.email}")

        except Exception as e:
            print(f"❌ [EMAIL] Error procesando usuario {user.email}: {e}")
            continue

    db.commit()
    print(f"✅ [EMAIL] Check completado — {enviados} emails enviados")
