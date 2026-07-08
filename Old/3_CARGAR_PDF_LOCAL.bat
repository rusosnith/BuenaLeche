@echo off
chcp 65001 >nul
echo.
echo ═══════════════════════════════════════════════════
echo   LABVIMA → Google Sheets   Cargar PDF local
echo   Arrastra un PDF de LABVIMA sobre este archivo
echo ═══════════════════════════════════════════════════
echo.
cd /d "%~dp0"
if "%~1"=="" (
    echo  Uso: arrasta un PDF de LABVIMA sobre este .bat
    pause & exit /b 0
)
python labvima_sync.py --pdf "%~1"
echo.
pause
