# 🚂 CONFIGURACIÓN DE VARIABLES DE ENTORNO EN RAILWAY

## 📋 Variables Requeridas

### 1. DATABASE_URL (CRÍTICO)

**✅ CORRECTO:**
```
DATABASE_URL = ${{Postgres.DATABASE_URL}}
```

**❌ INCORRECTO:**
```
DATABASE_URL = postgresql://user:pass@host:5432/dbname
DATABASE_URL = sqlite:///./gymai.db
```

**¿Por qué usar `${{Postgres.DATABASE_URL}}`?**
- Railway resuelve automáticamente esta referencia al servicio PostgreSQL
- Si cambias la base de datos, Railway actualiza la URL automáticamente
- Evita tener que copiar/pegar URLs manualmente
- Es la forma recomendada por Railway

**Cómo configurarlo:**
1. Ve a tu proyecto en Railway
2. Settings → Variables
3. Añade o edita `DATABASE_URL`
4. Valor: `${{Postgres.DATABASE_URL}}`
5. Guarda y reinicia el servicio

---

### 2. STRIPE_SECRET_KEY

```
STRIPE_SECRET_KEY = sk_live_xxxxxxxxxxxxx
```

O para testing:
```
STRIPE_SECRET_KEY = sk_test_xxxxxxxxxxxxx
```

**Dónde obtenerla:**
- Dashboard de Stripe → Developers → API keys
- https://dashboard.stripe.com/apikeys

---

### 3. STRIPE_PUBLISHABLE_KEY

```
STRIPE_PUBLISHABLE_KEY = pk_live_xxxxxxxxxxxxx
```

O para testing:
```
STRIPE_PUBLISHABLE_KEY = pk_test_xxxxxxxxxxxxx
```

**Dónde obtenerla:**
- Dashboard de Stripe → Developers → API keys
- https://dashboard.stripe.com/apikeys

---

### 4. STRIPE_PRICE_MENSUAL

```
STRIPE_PRICE_MENSUAL = price_xxxxxxxxxxxxx
```

**Dónde obtenerla:**
- Dashboard de Stripe → Products → Tu producto mensual → Pricing
- O crea un nuevo precio: Products → Add Product → Set up pricing

---

### 5. STRIPE_PRICE_ANUAL

```
STRIPE_PRICE_ANUAL = price_xxxxxxxxxxxxx
```

**Dónde obtenerla:**
- Dashboard de Stripe → Products → Tu producto anual → Pricing
- O crea un nuevo precio: Products → Add Product → Set up pricing

---

### 6. STRIPE_WEBHOOK_SECRET

```
STRIPE_WEBHOOK_SECRET = whsec_xxxxxxxxxxxxx
```

**Dónde obtenerla:**
1. Dashboard de Stripe → Developers → Webhooks
2. Crea un nuevo endpoint o edita uno existente
3. URL del endpoint: `https://tu-dominio.railway.app/stripe/webhook`
4. Eventos a escuchar:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. Copia el "Signing secret" (empieza con `whsec_`)

---

### 7. SECRET_KEY

```
SECRET_KEY = tu-clave-secreta-super-larga-y-aleatoria-de-minimo-32-caracteres
```

**Requisitos:**
- Mínimo 32 caracteres
- Aleatoria y segura
- No compartirla públicamente

**Generar una clave:**
```python
import secrets
print(secrets.token_urlsafe(32))
```

O usar:
```bash
openssl rand -hex 32
```

---

## 🔍 Cómo Verificar la Configuración

### Opción 1: Script de Verificación (Recomendado)

Ejecuta el script de verificación:

```bash
cd Backend
python scripts/verify_railway_env.py
```

Este script verifica:
- ✅ Que DATABASE_URL apunte a PostgreSQL
- ✅ Que todas las variables de Stripe estén configuradas
- ✅ Que SECRET_KEY tenga el formato correcto
- ✅ Que las variables opcionales estén presentes

### Opción 2: Verificación Manual en Railway

1. Ve a tu proyecto en Railway
2. Settings → Variables
3. Verifica que cada variable esté presente y con el formato correcto

### Opción 3: Verificar en los Logs

Después de desplegar, revisa los logs de Railway:

```bash
railway logs
```

Busca:
- ✅ "DATABASE_URL apunta a PostgreSQL" (no SQLite)
- ✅ "Stripe configurado correctamente"
- ✅ Sin errores de variables faltantes

---

## 🚨 Problemas Comunes

### Error: "DATABASE_URL no apunta a PostgreSQL"

**Solución:**
1. Ve a Railway → Settings → Variables
2. Cambia `DATABASE_URL` a: `${{Postgres.DATABASE_URL}}`
3. Asegúrate de tener un servicio PostgreSQL añadido a tu proyecto
4. Reinicia el servicio

### Error: "STRIPE_SECRET_KEY no válida"

**Solución:**
1. Verifica que empiece con `sk_live_` o `sk_test_`
2. Asegúrate de no tener espacios extra
3. Copia la clave directamente desde el dashboard de Stripe

### Error: "SECRET_KEY muy corta"

**Solución:**
1. Genera una nueva clave de mínimo 32 caracteres
2. Actualiza `SECRET_KEY` en Railway
3. Reinicia el servicio

---

## 📝 Checklist de Configuración

Antes de desplegar, verifica:

- [ ] DATABASE_URL = `${{Postgres.DATABASE_URL}}`
- [ ] STRIPE_SECRET_KEY configurada (sk_live_... o sk_test_...)
- [ ] STRIPE_PUBLISHABLE_KEY configurada (pk_live_... o pk_test_...)
- [ ] STRIPE_PRICE_MENSUAL configurada (price_...)
- [ ] STRIPE_PRICE_ANUAL configurada (price_...)
- [ ] STRIPE_WEBHOOK_SECRET configurada (whsec_...)
- [ ] SECRET_KEY configurada (mínimo 32 caracteres)
- [ ] OPENAI_API_KEY configurada (opcional pero recomendada)
- [ ] FRONTEND_URL configurada (opcional, para redirects)

---

## 🔄 Después de Cambiar Variables

1. **Reinicia el servicio** en Railway
2. **Verifica los logs** para asegurarte de que no hay errores
3. **Prueba el endpoint** `/api/user/me` para verificar que todo funciona

---

## 📚 Referencias

- [Railway Variables Documentation](https://docs.railway.app/develop/variables)
- [Stripe API Keys](https://dashboard.stripe.com/apikeys)
- [Stripe Webhooks](https://dashboard.stripe.com/webhooks)
