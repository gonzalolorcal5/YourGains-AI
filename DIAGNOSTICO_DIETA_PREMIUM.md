# 🔍 DIAGNÓSTICO: Problema Dieta Premium vs Free

## 📋 ARCHIVOS CLAVE - CONTENIDO COMPLETO

---

## 1. ENDPOINT QUE DEVUELVE LA DIETA
**Archivo:** `Backend/app/routes/plan.py`  
**Endpoint:** `GET /user/current-routine`

### Código Relevante:

```python
@router.get("/user/current-routine")
def obtener_rutina_actual(user_id: int, db: Session = Depends(get_db)):
    """
    Obtiene la rutina actual del usuario desde current_routine o planes (para usuarios free)
    """
    # IMPORTANTE: Invalidar cache de SQLAlchemy y hacer query fresca
    db.expire_all()
    
    usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Forzar refresh del objeto desde BD
    try:
        db.refresh(usuario)
    except Exception:
        db.expire_all()
        usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
    
    # Verificar si es premium
    is_premium = usuario.is_premium or usuario.plan_type == "PREMIUM"
    
    # Si es premium, usar current_routine
    if is_premium and usuario.current_routine:
        current_routine = deserialize_json(usuario.current_routine, "current_routine")
        current_diet = deserialize_json(usuario.current_diet or "{}", "current_diet")
        
        # Si current_diet está vacío o no tiene macros, intentar leer desde Plan.dieta como respaldo
        if (not current_diet or 
            not isinstance(current_diet, dict) or 
            not current_diet.get('macros') or 
            not any(current_diet.get('macros', {}).values())):
            plan_data = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.id.desc()).first()
            if plan_data and plan_data.dieta:
                dieta_plan = json.loads(plan_data.dieta)
                if isinstance(dieta_plan, dict):
                    current_diet = dieta_plan
    
    elif is_premium and not usuario.current_routine:
        # Usuario premium pero sin current_routine → intentar usar plan de tabla planes
        plan_data = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.id.desc()).first()
        if plan_data and plan_data.rutina and plan_data.dieta:
            rutina_plan = json.loads(plan_data.rutina)
            dieta_plan = json.loads(plan_data.dieta)
            # Convertir a formato current_routine/current_diet
            # ... código de conversión ...
    
    else:
        # Si es free, usar template genérico
        from app.utils.routine_templates import get_generic_plan
        generic_plan = get_generic_plan(user_data)
        # Convertir rutina genérica al formato esperado
        # ... código de conversión ...
    
    return {
        "success": True,
        "current_routine": current_routine,
        "current_diet": current_diet,
        "user_id": usuario.id,
        "is_premium": is_premium
    }
```

**🔍 PUNTOS CRÍTICOS:**
- Si usuario es PREMIUM y tiene `current_routine`, lee de `usuario.current_diet`
- Si `current_diet` está vacío, hace fallback a `Plan.dieta`
- Si usuario es PREMIUM pero NO tiene `current_routine`, lee de tabla `planes`
- Si usuario es FREE, genera template genérico con `get_generic_plan()`

---

## 2. FUNCIÓN QUE RECALCULA MACROS Y REGENERA DIETA
**Archivo:** `Backend/app/utils/function_handlers_optimized.py`  
**Función:** `handle_recalculate_macros()`

### Código Relevante:

