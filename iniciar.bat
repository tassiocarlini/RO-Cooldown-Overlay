@echo off
setlocal EnableExtensions EnableDelayedExpansion
title RO Cooldown Overlay
cd /d "%~dp0"
set "LOG=%~dp0instalacao.log"
echo [%date% %time%] Inicio > "%LOG%"

REM ============================================================
REM  Abre o RO Cooldown Overlay pelo Python.
REM  Se o Python ou as bibliotecas nao estiverem instalados,
REM  instala tudo sozinho na primeira vez.
REM ============================================================

call :achar_python
if not defined PY (
    echo.
    echo  O Python nao esta instalado neste computador.
    echo  Vou instalar agora. Isso so acontece na primeira vez e leva alguns minutos.
    echo.
    call :instalar_python
    call :achar_python
)
if not defined PY goto :falhou_python
echo Python encontrado: !PY! >> "%LOG%"

"!PY!" -c "import tkinter, mss, PIL, numpy, cv2, sv_ttk" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  Instalando as bibliotecas do programa. So na primeira vez, aguarde...
    echo.
    "!PY!" -m pip install --disable-pip-version-check --upgrade pip >> "%LOG%" 2>&1
    "!PY!" -m pip install --disable-pip-version-check -r "%~dp0requirements.txt" >> "%LOG%" 2>&1
    "!PY!" -c "import tkinter, mss, PIL, numpy, cv2, sv_ttk" >> "%LOG%" 2>&1
    if errorlevel 1 goto :falhou_bibliotecas
)

set "PYW=!PY:python.exe=pythonw.exe!"
if exist "!PYW!" (
    start "" "!PYW!" "%~dp0ro_cooldown_overlay.py"
) else (
    start "" "!PY!" "%~dp0ro_cooldown_overlay.py"
)
echo Programa aberto. >> "%LOG%"
exit /b 0


:achar_python
REM Procura um Python 3.10 ou mais novo que funcione de verdade
set "PY="
for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable) if sys.version_info >= (3, 10) else None" 2^>nul') do set "PY=%%P"
if defined PY if exist "!PY!" goto :eof
set "PY="
for /f "delims=" %%P in ('python -c "import sys; print(sys.executable) if sys.version_info >= (3, 10) else None" 2^>nul') do set "PY=%%P"
if defined PY if exist "!PY!" goto :eof
set "PY="
for %%V in (313 312 311 310) do (
    if not defined PY if exist "%LocalAppData%\Programs\Python\Python%%V\python.exe" set "PY=%LocalAppData%\Programs\Python\Python%%V\python.exe"
)
goto :eof


:instalar_python
where winget >nul 2>&1
if not errorlevel 1 (
    echo  Instalando o Python pelo winget, o instalador do Windows...
    winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements >> "%LOG%" 2>&1
    call :achar_python
    if defined PY goto :eof
)
echo  Baixando o Python do site oficial python.org...
set "INST=%TEMP%\python-3.12.10-amd64.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile $env:INST" >> "%LOG%" 2>&1
if not exist "%INST%" goto :eof
echo  Instalando o Python, aguarde...
"%INST%" /quiet InstallAllUsers=0 InstallLauncherAllUsers=0 PrependPath=1 Include_launcher=1 Include_tcltk=1 Include_pip=1 Include_test=0 >> "%LOG%" 2>&1
del "%INST%" >nul 2>&1
goto :eof


:falhou_python
echo.
echo  ------------------------------------------------------------
echo  Nao consegui instalar o Python automaticamente.
echo.
echo  Instale o Python em https://www.python.org/downloads/
echo  marcando "Add python.exe to PATH" e abra este arquivo de novo.
echo.
echo  Detalhes do erro em: instalacao.log
echo  ------------------------------------------------------------
pause
exit /b 1


:falhou_bibliotecas
echo.
echo  ------------------------------------------------------------
echo  Nao consegui instalar as bibliotecas do programa.
echo  Confira sua internet e tente de novo.
echo  Se continuar, envie o arquivo instalacao.log para quem te passou o programa.
echo  ------------------------------------------------------------
pause
exit /b 1
