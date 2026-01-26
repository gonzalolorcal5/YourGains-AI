# 🧪 Script de Testing de Flujo Completo de Usuario

## 📋 Descripción

Este script verifica el flujo completo de usuario después de aplicar los fixes de optimización:

1. ✅ Registro de usuario
2. ✅ Login inicial
3. ✅ Onboarding completo
4. ✅ Verificación pre-premium
5. ✅ Activación premium (usando fallback endpoint)
6. ✅ Verificación post-premium
7. ✅ Logout (simulado)
8. ✅ Login nuevamente
9. ✅ Verificación final

## 🚀 Uso

### Testing Local

```bash
cd Backend
python scripts/test_user_flow.py
```

Por defecto, apunta a `http://127.0.0.1:8000`

### Testing en Producción (Railway)

```bash
cd Backend
API_BASE_URL=https://tu-dominio.railway.app python scripts/test_user_flow.py
```

### Testing en Desarrollo

```bash
cd Backend
API_BASE_URL=http://localhost:8000 python scripts/test_user_flow.py
```

## 📊 Qué Verifica

### En cada paso:

1. **Estado de `is_premium`**
   - Debe ser `false` antes de activar premium
   - Debe ser `true` después de activar premium

2. **Estado de `onboarding_completed`**
   - Debe ser consistente entre `/api/user/me` y `/login`
   - Si tiene Plan en BD, debe ser `true` obligatoriamente

3. **Existencia de Plan en BD**
   - Verifica que después de onboarding se cree un Plan
   - Verifica que después de activar premium el Plan persista

4. **Contenido de `current_routine`**
   - Verifica que después de onboarding haya una rutina generada

5. **Consistencia de `plan_type`**
   - Debe ser `FREE` antes de premium
   - Debe ser `PREMIUM_MONTHLY` o `PREMIUM_YEARLY` después

## 📝 Logs Detallados

El script muestra logs detallados de cada paso:

```
[PASO 1] REGISTRO DE USUARIO
ℹ️  Email: test_1234567890@test.com
ℹ️  Password: TestPassword123!
✅ Registro: OK
  email: test_1234567890@test.com

[PASO 2] LOGIN
✅ Login: OK
  token_received: True
  onboarding_completed: False
  user_id: 123
```

## 📄 Reporte Generado

Al finalizar, el script genera un reporte JSON en:

```
Backend/test_user_flow_report.json
```

El reporte incluye:
- Timestamp de inicio y fin
- Resultado de cada paso
- Detalles de cada verificación
- Errores encontrados (si los hay)

## ✅ Verificaciones Críticas

### 1. Onboarding Completo

Después del onboarding, verifica:
- ✅ Se creó un Plan en la BD
- ✅ `onboarding_completed` es `true` (si tiene Plan)
- ✅ `current_routine` tiene contenido

### 2. Activación Premium

Después de activar premium, verifica:
- ✅ `is_premium` es `true`
- ✅ `plan_type` es `PREMIUM_MONTHLY` o `PREMIUM_YEARLY`
- ✅ `onboarding_completed` es `true` (porque tiene Plan en BD)
- ✅ NO se regenera el plan (el webhook ya lo hizo)

### 3. Consistencia entre Endpoints

Verifica que:
- ✅ `/api/user/me` y `/login` devuelven el mismo `onboarding_completed`
- ✅ La lógica es consistente en ambos endpoints

## 🚨 Problemas Comunes

### Error: "Usuario ya existe"

**Solución:** El script genera un email único con timestamp, pero si ejecutas muy rápido puede colisionar. Espera unos segundos entre ejecuciones.

### Error: "Token inválido"

**Solución:** Verifica que el servidor esté corriendo y que la URL sea correcta.

### Error: "Onboarding timeout"

**Solución:** El onboarding puede tardar si usa GPT-4. El script tiene timeout de 120 segundos. Si falla, verifica:
- Que OpenAI API Key esté configurada
- Que el modelo esté disponible
- Que no haya rate limits

### Error: "Activación premium falló"

**Solución:** Verifica que:
- El endpoint `/stripe/activate-premium` esté disponible
- El token JWT sea válido
- No haya errores en los logs del servidor

## 📋 Checklist de Verificación

Después de ejecutar el test, verifica:

- [ ] Todos los pasos pasaron (✅)
- [ ] `is_premium` cambió correctamente de `false` a `true`
- [ ] `onboarding_completed` es `true` después de tener Plan
- [ ] `onboarding_completed` es consistente entre endpoints
- [ ] No se regeneró el plan al activar premium
- [ ] El estado persiste después de logout/login

## 🔍 Análisis del Reporte

El reporte JSON tiene esta estructura:

```json
{
  "started_at": "2024-01-01T12:00:00",
  "completed_at": "2024-01-01T12:05:00",
  "all_passed": true,
  "steps": [
    {
      "step": "Registro",
      "success": true,
      "timestamp": "2024-01-01T12:00:01",
      "details": {
        "email": "test_1234567890@test.com"
      }
    },
    ...
  ],
  "errors": []
}
```

## 🎯 Casos de Uso

### Verificar Fixes de Optimización

```bash
# Ejecutar test
python scripts/test_user_flow.py

# Verificar que:
# 1. No se hace expire_all() en cada request
# 2. onboarding_completed es consistente
# 3. No se regenera plan al activar premium
```

### Verificar en Producción

```bash
# Ejecutar contra Railway
API_BASE_URL=https://tu-dominio.railway.app python scripts/test_user_flow.py

# Verificar logs en Railway
railway logs
```

### Debugging

Si un paso falla:
1. Revisa los logs del script
2. Revisa el reporte JSON
3. Revisa los logs del servidor
4. Verifica la base de datos directamente

## 📚 Referencias

- [Documentación de Fixes Aplicados](../RAILWAY_ENV_SETUP.md)
- [Script de Auditoría de BD](./audit_database.py)
- [Documentación de Onboarding](../ONBOARDING_AVANZADO_VERIFICACION.md)
