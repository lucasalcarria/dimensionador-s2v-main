@echo off
chcp 65001 >nul
REM Gera um executavel unico (DimensionadorS2V.exe) que dispensa Python instalado.
REM Rode este script UMA vez, em um Windows com Python 3.10+.
cd /d %~dp0
py -3 -m pip install -r requirements.txt pyinstaller
py -3 -m PyInstaller --noconfirm --onefile --name DimensionadorS2V ^
  --hidden-import qrcode ^
  --add-data "templates;templates" ^
  --add-data "assets;assets" ^
  --add-data "config.json;." ^
  app.py
copy /y config.json dist\config.json >nul
echo.
echo Pronto! O executavel esta em: dist\DimensionadorS2V.exe
echo Copie o .exe (e o config.json, opcional) para onde quiser usar.
pause
