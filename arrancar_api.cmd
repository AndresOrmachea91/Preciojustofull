@echo off
rem Solo la API (uvicorn en :8000). arrancar.cmd lo usa; tambien sirve solo.
cd /d "%~dp0backend"
set "PY=%~dp0backend\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
title PrecioJusto API - http://localhost:8000/docs  (cerrar esta ventana apaga la API)
"%PY%" -m uvicorn src.infraestructura.adaptadores.entrada.api.main:app --reload --port 8000
echo.
echo  La API se detuvo. Si fue un error, leelo arriba. Esta ventana queda abierta.
pause
