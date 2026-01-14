# 📝 INSTRUCCIONES: Crear archivo .env

## ⚠️ IMPORTANTE
El archivo `.env` fue eliminado porque estaba corrupto. Sigue estos pasos para crear uno nuevo:

## 🔧 PASOS PARA CREAR .env

### 1. Crear archivo manualmente
En la carpeta `Backend/`, crea un nuevo archivo llamado `.env` (con el punto al inicio)

**Opción A - Usando PowerShell:**
```powershell
cd Backend
New-Item -Path .env -ItemType File
```

**Opción B - Usando tu editor:**
- Abre VSCode / tu editor
- Crea nuevo archivo en `Backend/.env`
- Guarda el archivo

### 2. Copiar este contenido en el archivo

```
ENVIRONMENT=development
OPENAI_API_KEY=tu-api-key-aqui
# Modelo de OpenAI para generación de planes y chat
# Opciones: "gpt-4o" (mejor calidad, más caro) o "gpt-3.5-turbo" (más económico)
OPENAI_MODEL=gpt-4o
DATABASE_URL=sqlite:///./gymai.db
SECRET_KEY=tu-secret-key-aqui
```

### 3. Reemplazar valores

**OPENAI_API_KEY:**
- Ve a: https://platform.openai.com/api-keys
- Crea una nueva key (o usa la existente)
- Copia y pega en el archivo

**OPENAI_MODEL:**
- Opciones: `gpt-4o` (mejor calidad, más caro) o `gpt-3.5-turbo` (más económico)
- **Costos:**
  - gpt-4o: $5.00 / 1M input tokens, $15.00 / 1M output tokens
  - gpt-3.5-turbo: $0.50 / 1M input tokens, $1.50 / 1M output tokens
  - Diferencia: ~10x más barato gpt-3.5-turbo
- **Recomendación:**
  - Para reducir costos al 10% sin perder mucha calidad: `OPENAI_MODEL=gpt-3.5-turbo`
  - Para máxima calidad y estás dispuesto a pagar más: `OPENAI_MODEL=gpt-4o`

**SECRET_KEY:**
- Puede ser cualquier string largo y aleatorio
- Ejemplo: `mi-super-secret-key-123456789`

### 4. Verificar que funciona

Reinicia el servidor y busca esta línea en los logs:
```
💡 Usando GPT-3.5 Turbo para DESARROLLO (20x más barato)
```

Si ves esa línea, ¡todo está funcionando! ✅

## 📋 EJEMPLO COMPLETO

Tu archivo `.env` debería verse así:

```
ENVIRONMENT=development
OPENAI_API_KEY=sk-proj-abc123def456...
# Modelo de OpenAI para generación de planes y chat
# Opciones: "gpt-4o" (mejor calidad, más caro) o "gpt-3.5-turbo" (más económico)
OPENAI_MODEL=gpt-4o
DATABASE_URL=sqlite:///./gymai.db
SECRET_KEY=mi-secret-key-super-segura-2024
```

## 🚫 ERRORES COMUNES

❌ **NO** incluyas espacios alrededor del `=`:
```
ENVIRONMENT = development  ❌ (mal)
ENVIRONMENT=development    ✅ (bien)
```

❌ **NO** uses comillas:
```
OPENAI_API_KEY="sk-..."  ❌ (mal)
OPENAI_API_KEY=sk-...    ✅ (bien)
```

❌ **NO** incluyas comentarios en la misma línea:
```
ENVIRONMENT=development # comentario  ❌ (mal)
# comentario
ENVIRONMENT=development                ✅ (bien)
```

## ✅ VERIFICACIÓN

Después de crear el archivo:

1. El servidor debería mostrar:
   ```
   💡 Usando GPT-3.5 Turbo para DESARROLLO (20x más barato)
   ```

2. Si ves errores, revisa que:
   - El archivo se llama exactamente `.env` (con el punto)
   - Está en la carpeta `Backend/`
   - No tiene espacios extra
   - La API key es válida

## 🆘 SI SIGUE SIN FUNCIONAR

El servidor funcionará con valores por defecto:
- `ENVIRONMENT=development` (GPT-3.5 Turbo)
- Usará variables de sistema si existen

**No es crítico** tener el archivo `.env` si ya tienes las variables de entorno configuradas en tu sistema.
