# 🌍 CONFIGURACIÓN DE AMBIENTE

## 📋 Variables de Entorno

Crea un archivo `.env` en `Backend/` con las siguientes variables:

```bash
# 🌍 AMBIENTE (development o production)
# development = GPT-3.5 Turbo (~$0.0015/1K tokens - 20x más barato)
# production = GPT-4 Turbo (~$0.03/1K tokens)
ENVIRONMENT=development

# 🔑 OPENAI API KEY
# Regenerar en: https://platform.openai.com/api-keys
OPENAI_API_KEY=your-api-key-here

# 💾 DATABASE
DATABASE_URL=sqlite:///./gymai.db

# 🔐 JWT SECRET
SECRET_KEY=your-secret-key-here

# 💳 STRIPE (opcional)
STRIPE_SECRET_KEY=your-stripe-key-here
STRIPE_PUBLISHABLE_KEY=your-stripe-publishable-key-here
```

## 💰 Costos por Modelo

| Modelo | Input | Output | Uso Recomendado |
|--------|-------|--------|-----------------|
| **GPT-3.5 Turbo** | $0.0015/1K | $0.002/1K | ✅ Desarrollo/Testing |
| **GPT-4 Turbo** | $0.01/1K | $0.03/1K | 🚀 Producción |

## 🔧 Configuración por Ambiente

### 💡 DESARROLLO (Recomendado)
```bash
ENVIRONMENT=development
```
- Usa **GPT-3.5 Turbo** (20x más barato)
- Ideal para testing y desarrollo
- Costo estimado: ~$2-5/día

### 🚀 PRODUCCIÓN
```bash
ENVIRONMENT=production
```
- Usa **GPT-4 Turbo** (mejor calidad)
- Para usuarios reales
- Costo estimado: ~$50-100/día

## ⚠️ SEGURIDAD

### 1. Regenerar API Key
Si crees que tu API key está comprometida:
1. Ve a https://platform.openai.com/api-keys
2. Haz clic en "Create new secret key"
3. Copia la nueva key
4. Actualiza tu archivo `.env`
5. Revoca la key antigua

### 2. Establecer Límites de Gasto
Para evitar sorpresas:
1. Ve a https://platform.openai.com/account/billing/limits
2. Establece límite mensual:
   - **Desarrollo**: $5-10/mes
   - **Producción**: $50-100/mes (según tráfico)

### 3. Monitoreo
Revisa tu consumo diariamente en:
https://platform.openai.com/usage

## 🚀 Cómo Cambiar de Ambiente

### Durante Desarrollo:
```bash
# En tu .env
ENVIRONMENT=development
```

### Al Lanzar a Producción:
```bash
# En tu .env de producción
ENVIRONMENT=production
```

### Verificar Ambiente Activo:
Mira los logs del servidor al iniciar:
```
💡 Usando GPT-3.5 Turbo para DESARROLLO (20x más barato)
```
o
```
🚀 Usando GPT-4 Turbo para PRODUCCIÓN
```

## 📊 Ahorro Estimado

Con todas las optimizaciones implementadas:

| Métrica | Antes | Después (Dev) | Ahorro |
|---------|-------|---------------|--------|
| **Modelo** | GPT-4 | GPT-3.5 | 20x |
| **Historial** | Ilimitado | 10 mensajes | 80% |
| **Duplicados** | 53 | 0 | 83% |
| **Total** | ~$600/día | ~$2-5/día | **~99%** |

## 🎯 Recomendaciones

1. ✅ **Siempre** usa `development` para testing
2. ✅ **Solo** cambia a `production` cuando lances
3. ✅ **Monitorea** el consumo diariamente
4. ✅ **Establece** límites de gasto
5. ✅ **Revisa** los logs de tokens en tiempo real