```python
async def handle_recalculate_macros(
    user_id: int,
    weight_change_kg: float = None,
    goal: str = None,
    calorie_adjustment: int = None,
    is_incremental: bool = None,
    adjustment_type: str = None,
    target_calories: int = None,
    db: Session = None
) -> Dict[str, Any]:
    """
    Recalcula los macronutrientes de la dieta - VERSIÓN LIMPIA Y OPTIMIZADA
    """
    # Obtener datos del usuario
    user_data = await db_service.get_user_complete_data(user_id, db)
    current_diet = user_data.get("current_diet")
    
    from app.models import Plan, Usuario
    
    # Obtener usuario para verificar si es premium
    usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
    
    # Verificar si es premium
    is_premium = bool(usuario.is_premium) or (usuario.plan_type == "PREMIUM")
    logger.info(f"💎 Usuario premium: {is_premium}")
    
    # Obtener plan actual
    current_plan = db.query(Plan).filter(Plan.user_id == user_id).order_by(Plan.id.desc()).first()
    
    # Calcular nuevo peso, objetivo, TMB, TDEE y target_calories
    # ... código de cálculo ...
    
    # Calcular macros teóricos
    macros_obj = calculate_macros_distribution(
        calorias_totales=int(target_calories),
        peso_kg=float(nuevo_peso),
        goal=nuevo_objetivo
    )
    
    nuevas_proteinas = int(round(float(macros_obj.get("proteina", 0) or 0)))
    nuevos_carbos = int(round(float(macros_obj.get("carbohidratos", 0) or 0)))
    nuevas_grasas = int(round(float(macros_obj.get("grasas", 0) or 0)))
    
    # ==========================================
    # REGENERAR DIETA COMPLETA CON NUEVOS VALORES
    # ==========================================
    
    if is_premium:
        # PREMIUM: Regenerar dieta completa con GPT
        logger.info(f"🤖 Generando dieta personalizada con GPT para usuario PREMIUM...")
        
        datos_usuario = {
            'altura': int(altura_cm),
            'peso': float(nuevo_peso),
            'edad': int(edad),
            'sexo': sexo,
            'objetivo': current_plan.objetivo or 'ganar_musculo',
            'nutrition_goal': nuevo_objetivo,
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
            # Si falla GPT, usar template genérico
            is_premium = False
    
    if not is_premium:
        # FREE: Usar template genérico con nuevos valores
        logger.info(f"📋 Generando dieta genérica para usuario FREE...")
        
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
            meals_existing = current_diet.get("meals") or current_diet.get("comidas") or []
            meals_updated = meals_existing
    
    # Actualizar current_diet con macros teóricos y meals regenerados
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
    
    # Guardar en BD - Actualizar tanto Plan.dieta como usuario.current_diet
    current_plan.dieta = json.dumps(current_diet)
    usuario.current_diet = json.dumps(current_diet)
    db.commit()
    
    return {
        "success": True,
        "message": "Plan actualizado correctamente",
        "plan_updated": True,
        "changes": changes
    }
```

**🔍 PUNTOS CRÍTICOS:**
- Si es PREMIUM: Llama a `generar_plan_personalizado()` con GPT
- Si es FREE: Llama a `get_generic_plan()` con template
- Guarda en AMBOS: `Plan.dieta` y `usuario.current_diet`

---

## 3. GENERACIÓN DE DIETA CON GPT (PREMIUM)
**Archivo:** `Backend/app/utils/gpt.py`  
**Función:** `generar_plan_personalizado()`

### Código Relevante:

```python
async def generar_plan_personalizado(datos):
    """
    Genera plan personalizado usando GPT con cálculos científicos (TMB/TDEE)
    """
    # Calcular plan nutricional con función científica (TMB + TDEE)
    nutrition_plan = get_complete_nutrition_plan(datos, nutrition_goal)
    
    tmb = nutrition_plan['tmb']
    tdee = nutrition_plan['tdee']
    kcal_objetivo = nutrition_plan['calorias_objetivo']
    macros = nutrition_plan['macros']
    
    # Crear prompt para GPT con macros exactos
    texto_dieta = f"""
    CÁLCULOS NUTRICIONALES CIENTÍFICOS:
    - TMB: {tmb} kcal/día
    - TDEE: {tdee} kcal/día
    - Calorías objetivo ({nutrition_goal}): {kcal_objetivo} kcal/día
    
    MACRONUTRIENTES OBJETIVO:
    - Proteína: {macros['proteina']}g/día
    - Carbohidratos: {macros['carbohidratos']}g/día
    - Grasas: {macros['grasas']}g/día
    
    INSTRUCCIONES CRÍTICAS:
    1. La dieta DEBE cumplir EXACTAMENTE con {kcal_objetivo} kcal/día total
    2. Los macros deben aproximarse lo máximo posible a los valores calculados
    3. Distribuir en 5 comidas balanceadas al día
    4. Cada comida debe especificar cantidades exactas en gramos/ml
    5. Los macros totales deben sumar aproximadamente los valores objetivo
    
    Formato obligatorio de salida en JSON:
    "dieta": {{
      "resumen": "Explicación de TMB y ajuste calórico",
      "comidas": [
        {{
          "nombre": "Desayuno",
          "kcal": 500,
          "macros": {{
            "proteinas": 35,
            "hidratos": 50,
            "grasas": 15
          }},
          "alimentos": [
            "300ml leche semidesnatada - 150kcal",
            "40g avena - 150kcal",
            "1 plátano - 100kcal"
          ],
          "alternativas": [...]
        }}
      ]
    }}
    """
    
    # Llamar a GPT con el prompt
    # ... código de llamada a OpenAI ...
    
    # Parsear respuesta JSON de GPT
    # ... código de parsing ...
    
    return plan_generado
```

