# 🔍 CÓDIGO REAL: handle_recalculate_macros()

## 📍 Ubicación: `Backend/app/utils/function_handlers_optimized.py`
## 📍 Líneas: 237-635

---

## 1️⃣ VERIFICACIÓN DE PREMIUM (Líneas 294-305)

```python
from app.models import Plan, Usuario

# Obtener usuario para verificar si es premium
usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
if not usuario:
    logger.error(f"❌ No se encontró usuario {user_id}")
    return {
        "success": False,
        "message": "Usuario no encontrado"
    }

# Verificar si es premium
is_premium = bool(usuario.is_premium) or (usuario.plan_type == "PREMIUM")
logger.info(f"💎 Usuario premium: {is_premium}")
```

---

## 2️⃣ REGENERACIÓN DE DIETA CON GPT (Líneas 440-492)

```python
# Regenerar dieta según tipo de usuario
if is_premium:
    # ==========================================
    # PREMIUM: Regenerar dieta completa con GPT
    # ==========================================
    logger.info(f"🤖 Generando dieta personalizada con GPT para usuario PREMIUM...")
    
    # Preparar datos para GPT
    datos_usuario = {
        'altura': int(altura_cm),
        'peso': float(nuevo_peso),
        'edad': int(edad),
        'sexo': sexo,
        'objetivo': current_plan.objetivo or 'ganar_musculo',
        'nutrition_goal': nuevo_objetivo,  # Este es el objetivo nutricional actualizado
        'experiencia': current_plan.experiencia or 'intermedio',
        'materiales': current_plan.materiales or 'gym_completo',
        'tipo_cuerpo': current_plan.tipo_cuerpo or 'mesomorfo',
        'alergias': current_plan.alergias or 'Ninguna',
        'restricciones': current_plan.restricciones_dieta or 'Ninguna',
        'lesiones': current_plan.lesiones or 'Ninguna',
        'nivel_actividad': nivel_actividad
    }
    
    try:
        # Generar nuevo plan completo con GPT
        plan_generado = await generar_plan_personalizado(datos_usuario)
        
        # Extraer dieta del plan generado
        dieta_generada = plan_generado.get("dieta", {})
        
        # Convertir al formato current_diet
        meals_from_gpt = dieta_generada.get("comidas", [])
        
        # Convertir formato de comidas del GPT al formato current_diet
        meals_updated = []
        for comida in meals_from_gpt:
            comida_formato = {
                "nombre": comida.get("nombre", ""),
                "kcal": comida.get("kcal", 0),
                "macros": comida.get("macros", {}),
                "alimentos": comida.get("alimentos", []),
                "alternativas": comida.get("alternativas", [])
            }
            meals_updated.append(comida_formato)
        
        logger.info(f"✅ Dieta regenerada con GPT: {len(meals_updated)} comidas")
        
    except Exception as e:
        logger.error(f"❌ Error generando dieta con GPT: {e}")
        logger.warning(f"⚠️ Fallando a dieta genérica como respaldo...")
        # Si falla GPT, usar template genérico
        is_premium = False  # Para que use el código de FREE abajo
```

**🔍 PUNTO CRÍTICO:** Si `generar_plan_personalizado()` falla, cambia `is_premium = False` y cae al código de FREE.

---

## 3️⃣ REGENERACIÓN CON TEMPLATE GENÉRICO (Líneas 494-534)

```python
if not is_premium:
    # ==========================================
    # FREE: Usar template genérico con nuevos valores
    # ==========================================
    logger.info(f"📋 Generando dieta genérica para usuario FREE...")
    
    # Preparar datos para template genérico
    user_data_generic = {
        'peso': float(nuevo_peso),
        'altura': int(altura_cm),
        'edad': int(edad),
        'sexo': sexo,
        'objetivo': nuevo_objetivo,
        'nivel_actividad': nivel_actividad
    }
    
    try:
        # Generar plan genérico
        plan_generico = get_generic_plan(user_data_generic)
        dieta_generica = plan_generico.get("dieta", {})
        
        # Convertir formato de comidas al formato current_diet
        meals_from_template = dieta_generica.get("comidas", [])
        meals_updated = []
        for comida in meals_from_template:
            comida_formato = {
                "nombre": comida.get("nombre", ""),
                "kcal": comida.get("kcal", 0),
                "macros": comida.get("macros", {}),
                "alimentos": comida.get("alimentos", []),
                "alternativas": comida.get("alternativas", [])
            }
            meals_updated.append(comida_formato)
        
        logger.info(f"✅ Dieta genérica regenerada: {len(meals_updated)} comidas")
        
    except Exception as e:
        logger.error(f"❌ Error generando dieta genérica: {e}")
        # Si falla, mantener meals existentes
        meals_existing = current_diet.get("meals") or current_diet.get("comidas") or []
        meals_updated = meals_existing

# Si no se generaron meals (fallo en ambos), mantener los existentes
if not meals_updated:
    logger.warning(f"⚠️ No se pudieron generar meals, manteniendo existentes")
    meals_existing = current_diet.get("meals") or current_diet.get("comidas") or []
    meals_updated = meals_existing

logger.info(f"🔄 Dieta regenerada: {len(meals_updated)} comidas")
```

