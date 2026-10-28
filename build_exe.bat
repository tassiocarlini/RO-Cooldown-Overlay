@echo off
REM Gera o .exe localmente (opcional; o GitHub ja faz isso sozinho ao publicar uma Release).
cd /d "%~dp0"
python -m pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean --windowed --name "RO Cooldown Overlay" --add-data "banco_skills.json;." --collect-data sv_ttk --icon assets\icone.ico ro_cooldown_overlay.py
copy /Y LEIA-ME.txt "dist\RO Cooldown Overlay\"
echo.
echo Pronto! O programa esta em: dist\RO Cooldown Overlay
pause
