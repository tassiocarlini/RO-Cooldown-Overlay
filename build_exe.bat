@echo off
REM Gera o .exe no seu PC (opcional: o GitHub ja gera sozinho a cada versao nova na main).
cd /d "%~dp0"
python -m pip install -r requirements.txt pyinstaller==6.22.3
python empacotar.py
echo.
echo O programa esta em: dist\RO Cooldown Overlay
pause
