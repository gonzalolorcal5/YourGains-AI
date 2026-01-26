# 🔧 Script de Migración One-Time: Corrección de Usuarios Existentes

## 📋 Descripción

Este script corrige inconsistencias en usuarios existentes que pueden tener datos inconsistentes después de aplicar los fixes de optimización.

### Problemas que corrige:

1. ✅ **Usuarios premium sin `current_routine` válida**
   - Busca usuarios con `is_premium = true` pero `current_routine = '{}'` o inválida
   - Si tienen un Plan en la tabla `planes`, copia la rutina y dieta del Plan más reciente

2. ✅ **Usuarios con Plan pero `onboarding_completed = false`**
   - Si el usuario tiene un Plan en la BD, asegura que `onboarding_completed = true`
   - Esto es consistente con la nueva lógica que prioriza Plan en BD

## 🚀 Uso

### Modo Dry-Run (Recomendado primero)

Ejecuta primero en modo dry-run para ver qué cambios se harían:

```bash
cd Backend
python scripts/fix_existing_users.py
```

**Salida:**
- Muestra todos los usuarios problemáticos encontrados
- Indica qué correcciones se aplicarían
- **NO modifica la base de datos**

### Modo Ejecución Real

Una vez que hayas revisado el dry-run, ejecuta con `--execute`:

```bash
cd Backend
python scripts/fix_existing_users.py --execute
```

**⚠️ IMPORTANTE:**
- Este modo **SÍ modifica la base de datos**
- Te pedirá confirmación antes de aplicar cambios
- Se genera un reporte detallado de todos los cambios

## 📊 Qué Hace el Script

### 1. Busca Usuarios Problemáticos

El script identifica usuarios premium que:
- No tienen `current_routine` válida (vacía o '{}')
- No tienen `current_diet` válida (vacía o '{}')
- Tienen Plan en BD pero `onboarding_completed = false`

### 2. Obtiene el Plan Más Reciente

Para cada usuario problemático:
- Busca el Plan más reciente en la tabla `planes`
- Usa el Plan con el `id` más alto (más reciente)

### 3. Aplica Correcciones

**Si tiene Plan:**
- ✅ Copia `rutina` del Plan → `current_routine` del Usuario
- ✅ Copia `dieta` del Plan → `current_diet` del Usuario
- ✅ Actualiza `onboarding_completed = true`

**Si no tiene Plan:**
- ⚠️ No se puede corregir automáticamente
- Se muestra advertencia en el reporte

## 📄 Reporte Generado

El script genera un reporte JSON con timestamp:

```
Backend/fix_users_report_20240101_120000.json
```

**Contenido del reporte:**
- Timestamp de ejecución
- Modo (dry-run o ejecución)
- Total de usuarios procesados
- Correcciones aplicadas
- Errores encontrados (si los hay)
- Detalle de cada corrección

## ✅ Verificaciones

### Antes de Ejecutar

1. ✅ **Backup de la base de datos**
   ```bash
   # En Railway CLI
   railway connect postgres
   pg_dump > backup_$(date +%Y%m%d).sql
   ```

2. ✅ **Ejecutar en modo dry-run primero**
   ```bash
   python scripts/fix_existing_users.py
   ```

3. ✅ **Revisar el reporte del dry-run**
   - Verifica que los cambios sean correctos
   - Confirma que no afectará usuarios incorrectos

### Después de Ejecutar

1. ✅ **Verificar el reporte JSON**
   - Revisa que todas las correcciones se aplicaron
   - Verifica que no haya errores

2. ✅ **Verificar en la base de datos**
   ```sql
   -- Verificar usuarios corregidos
   SELECT id, email, is_premium, onboarding_completed,
          CASE WHEN current_routine != '{}' THEN 'SI' ELSE 'NO' END as tiene_rutina
   FROM usuarios
   WHERE is_premium = true;
   ```

3. ✅ **Ejecutar script de auditoría**
   ```bash
   python scripts/audit_database.py
   ```

## 🚨 Casos Especiales

### Usuario Premium sin Plan

Si un usuario es premium pero no tiene Plan en la tabla `planes`:
- ⚠️ No se puede copiar rutina/dieta automáticamente
- Se muestra advertencia en el reporte
- **Solución manual:** El usuario debe completar onboarding o regenerar plan

### Usuario con Múltiples Planes

Si un usuario tiene múltiples Planes:
- ✅ Se usa el Plan más reciente (mayor `id`)
- ✅ Se copia la rutina y dieta de ese Plan

### Usuario con Rutina Inválida

Si `current_routine` existe pero no es válida (JSON malformado):
- ✅ Se reemplaza con la rutina del Plan
- ✅ Se valida que el JSON sea correcto antes de copiar

## 📋 Checklist de Ejecución

- [ ] Backup de la base de datos realizado
- [ ] Ejecutado en modo dry-run
- [ ] Revisado el reporte del dry-run
- [ ] Confirmado que los cambios son correctos
- [ ] Ejecutado con `--execute`
- [ ] Revisado el reporte final
- [ ] Verificado en la base de datos
- [ ] Ejecutado script de auditoría

## 🔍 Ejemplo de Salida

```
======================================================================
  MIGRACIÓN ONE-TIME: CORRECCIÓN DE USUARIOS EXISTENTES
======================================================================

✅ Conexión a PostgreSQL establecida

======================================================================
  BUSCANDO USUARIOS PROBLEMÁTICOS
======================================================================

ℹ️  Total usuarios premium: 15
ℹ️  Usuarios problemáticos encontrados: 3

Usuarios a corregir:
  - ID 123 (user1@example.com): sin rutina válida, onboarding_completed = false
  - ID 456 (user2@example.com): sin dieta válida
  - ID 789 (user3@example.com): onboarding_completed = false

======================================================================
  APLICANDO CORRECCIONES
======================================================================

Usuario ID 123 (user1@example.com):
  → Copiar rutina y dieta del Plan ID 45
  → Actualizar onboarding_completed = true
  ✅ Rutina y dieta copiadas del Plan ID 45
  ✅ onboarding_completed actualizado a True
  ✅ Cambios guardados para usuario 123

======================================================================
  REPORTE FINAL
======================================================================

ℹ️  Total usuarios procesados: 3
ℹ️  Correcciones aplicadas: 3
ℹ️  Errores: 0

Reporte guardado en: Backend/fix_users_report_20240101_120000.json
```

## ⚠️ Advertencias

1. **Este script es ONE-TIME**
   - Solo debe ejecutarse una vez después de aplicar los fixes
   - No está diseñado para ejecutarse periódicamente

2. **Backup obligatorio**
   - Siempre haz backup antes de ejecutar con `--execute`
   - Los cambios son irreversibles sin backup

3. **Verificación manual**
   - Revisa el reporte después de ejecutar
   - Verifica que los cambios sean correctos

## 📚 Referencias

- [Script de Auditoría](./audit_database.py)
- [Script de Testing de Flujo](./test_user_flow.py)
- [Documentación de Fixes](../RAILWAY_ENV_SETUP.md)