**🔍 PUNTOS CRÍTICOS:**
- Calcula TMB/TDEE científicamente
- Pasa macros exactos a GPT
- GPT genera dieta con cantidades específicas
- Devuelve formato `{"dieta": {"comidas": [...]}}`

---

## 4. FUNCIÓN FRONTEND QUE MUESTRA LA DIETA
**Archivo:** `Backend/app/frontend/dashboard.html`  
**Función:** `displayPlan()`

### Código Relevante:

```javascript
function displayPlan(plan, userPremiumStatus = null) {
    const rutinaContent = document.getElementById('rutinaContent');
    const dietaContent = document.getElementById('dietaContent');
    const isPremium = userPremiumStatus !== null ? userPremiumStatus : isPremiumUser();
    
    // DIETA - DISEÑO MINIMALISTA
    if (dietaContent && plan.dieta && plan.dieta.meals && plan.dieta.meals.length > 0) {
        const totalKcal = (typeof plan.dieta.total_kcal === 'number')
            ? plan.dieta.total_kcal
            : (Array.isArray(plan.dieta.meals)
                ? plan.dieta.meals.reduce((acc, m) => acc + (Number(m.kcal) || 0), 0)
                : 0);
        
        let dietaHtml = `
            <h1 class="section-title" style="margin-top: 50px;">Dieta</h1>
            <p class="section-subtitle">Plan personalizado - ${totalKcal} kcal diarias<br>
                <span style="color:#00ff00;font-size:14px">
                    Proteínas: ${plan.dieta?.macros?.proteina||0}g | 
                    Carbos: ${plan.dieta?.macros?.carbohidratos||0}g | 
                    Grasas: ${plan.dieta?.macros?.grasas||0}g
                </span>
            </p>
        `;
        
        plan.dieta.meals.forEach((comida, index) => {
            // Primera comida siempre visible
            if (index === 0) {
                dietaHtml += `<div class="meal-title">${comida.nombre}</div>`;
                if (comida.alimentos) {
                    comida.alimentos.forEach(alimento => {
                        const alimentoText = renderAlimento(alimento);
                        dietaHtml += `<div class="food-item">• ${alimentoText}</div>`;
                    });
                }
            }
            // Resto censurado para FREE
            else if (!isPremium) {
                dietaHtml += `
                    <div class="censored-content">
                        <div class="meal-title">${comida.nombre}</div>
                        <div class="food-item">• ████████ ████</div>
                    </div>
                `;
            }
            // Todo visible para PREMIUM
            else {
                dietaHtml += `<div class="meal-title">${comida.nombre}</div>`;
                if (comida.alimentos) {
                    comida.alimentos.forEach(alimento => {
                        const alimentoText = renderAlimento(alimento);
                        dietaHtml += `<div class="food-item">• ${alimentoText}</div>`;
                    });
                }
            }
        });
        
        dietaContent.innerHTML = dietaHtml;
    }
}
```

**🔍 PUNTOS CRÍTICOS:**
- Lee `plan.dieta.meals[]` para mostrar comidas
- Lee `plan.dieta.macros` para mostrar macros
- Muestra solo primera comida si es FREE
- Muestra todas las comidas si es PREMIUM

---

## 🔍 PREGUNTAS PARA DIAGNÓSTICO

### 1. ¿Cuándo se genera la dieta personalizada?
- **Onboarding:** Cuando el usuario completa el onboarding como PREMIUM
- **Recalcular macros:** Cuando se llama `handle_recalculate_macros()` y el usuario es PREMIUM

