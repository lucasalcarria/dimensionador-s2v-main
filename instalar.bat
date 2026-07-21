@echo off
chcp 65001 >nul
cd /d %~dp0
echo Instalando dependencias do Dimensionador S2V (so na primeira vez)...
py -3 -m pip install --upgrade pip >nul 2>&1
py -3 -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo [ERRO] Instale o Python 3.10+ em https://www.python.org/downloads/
  echo        e marque a opcao "Add python.exe to PATH" durante a instalacao.
)
echo.
pause
