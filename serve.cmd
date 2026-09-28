@echo off
rem =====================================================================
rem  PrecioJusto - servidor de desarrollo
rem
rem      serve.cmd            interfaz + API contra la base real
rem      serve.cmd memoria    datos fijos, sin base ni internet (PLAN B)
rem      serve.cmd 9000       en otro puerto
rem
rem  Igual que "php artisan serve": un comando, imprime el enlace y se
rem  queda corriendo. La interfaz la sirve el mismo proceso de FastAPI.
rem =====================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "MODO=http"
set "PUERTO=8000"
for %%a in (%*) do (
  if /i "%%a"=="memoria" (set "MODO=memoria") else (set "PUERTO=%%a")
)

set "PY=%~dp0backend\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
title PrecioJusto - servidor (:%PUERTO%)

rem --- Requisitos, con mensajes en castellano --------------------------
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
netstat -ano | findstr /r /c:":%PUERTO% .*LISTENING" >nul 2>&1
if not errorlevel 1 (
  echo  [X] El puerto %PUERTO% ya esta ocupado. Ver quien lo tiene y cerrarlo:
  echo        netstat -ano ^| findstr :%PUERTO%
  echo        taskkill /F /PID ^<pid^>
  echo      O usar otro puerto:  serve.cmd 9000
  goto :fin_error
)
if not exist "backend\.env" (
  echo  [!] Sin backend\.env: la API usara datos de ejemplo en memoria.
  echo      Crearlo con:  copy backend\.env.example backend\.env
)

rem --- Construir la interfaz solo si hace falta -------------------------
"%PY%" "%~dp0herramientas\necesita_build.py" %MODO% >"%TEMP%\preciojusto_build_check.txt"
rem OJO: "set /p" pisa el errorlevel, asi que se guarda ANTES de leer el motivo.
set "RECONSTRUIR=%ERRORLEVEL%"
set /p MOTIVO=<"%TEMP%\preciojusto_build_check.txt"
if "%RECONSTRUIR%"=="1" (
  echo  Construyendo la interfaz ^(%MOTIVO%; modo de datos: %MODO%^)...
  pushd frontend
  set "VITE_ORIGEN_DATOS=%MODO%"
  set "VITE_API_URL=/api/v1"
  call npm run build >"%TEMP%\preciojusto_build.log" 2>&1
  if errorlevel 1 (
    popd
    echo  [X] Fallo la construccion de la interfaz:
    type "%TEMP%\preciojusto_build.log"
    goto :fin_error
  )
  popd
  >"frontend\dist\.modo" echo %MODO%
) else (
  echo  Interfaz lista ^(%MOTIVO%^).
)

rem --- Banner y arranque -----------------------------------------------
echo.
echo   PrecioJusto - servidor de desarrollo
echo.
echo     Aplicacion:  http://localhost:%PUERTO%
echo     API ^(docs^):  http://localhost:%PUERTO%/docs
echo     Datos:       %MODO%
echo.
echo     Ctrl+C para detener
echo.
cd backend
"%PY%" -m uvicorn src.infraestructura.adaptadores.entrada.api.main:app --port %PUERTO%
cd ..
echo.
echo  Servidor detenido.
exit /b 0

:fin_error
echo.
echo  No se arranco nada. Corregir lo de arriba y volver a ejecutar.
echo.
exit /b 1