### 2. ¿Cómo se guarda la dieta en la BD?
- **Campo 1:** `Plan.dieta` (JSON string) - Guardado en tabla `planes`
- **Campo 2:** `Usuario.current_diet` (JSON string) - Guardado en tabla `usuarios`

### 3. ¿Qué es "la dieta del sistema free"?
- Es una dieta genérica generada por `get_generic_plan()` en `routine_templates.py`
- Siempre tiene las mismas comidas base, solo ajusta cantidades según peso/objetivo
- Formato: `{"comidas": [{"nombre": "Desayuno", "kcal": X, "alimentos": [...]}]}`

### 4. ¿Por qué puede estar mostrando la dieta genérica?
**Posibles causas:**
1. ✅ El usuario NO es realmente PREMIUM (verificar `is_premium` y `plan_type`)
2. ✅ La dieta personalizada nunca se generó/guardó correctamente
3. ✅ El endpoint devuelve siempre la dieta genérica (fallback)
4. ✅ `usuario.current_diet` está vacío, entonces hace fallback a `Plan.dieta` o template

---

## 🛠️ CHECKLIST DE VERIFICACIÓN

### En la Base de Datos:
```sql
-- Verificar si el usuario es premium
SELECT id, email, is_premium, plan_type FROM usuarios WHERE id = ?;

-- Verificar current_diet del usuario
SELECT id, email, current_diet FROM usuarios WHERE id = ?;

-- Verificar Plan.dieta más reciente
SELECT id, user_id, dieta, objetivo_nutricional FROM planes 
WHERE user_id = ? ORDER BY id DESC LIMIT 1;
```

### En los Logs del Backend:
1. ¿Aparece `💎 Usuario premium: True` cuando se recalculan macros?
2. ¿Aparece `🤖 Generando dieta personalizada con GPT para usuario PREMIUM...`?
3. ¿Aparece `✅ Dieta regenerada con GPT: X comidas`?
4. ¿Aparece `✅ Actualizado usuario.current_diet para user_id: X`?

### En el Frontend:
1. ¿Qué muestra `console.log('📊 Frontend: Datos recibidos:', data)`?
2. ¿Qué muestra `console.log('🔍 DEBUG COMPLETO DE MACROS:')`?
3. ¿Qué muestra `console.log('🚀 current_diet existe:', !!data.current_diet)`?

---

## 💡 SOLUCIONES SUGERIDAS

### Solución 1: Verificar que se guarda correctamente
Añadir más logs en `handle_recalculate_macros()` después de guardar:
```python
logger.info(f"💾 Verificando guardado de dieta:")
logger.info(f"   Plan.dieta actualizado: {bool(current_plan.dieta)}")
logger.info(f"   usuario.current_diet actualizado: {bool(usuario.current_diet)}")
logger.info(f"   Contenido usuario.current_diet: {usuario.current_diet[:200] if usuario.current_diet else 'NULL'}")
```

### Solución 2: Forzar regeneración completa
Si la dieta nunca se generó inicialmente, forzar regeneración en el endpoint:
```python
if is_premium and usuario.current_routine and not current_diet.get("meals"):
    # Generar dieta si no existe
    plan_generado = await generar_plan_personalizado(datos_usuario)
    # ... guardar ...
```

### Solución 3: Mejorar logs en frontend
Añadir logs más detallados en `loadUserPlans()`:
```javascript
console.log('🔍 DEBUG COMPLETO DE DIETA RECIBIDA:');
console.log('   current_diet:', data.current_diet);
console.log('   current_diet.meals:', data.current_diet?.meals);
console.log('   current_diet.meals.length:', data.current_diet?.meals?.length);
console.log('   Primer alimento:', data.current_diet?.meals?.[0]?.alimentos?.[0]);
```

---

## 📝 PRÓXIMOS PASOS

1. **Verificar BD:** Ejecutar las queries SQL arriba para ver qué hay guardado
2. **Revisar Logs:** Buscar en los logs del backend los mensajes mencionados
3. **Probar Flujo:** Hacer un cambio de peso/objetivo y seguir todo el flujo
4. **Comparar:** Comparar dieta esperada vs dieta recibida en frontend

---

**Fecha de creación:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")  
**Archivo generado automáticamente para diagnóstico**


