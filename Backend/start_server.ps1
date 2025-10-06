# GYMAI - Script de inicio del servidor
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    GYMAI - Iniciando Servidor" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Cambiar al directorio del script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Activar entorno virtual
Write-Host "Activando entorno virtual..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Verificar directorio actual
Write-Host "Directorio actual: $(Get-Location)" -ForegroundColor Green

# Verificar que el módulo app existe
Write-Host "Verificando módulo app.main..." -ForegroundColor Yellow
try {
    python -c "import app.main; print('✓ Módulo app.main importado correctamente')"
    if ($LASTEXITCODE -ne 0) {
        throw "Error al importar módulo"
    }
} catch {
    Write-Host "✗ Error: No se puede importar app.main" -ForegroundColor Red
    Write-Host "Asegúrate de estar en el directorio Backend" -ForegroundColor Red
    Read-Host "Presiona Enter para salir"
    exit 1
}

# Iniciar servidor
Write-Host ""
Write-Host "Iniciando servidor en puerto 8001..." -ForegroundColor Green
Write-Host "URL: http://127.0.0.1:8001" -ForegroundColor Green
Write-Host "Presiona Ctrl+C para detener el servidor" -ForegroundColor Yellow
Write-Host ""

python -m uvicorn app.main:app --host 127.0.0.1 --port 8001





