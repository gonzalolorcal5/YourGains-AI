# 🔍 AUDITORÍA DE BASE DE DATOS POSTGRESQL EN RAILWAY

## 📋 Queries SQL para Ejecutar Manualmente

### 1. Ver todos los usuarios con su estado de premium

```sql
SELECT 
    id, 
    email, 
    is_premium, 
    plan_type,
    stripe_customer_id, 
    stripe_subscription_id, 
    onboarding_completed,
    CASE 
        WHEN current_routine = '{}' OR current_routine IS NULL THEN false
        ELSE true
    END as tiene_rutina
FROM usuarios
ORDER BY id DESC;
```

**Qué verificar:**
- ✅ Usuarios premium tienen `is_premium = true`
- ✅ `plan_type` coincide con el tipo de suscripción (PREMIUM_MONTHLY, PREMIUM_YEARLY)
- ✅ `onboarding_completed` es `true` si tienen plan

---

### 2. Ver todos los planes (historial de onboarding)

```sql
SELECT 
    id, 
    user_id, 
    fecha_creacion, 
    objetivo_gym, 
    objetivo_nutricional,
    session_duration
FROM planes
ORDER BY id DESC;
```

**Qué verificar:**
- ✅ Cada usuario premium tiene al menos un plan
- ✅ `fecha_creacion` es reciente (no muy antigua)
- ✅ `session_duration` está configurado

---

### 3. Verificar usuarios premium sin plan generado (PROBLEMA POTENCIAL)

```sql
SELECT 
    u.id,
    u.email,
    u.is_premium,
    u.plan_type,
    CASE 
        WHEN u.current_routine = '{}' OR u.current_routine IS NULL THEN 'NO'
        ELSE 'SI'
    END as tiene_rutina,
    CASE
        WHEN EXISTS (SELECT 1 FROM planes WHERE user_id = u.id) THEN 'SI'
        ELSE 'NO'
    END as tiene_plan_tabla,
    u.onboarding_completed
FROM usuarios u
WHERE u.is_premium = true;
```

**Qué buscar:**
- ❌ `tiene_rutina = 'NO'` y `tiene_plan_tabla = 'NO'` → Usuario premium sin plan
- ❌ `tiene_plan_tabla = 'SI'` pero `onboarding_completed = false` → Inconsistencia

---

### 4. Usuarios con plan pero sin premium (casos legacy)

```sql
SELECT 
    u.id,
    u.email,
    u.is_premium,
    u.plan_type,
    COUNT(p.id) as total_planes
FROM usuarios u
INNER JOIN planes p ON p.user_id = u.id
WHERE u.is_premium = false
GROUP BY u.id, u.email, u.is_premium, u.plan_type;
```

**Qué buscar:**
- Usuarios que tienen plan pero `is_premium = false`
- Posibles casos de usuarios que cancelaron suscripción

---

### 5. Inconsistencias entre is_premium y plan_type

```sql
SELECT 
    id,
    email,
    is_premium,
    plan_type,
    CASE
        WHEN is_premium = true AND plan_type NOT IN ('PREMIUM_MONTHLY', 'PREMIUM_YEARLY', 'PREMIUM') THEN 'INCONSISTENTE'
        WHEN is_premium = false AND plan_type IN ('PREMIUM_MONTHLY', 'PREMIUM_YEARLY', 'PREMIUM') THEN 'INCONSISTENTE'
        ELSE 'OK'
    END as estado
FROM usuarios
WHERE 
    (is_premium = true AND plan_type NOT IN ('PREMIUM_MONTHLY', 'PREMIUM_YEARLY', 'PREMIUM'))
    OR
    (is_premium = false AND plan_type IN ('PREMIUM_MONTHLY', 'PREMIUM_YEARLY', 'PREMIUM'));
```

---

## 🤖 Script Automático de Auditoría

En lugar de ejecutar los queries manualmente, puedes usar el script de Python:

```bash
cd Backend
python scripts/audit_database.py
```

