@echo off
chcp 65001 >nul
echo.
echo ═══════════════════════════════════════════════════
echo   LABVIMA → Google Sheets   Sincronizar
echo ═══════════════════════════════════════════════════
echo.
cd /d "%~dp0"
python labvima_sync.py
echo.
pause
