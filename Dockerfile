# Una sola imagen para la API (que también sirve la interfaz) y para el
# recolector: el mismo código, dos comandos distintos en docker-compose.yml.

# --- 1. Interfaz: se construye con Node y solo se conserva el resultado ---
FROM node:24-alpine AS interfaz
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# La API sirve la interfaz desde el mismo origen: la base es relativa.
ENV VITE_ORIGEN_DATOS=http VITE_API_URL=/api/v1
RUN npm run build

# --- 2. Backend: Python con las dependencias y el código -----------------
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt
COPY backend/src ./src
COPY backend/datos ./datos
# main.py busca la interfaz en <raíz>/frontend/dist: se respeta esa ruta.
COPY --from=interfaz /app/frontend/dist /app/frontend/dist

# Sin privilegios de root dentro del contenedor.
RUN useradd --system --no-create-home preciojusto
USER preciojusto

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.infraestructura.adaptadores.entrada.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
