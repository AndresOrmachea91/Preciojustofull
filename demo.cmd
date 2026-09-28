@echo off
rem =====================================================================
rem  PrecioJusto - UN SOLO SERVIDOR (como "mvn spring-boot:run")
rem
rem      demo.cmd            interfaz + API contra la base real
rem      demo.cmd memoria    interfaz sin backend de datos (PLAN B)
rem
rem  Construye la interfaz (npm run build) y la sirve el MISMO proceso de
rem  FastAPI: un puerto, una ventana, sin CORS, sin Vite aparte.
rem
rem      Todo:  http://localhost:8000
rem      API:   http://localhost:8000/docs
rem =====================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title PrecioJusto - servidor unico

set "MODO=http"
if /i "%~1"=="memoria" set "MODO=memoria"

set "PY=%~dp0backend\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo.
echo  PrecioJusto - preparando ^(modo de datos: %MODO%^)
echo  ------------------------------------------------

"%PY%" --version >nul 2>&1 || (
  echo  [X] No se encuentra Python. Instalar Python 3.11+ desde python.org.
  goto :fin_error
)
"%PY%" -c "import uvicorn, fastapi, sqlalchemy, pydantic_settings, psycopg2" >nul 2>&1 || (
  echo  [X] Faltan dependencias del backend. Instalar con:
  echo        "%PY%" -m pip install -r backend\requirements.txt
  goto :fin_error
)
where npm >nul 2>&1 || (
  echo  [X] No se encuentra npm. Instalar Node.js LTS desde nodejs.org.
  goto :fin_error
)
if not exist "frontend\node_modules" (
  echo  [X] Falta frontend\node_modules. Instalar con:  cd frontend ^&^& npm install
  goto :fin_error
)
if not exist "backend\.env" (
  echo  [!] No hay backend\.env: la API usaria datos de ejemplo en memoria.
  echo      Crearlo con:  copy backend\.env.example backend\.env
)

rem --- Construir la interfaz ------------------------------------------
rem En modo http la interfaz pide al MISMO origen, asi que no necesita
rem VITE_API_URL. En modo memoria no pide nada: los datos son fijos.
echo.
echo  Construyendo la interfaz ^(un minuto la primera vez^)...
cd frontend
set "VITE_ORIGEN_DATOS=%MODO%"
rem Ruta RELATIVA a proposito: el mismo build sirve en cualquier puerto y
rem tambien desde otra maquina de la sala (http://192.168.x.x:8000).
set "VITE_API_URL=/api/v1"
call npm run build >"%TEMP%\preciojusto_build.log" 2>&1
if errorlevel 1 (
  cd ..
  echo  [X] Fallo la construccion de la interfaz. Detalle:
  type "%TEMP%\preciojusto_build.log" | more +1
  goto :fin_error
)
cd ..
echo  [OK] Interfaz construida en frontend\dist

rem --- Puerto libre ----------------------------------------------------
netstat -ano | findstr /r /c:":8000 .*LISTENING" >nul 2>&1
if not errorlevel 1 (
  echo.
  echo  [X] El puerto 8000 ya esta ocupado. Cerrar lo que este corriendo:
  echo        netstat -ano ^| findstr :8000      ^(anotar el PID^)
  echo        taskkill /F /PID ^<pid^>
  goto :fin_error
)

rem --- Arrancar --------------------------------------------------------
echo.
echo  Arrancando el servidor. Cuando diga "Application startup complete":
echo.
echo      Todo:  http://localhost:8000
echo      API:   http://localhost:8000/docs
echo.
echo  Para detenerlo: Ctrl+C, o cerrar esta ventana.
echo.
start "" http://localhost:8000
cd backend
"%PY%" -m uvicorn src.infraestructura.adaptadores.entrada.api.main:app --port 8000
cd ..
echo.
echo  El servidor se detuvo.
pause
exit /b 0

:fin_error
echo.
echo  No se arranco nada. Corregir lo de arriba y volver a ejecutar demo.cmd
echo.
pause
exit /b 1
