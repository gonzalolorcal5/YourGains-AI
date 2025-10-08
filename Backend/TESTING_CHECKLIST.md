# 🧪 TESTING CHECKLIST - YourGains AI

## 📋 FLUJO COMPLETO A TESTEAR

### 1️⃣ REGISTRO Y ONBOARDING (5 min)
- [ ] Ir a http://127.0.0.1:8000/login.html
- [ ] Hacer clic en "Registrarse"
- [ ] Crear cuenta nueva con email de prueba
- [ ] Verificar que redirige a onboarding
- [ ] Completar formulario onboarding:
  - Datos personales (edad, peso, altura, sexo)
  - Objetivo (volumen, definición, mantenimiento, etc.)
  - Nivel de experiencia
  - Días de entrenamiento
  - Alergias/restricciones (si aplica)
- [ ] Verificar que genera plan automáticamente
- [ ] Verificar que redirige a dashboard

**✅ ESPERADO:** Plan generado y guardado en BD

---

### 2️⃣ VISUALIZACIÓN DEL PLAN (2 min)
- [ ] En dashboard, hacer clic en "Rutina y Dieta"
- [ ] Verificar que muestra:
  - **Rutina**: Ejercicios con series, reps, peso
  - **Dieta**: Comidas con alimentos y macros
- [ ] Como usuario FREE, verificar censura:
  - Primeros 3 ejercicios visibles
  - Resto con blur + badge "PRO"
  - Mensaje "Mejora a Pro para ver 100%"
- [ ] Verificar diseño responsive (mobile)

**✅ ESPERADO:** Plan visible con censura para usuarios free

---

### 3️⃣ CHAT CON IA - MENSAJES GRATIS (5 min)

**Mensaje 1:**
- [ ] Escribir: "Hola, ¿cómo estás?"
- [ ] Verificar respuesta de IA
- [ ] Verificar contador: 1/2 mensajes usados

**Mensaje 2:**
- [ ] Escribir: "Me duele el hombro, modifica mi rutina"
- [ ] Verificar que IA detecta lesión
- [ ] Verificar que aparece notificación de modificación
- [ ] Hacer clic en "Ver Rutina"
- [ ] Verificar que rutina cambió (sin press de banca, con ejercicios seguros)
- [ ] Verificar contador: 2/2 mensajes usados

