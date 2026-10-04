@echo off
REM ============================================================
REM  KRB Assistant - iniciar (janela de terminal fica aberta
REM  para vermos mensagens de erro durante os testes)
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente nao instalado. Execute primeiro: instalar.bat
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m app.main
if errorlevel 1 (
    echo.
    echo O programa terminou com erro. Veja logs\errors.log
    pause
)