**El script:**
- ✅ Se conecta automáticamente a PostgreSQL usando DATABASE_URL
- ✅ Ejecuta todos los queries
- ✅ Detecta inconsistencias automáticamente
- ✅ Genera un reporte con recomendaciones
- ✅ Guarda el reporte en `audit_report.txt`

---

## 🚨 Problemas Comunes y Soluciones

### Problema 1: Usuario premium sin plan generado

**Síntomas:**
- `is_premium = true`
- `current_routine = '{}'` o `NULL`
- No existe registro en tabla `planes`

**Causas posibles:**
- El webhook de Stripe no se ejecutó
- Error durante la generación del plan
- El usuario se activó manualmente sin generar plan

**Solución:**
1. Verificar logs del webhook en Railway
2. Regenerar plan manualmente usando el endpoint `/stripe/webhook` o regenerar desde el admin
3. Verificar que el webhook esté configurado correctamente en Stripe

---

### Problema 2: Usuario con plan pero `onboarding_completed = false`

**Síntomas:**
- Existe registro en tabla `planes`
- `onboarding_completed = false`

**Causa:**
- La lógica antigua no actualizaba `onboarding_completed` correctamente

**Solución:**
- ✅ Ya está corregido en la nueva lógica
- El endpoint `/api/user/me` ahora verifica Plan en BD primero
- Se puede corregir manualmente:
  ```sql
  UPDATE usuarios
  SET onboarding_completed = true
  WHERE id IN (
      SELECT DISTINCT user_id FROM planes
  );
  ```

---

### Problema 3: Inconsistencia entre `is_premium` y `plan_type`

**Síntomas:**
- `is_premium = true` pero `plan_type = 'FREE'`
- `is_premium = false` pero `plan_type = 'PREMIUM_MONTHLY'`

**Causa:**
- Sincronización incompleta con Stripe
- Cambios manuales en la BD

**Solución:**
1. Usar el endpoint `/subscription-status` para sincronizar
2. O corregir manualmente:
   ```sql
   -- Si es premium, actualizar plan_type
   UPDATE usuarios
   SET plan_type = 'PREMIUM_MONTHLY'
   WHERE is_premium = true AND plan_type = 'FREE';
   
   -- Si no es premium, actualizar plan_type
   UPDATE usuarios
   SET plan_type = 'FREE'
   WHERE is_premium = false AND plan_type LIKE 'PREMIUM%';
   ```

---

## 📊 Interpretación de Resultados

### Estado Ideal

```
✅ Usuario premium:
   - is_premium = true
   - plan_type = PREMIUM_MONTHLY o PREMIUM_YEARLY
   - tiene_rutina = SI
   - tiene_plan_tabla = SI
   - onboarding_completed = true
```

### Estados Problemáticos

```
❌ Usuario premium sin plan:
   - is_premium = true
   - tiene_rutina = NO
   - tiene_plan_tabla = NO

❌ Plan sin onboarding:
   - tiene_plan_tabla = SI
   - onboarding_completed = false

❌ Inconsistencia plan_type:
   - is_premium = true pero plan_type = FREE
   - is_premium = false pero plan_type = PREMIUM_MONTHLY
```

---

## 🔄 Después de la Auditoría

1. **Si encuentras problemas:**
   - Ejecuta el script de auditoría para obtener detalles
   - Revisa los logs de Railway para entender qué pasó
   - Corrige los problemas usando las soluciones sugeridas

2. **Si todo está bien:**
   - Guarda el reporte para referencia futura
   - Programa auditorías periódicas (semanal o mensual)

3. **Monitoreo continuo:**
   - Configura alertas en Railway si es posible
   - Revisa los logs del webhook regularmente
   - Verifica que nuevos usuarios premium tengan plan generado

---

## 📝 Checklist de Auditoría

- [ ] Ejecutar query de usuarios
- [ ] Ejecutar query de planes
- [ ] Ejecutar query de usuarios premium sin plan
- [ ] Verificar inconsistencias
- [ ] Ejecutar script automático de auditoría
- [ ] Revisar reporte generado
- [ ] Corregir problemas detectados
- [ ] Documentar cambios realizados