**🔍 PUNTO CRÍTICO:** Si ambos fallan, mantiene `meals_existing` que podría estar vacío o desactualizado.

---

## 4️⃣ ACTUALIZACIÓN DE current_diet (Líneas 544-556)

```python
# Actualizar current_diet con macros teóricos y meals actualizados
current_diet = {
    "meals": meals_updated,
    "total_kcal": int(target_calories),
    "macros": {
        "proteina": nuevas_proteinas,
        "carbohidratos": nuevos_carbos,
        "grasas": nuevas_grasas
    },
    "objetivo": nuevo_objetivo,
    "updated_at": datetime.utcnow().isoformat(),
    "version": increment_diet_version(current_diet.get("version", "1.0.0"))
}

# Actualizar metadata para compatibilidad con código legacy
if 'metadata' not in current_diet:
    current_diet['metadata'] = {}

current_diet['metadata']['proteina_total'] = round(nuevas_proteinas, 1)
current_diet['metadata']['carbohidratos_total'] = round(nuevos_carbos, 1)
current_diet['metadata']['grasas_total'] = round(nuevas_grasas, 1)
```

---

## 5️⃣ GUARDADO EN BASE DE DATOS (Líneas 566-584)

```python
logger.info(f"💾 Actualizando dieta en BD:")
logger.info(f"   Total kcal: {current_diet['total_kcal']}")
logger.info(f"   Macros: P={current_diet['macros']['proteina']}g, C={current_diet['macros']['carbohidratos']}g, G={current_diet['macros']['grasas']}g")

# Guardar en BD - Actualizar tanto Plan.dieta como usuario.current_diet
current_plan.dieta = json.dumps(current_diet)

# Actualizar también usuario.current_diet para que el endpoint lo lea correctamente
from app.models import Usuario
usuario = db.query(Usuario).filter(Usuario.id == user_id).first()  # ⚠️ QUERY DUPLICADA
if usuario:
    usuario.current_diet = json.dumps(current_diet)
    logger.info(f"✅ Actualizado usuario.current_diet para user_id: {user_id}")
else:
    logger.warning(f"⚠️ No se encontró usuario {user_id} para actualizar current_diet")

db.commit()

logger.info(f"✅ Dieta actualizada en BD - Plan.dieta y usuario.current_diet")
```

**🔍 PUNTO CRÍTICO:** Hay una query duplicada del usuario (línea 575), pero debería usar el objeto `usuario` que ya existe desde la línea 295.

---

## 🐛 POSIBLES PROBLEMAS DETECTADOS:

### Problema 1: Variable `meals_updated` puede no estar definida
- Si `is_premium = True` pero la excepción en GPT no se captura correctamente
- Si `is_premium = False` pero `get_generic_plan()` falla y `meals_existing` está vacío

### Problema 2 more: Query duplicada del usuario
- Línea 295: `usuario = db.query(Usuario)...`
- Línea 575: `usuario = db.query(Usuario)...` (duplicada)
- Podría usar la instancia ya existente

### Problema 3: Si GPT falla silenciosamente
- El `try-except` captura errores pero cambia `is_premium = False`
- Si no hay log del error, no se sabe por qué falló

---

## ✅ SOLUCIÓN SUGERIDA:

1. **Añadir más logs** para verificar qué camino se está ejecutando
2. **Verificar que `meals_updated` siempre esté definido** antes de usarlo
3. **Usar el objeto `usuario` ya existente** en lugar de hacer query duplicada
4. **Añadir logs de debugging** para ver qué devuelve GPT

---

**Fecha:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")


