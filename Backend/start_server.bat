@echo off
echo ========================================
echo    GYMAI - Iniciando Servidor
echo ========================================

REM Cambiar al directorio del Backend
cd /d "%~dp0"

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Verificar que estamos en el directorio correcto
echo Directorio actual: %CD%
echo.

REM Verificar que el módulo app existe
echo Verificando módulo app.main...
python -c "import app.main; print('✓ Módulo app.main importado correctamente')"
if errorlevel 1 (
    echo.
    echo ✗ Error: No se puede importar app.main
    echo.
    echo Directorio actual: %CD%
    echo.
    echo Verificando archivos...
    dir app
    echo.
    echo Asegúrate de estar en el directorio Backend
    pause
    exit /b 1
)

REM Iniciar servidor
echo.
echo Iniciando servidor en puerto 8000...
echo URL: http://127.0.0.1:8000
echo.
python -m uvicorn main:app --host 127.0.0.1 --port 8000

pause
