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
# /fotos es del usuario de la app: el volumen nuevo hereda este dueño y las
# fotos de los puestos se pueden guardar sin root.
RUN useradd --system --no-create-home preciojusto     && mkdir -p /fotos && chown preciojusto:preciojusto /fotos
USER preciojusto

EXPOSE 8000
# --proxy-headers: detrás de Caddy, la IP real de quien llama viene en
# X-Forwarded-For; el límite de intentos la necesita para no contar a todos
# como si fueran el proxy.
CMD ["python", "-m", "uvicorn", "src.infraestructura.adaptadores.entrada.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
