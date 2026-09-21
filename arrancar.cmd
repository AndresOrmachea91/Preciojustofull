@echo off
rem =====================================================================
rem  PrecioJusto - arranque completo con doble clic (Windows)
rem
rem    API       http://localhost:8000/docs
rem    Interfaz  http://localhost:5173
rem
rem  La configuracion sale de archivos, no de la terminal:
rem    backend\.env          (copiar de backend\.env.example)
rem    frontend\.env.local   (copiar de frontend\.env.example)
rem
rem  Cada paso se verifica antes de arrancar y, si falta algo, este
rem  script lo dice con un mensaje claro en vez de morir con un error de
rem  Python. Cualquier error deja la ventana abierta.
rem =====================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title PrecioJusto - arranque

echo.
echo  PrecioJusto - verificando antes de arrancar
echo  -------------------------------------------

set "PY=%~dp0backend\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" --version >nul 2>&1
if errorlevel 1 (
  echo  [X] No se encuentra Python. Instala Python 3.11 o superior desde python.org
  echo      y marca "Add python to PATH".
  goto :fin_error
)
for /f "tokens=*" %%v in ('"%PY%" --version 2^>^&1') do echo  [OK] %%v  ^(%PY%^)

rem --- 2. Dependencias del backend
"%PY%" -c "import uvicorn, fastapi, sqlalchemy, pydantic_settings, psycopg2" >nul 2>&1
if errorlevel 1 (
  echo  [X] Faltan dependencias del backend. Instalalas con:
  echo.
  echo        cd backend
  echo        %PY% -m pip install -r requirements.txt
  echo.
  echo      Si psycopg2-binary falla al compilar, Python es 3.13 y requirements.txt
  echo      ya pide ^>=2.9.10, que trae wheel para 3.13. Repite el comando.
  goto :fin_error
)
echo  [OK] Dependencias del backend instaladas

rem --- 3. backend\.env
if not exist "backend\.env" (
  echo  [X] Falta backend\.env. Crealo asi y completa BASE_DATOS_URL con la cadena de Neon:
  echo.
  echo        copy backend\.env.example backend\.env
  echo.
  echo      Con BASE_DATOS_URL vacia la API arranca igual, pero con datos de ejemplo
  echo      en memoria, no con los 88 puntos reales.
  goto :fin_error
)
findstr /b /c:"BASE_DATOS_URL=postgres" "backend\.env" >nul 2>&1
if errorlevel 1 (
  echo  [!] backend\.env existe pero BASE_DATOS_URL esta vacia: la API va a arrancar
  echo      con repositorios en memoria ^(4 mercados de ejemplo^), no con la base real.
) else (
  echo  [OK] backend\.env con BASE_DATOS_URL definida
)

rem --- 4. Node y dependencias del frontend
where npm >nul 2>&1
if errorlevel 1 (
  echo  [X] No se encuentra npm. Instala Node.js LTS desde nodejs.org
  goto :fin_error
)
if not exist "frontend\node_modules" (
  echo  [X] Falta frontend\node_modules. Instalalo con:
  echo.
  echo        cd frontend
  echo        npm install
  goto :fin_error
)
echo  [OK] Dependencias del frontend instaladas

rem --- 5. frontend\.env.local
if not exist "frontend\.env.local" (
  echo  [X] Falta frontend\.env.local. Crealo asi:
  echo.
  echo        copy frontend\.env.example frontend\.env.local
  echo.
  echo      VITE_ORIGEN_DATOS=http usa la API; =memoria corre sin backend ^(plan B^).
  goto :fin_error
)
for /f "tokens=2 delims==" %%m in ('findstr /b /c:"VITE_ORIGEN_DATOS=" "frontend\.env.local"') do set "MODO=%%m"
echo  [OK] frontend\.env.local con VITE_ORIGEN_DATOS=!MODO!

rem --- 6. Puertos libres
netstat -ano | findstr /r /c:":8000 .*LISTENING" >nul 2>&1
if not errorlevel 1 (
  echo  [!] El puerto 8000 ya esta en uso: probablemente la API ya esta corriendo.
  echo      Si no es asi, cierra el proceso ^(netstat -ano ^| findstr :8000 ^) y vuelve a intentar.
)
netstat -ano | findstr /r /c:":5173 .*LISTENING" >nul 2>&1
if not errorlevel 1 (
  echo  [!] El puerto 5173 ya esta en uso: probablemente la interfaz ya esta corriendo.
)

rem --- 7. Arrancar, cada uno en su ventana
echo.
echo  Arrancando...
start "PrecioJusto API" cmd /c "%~dp0arrancar_api.cmd"
start "PrecioJusto UI" cmd /c "%~dp0arrancar_ui.cmd"

echo.
echo  API:       http://localhost:8000/docs
echo  Interfaz:  http://localhost:5173
echo.
echo  Espera unos segundos a que las dos ventanas digan que estan listas.
echo  Esta ventana se puede cerrar.
ping -n 9 127.0.0.1 >nul
start "" http://localhost:5173
exit /b 0

:fin_error
echo.
echo  No se arranco nada. Corrige lo de arriba y vuelve a ejecutar arrancar.cmd
echo.
pause
exit /b 1
