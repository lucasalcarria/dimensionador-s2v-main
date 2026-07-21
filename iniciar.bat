@echo off
chcp 65001 >nul
cd /d %~dp0
echo Abrindo o Dimensionador S2V... (deixe esta janela aberta)
py -3 app.py
if errorlevel 1 (
  echo.
  echo [ERRO] Se for o primeiro uso, execute antes o instalar.bat
)
pause
