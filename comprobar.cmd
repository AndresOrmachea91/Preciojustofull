@echo off
rem Comprobacion previa a la demo: dice si backend\.env conecta a la base y
rem si los datos estan donde tienen que estar. No escribe nada.
setlocal
cd /d "%~dp0backend"
set "PY=%~dp0backend\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
title PrecioJusto - comprobacion previa

"%PY%" -m src.infraestructura.adaptadores.entrada.cli.estado
if errorlevel 1 echo  ^(revisar lo de arriba antes de presentar^)
echo.
pause
