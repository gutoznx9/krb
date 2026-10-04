@echo off
REM ============================================================
REM  KRB Assistant - instalacao (rodar uma vez, ou apos atualizar)
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")

%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>nul
if errorlevel 1 (
    echo [ERRO] Python 3.11 ou mais novo nao encontrado.
    echo Instale pelo site https://www.python.org/downloads/ e marque "Add python.exe to PATH".
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual .venv ...
    %PY% -m venv .venv || (echo [ERRO] Falha ao criar ambiente virtual & pause & exit /b 1)
)

echo Instalando dependencias...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt || (echo [ERRO] Falha ao instalar dependencias & pause & exit /b 1)

echo.
echo Rodando testes automaticos...
".venv\Scripts\python.exe" -m unittest discover -s tests

echo.
echo Instalacao concluida. Para abrir o programa: iniciar.bat
pause
