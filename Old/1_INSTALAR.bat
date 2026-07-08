@echo off
chcp 65001 >nul
echo.
echo ═══════════════════════════════════════════════════
echo   LABVIMA → Google Sheets   Instalador
echo ═══════════════════════════════════════════════════
echo.
python --version >nul 2>&1
if errorlevel 1 (
    echo  ✗ Python no instalado.
    echo    Descargalo en https://www.python.org/downloads/
    echo    Tildar "Add Python to PATH" durante la instalacion
    pause & exit /b 1
)
echo  ✓ Python OK
echo.
echo  Instalando librerias...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  ✗ Error instalando librerias. Revisa tu conexion.
    pause & exit /b 1
)
echo.
echo ═══════════════════════════════════════════════════
echo  ✓ Instalacion lista
echo.
echo  SEGUIR CON EL LEEME.txt — Paso 2 en adelante
echo ═══════════════════════════════════════════════════
echo.
pause
