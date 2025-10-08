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
DATABASE_URL=sqlite:///./gymai.db
SECRET_KEY=tu-secret-key-aqui
```

### 3. Reemplazar valores

**OPENAI_API_KEY:**
- Ve a: https://platform.openai.com/api-keys
- Crea una nueva key (o usa la existente)
- Copia y pega en el archivo

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