**Mensaje 3 (Límite alcanzado):**
- [ ] Intentar escribir mensaje 3
- [ ] Verificar que input se deshabilita
- [ ] Verificar modal de upgrade:
  - Mensaje: "Has alcanzado el límite de mensajes gratuitos"
  - Botón "Mejorar a Pro" (verde #84cc16)
  - Botón redirige a tarifas.html

**✅ ESPERADO:** 
- 2 mensajes gratis funcionan
- 3er mensaje bloqueado con modal profesional

---

### 4️⃣ PÁGINA DE TARIFAS (2 min)
- [ ] Verificar que tarifas.html carga correctamente
- [ ] Verificar precios mostrados:
  - Plan FREE: €0/mes (limitado)
  - Plan PRO: €9.99/mes
- [ ] Verificar botón "Suscribirse" funciona
- [ ] Hacer clic en "Suscribirse PRO"

**✅ ESPERADO:** Página de tarifas profesional y clara

---

### 5️⃣ PROCESO DE PAGO STRIPE (5 min)
- [ ] Verificar que redirige a Stripe Checkout
- [ ] Usar tarjeta de prueba: `4242 4242 4242 4242`
- [ ] Fecha: Cualquier futura (12/25)
- [ ] CVC: Cualquier 3 dígitos (123)
- [ ] Completar pago
- [ ] Verificar redirección a dashboard
- [ ] Verificar que ahora es usuario PREMIUM

**✅ ESPERADO:** Pago procesado y usuario actualizado a PRO

---

### 6️⃣ FUNCIONALIDAD PREMIUM (5 min)

**Chat ilimitado:**
- [ ] Enviar mensaje 1: "Quiero enfocar brazos"
- [ ] Verificar respuesta y modificación
- [ ] Enviar mensaje 2: "Añade más volumen a pecho"
- [ ] Verificar respuesta y modificación
- [ ] Enviar mensaje 3, 4, 5... (sin límite)
- [ ] Verificar que no hay modal de upgrade

**Rutina completa visible:**
- [ ] Ir a "Rutina y Dieta"
- [ ] Verificar que se ve TODO sin censura
- [ ] Verificar modificaciones aplicadas

**✅ ESPERADO:** Chat ilimitado + rutina completa visible

---

### 7️⃣ MODIFICACIONES DINÁMICAS AVANZADAS (10 min)

**Lesión de cuádriceps:**
- [ ] Mensaje: "Me lesioné el cuádriceps"
- [ ] Verificar que elimina: sentadillas, zancadas, prensa
- [ ] Verificar que añade: leg press, curl femoral, puente de glúteos
- [ ] Verificar notificación con cambios

**Enfoque en área específica:**
- [ ] Mensaje: "Quiero enfocar más en pectorales"
- [ ] Verificar que añade ejercicios de pecho
- [ ] Verificar aumento de volumen/series

**Cambio de peso:**
- [ ] Mensaje: "He ganado 3kg, recalcula mi dieta"
- [ ] Verificar que ajusta calorías
- [ ] Verificar que recalcula macros
- [ ] Verificar cambios en cantidades de comida

**Sustitución de alimento:**
- [ ] Mensaje: "No me gusta el pollo, sustitúyelo"
- [ ] Verificar que reemplaza pollo por alternativa (pavo, pescado)
- [ ] Verificar que mantiene macros similares

**Deshacer cambios:**
- [ ] En notificación, hacer clic en "Deshacer Cambios"
- [ ] Verificar que restaura plan anterior
- [ ] Verificar notificación de confirmación

**✅ ESPERADO:** Todas las modificaciones funcionan y son reversibles

---

### 8️⃣ RESPONSIVE MOBILE (3 min)
- [ ] Abrir dashboard en navegador móvil o DevTools responsive
- [ ] Verificar que todo se adapta correctamente:
  - Chat funcional
  - Botones accesibles
  - Rutina/dieta legible
  - Modales centrados
- [ ] Probar flujo completo en móvil

**✅ ESPERADO:** UX excelente en mobile

---

### 9️⃣ PERSISTENCIA DE DATOS (2 min)
- [ ] Cerrar sesión (logout)
- [ ] Volver a hacer login
- [ ] Verificar que:
  - Plan sigue ahí
  - Modificaciones guardadas
  - Estado premium conservado
  - Historial de chat (opcional)

**✅ ESPERADO:** Datos persisten correctamente

---

### 🔟 CASOS EDGE / ERRORES (5 min)

**Sin conexión a internet:**
- [ ] Desconectar internet
- [ ] Intentar enviar mensaje
- [ ] Verificar error amigable

**API key inválida:**
- [ ] (Solo si quieres testear) Cambiar API key en .env
- [ ] Verificar error claro para el usuario

**Usuario sin plan:**
- [ ] Usuario nuevo sin completar onboarding
- [ ] Verificar que no puede acceder a dashboard

**Rate limiting:**
- [ ] Enviar mensajes muy rápido (< 2 segundos)
- [ ] Verificar que previene spam

**✅ ESPERADO:** Manejo elegante de errores

---

## 📊 RESUMEN DE TESTING

**Total estimado:** ~45 minutos

**Criterios de éxito:**
- ✅ Flujo completo funciona sin errores críticos
- ✅ Modificaciones dinámicas funcionan
- ✅ Freemium limit funciona correctamente
- ✅ Pago Stripe procesa correctamente
- ✅ UX es fluida y profesional

**Si todo pasa:** ✅ Listo para añadir RAG/nuevas features
**Si hay errores:** 🔧 Fix primero antes de continuar

---

## 🐛 BUGS ENCONTRADOS

### Bug #1: [Descripción]
- **Reproducir:** [Pasos]
- **Esperado:** [Comportamiento correcto]
- **Actual:** [Lo que pasa]
- **Prioridad:** Alta/Media/Baja
- **Status:** Pendiente/En progreso/Resuelto

### Bug #2: [Descripción]
...

---

## 📝 NOTAS DEL TESTING

[Espacio para notas durante el testing]

---

**Fecha:** 7 Enero 2025
**Testeador:** Gonzalo
**Versión:** Pre-lanzamiento v0.9
