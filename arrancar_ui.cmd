@echo off
rem Solo la interfaz (vite en :5173). arrancar.cmd lo usa; tambien sirve solo.
rem Lee frontend\.env.local: VITE_ORIGEN_DATOS=http (API) o memoria (plan B).
cd /d "%~dp0frontend"
title PrecioJusto UI - http://localhost:5173  (cerrar esta ventana apaga la interfaz)
call npm run dev
echo.
echo  La interfaz se detuvo. Si fue un error, leelo arriba. Esta ventana queda abierta.
pause
