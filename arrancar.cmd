@echo off
rem Arranca todo con un solo comando, en Windows:
rem   - la API en http://localhost:8000 (uvicorn, con recarga)
rem   - la interfaz en http://localhost:5173 (vite), apuntando a esa API
rem
rem La API usa la base de BASE_DATOS_URL si esta definida (backend\.env o el
rem entorno); sin ella arranca con los repositorios en memoria, sin datos
rem reales. Para ver los 88 puntos de venta con precios, definila antes.
setlocal
cd /d "%~dp0"

if not exist backend\.venv\Scripts\python.exe (
  echo Falta backend\.venv. Crealo con:
  echo   cd backend ^&^& python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
  exit /b 1
)
if not exist frontend\node_modules (
  echo Falta frontend\node_modules. Instalalo con:  cd frontend ^&^& npm install
  exit /b 1
)

start "PrecioJusto API" cmd /k "cd /d backend && .venv\Scripts\python -m uvicorn src.infraestructura.adaptadores.entrada.api.main:app --reload --port 8000"
start "PrecioJusto UI" cmd /k "cd /d frontend && set VITE_ORIGEN_DATOS=http&& set VITE_API_URL=http://localhost:8000/api/v1&& npm run dev"

echo API:      http://localhost:8000/docs
echo Interfaz: http://localhost:5173
endlocal
