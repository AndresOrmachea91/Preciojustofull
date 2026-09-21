# PrecioJusto Bolivia

Plataforma de inteligencia de precios de la canasta familiar para La Paz.

Integra fuentes oficiales de precios, reportes de comerciantes y reportes
ciudadanos con fotografía y OCR; consolida las fuentes en conflicto con un
motor de fusión que asigna niveles de confianza, estima precios donde no hay
datos y predice el impacto de los bloqueos de rutas sobre productos
específicos.

Proyecto integrador de Ingeniería de Sistemas.

## Este repositorio

Monorepo. Dos aplicaciones desplegables, una arquitectura.

    backend/    FastAPI + Python — API REST, motor de fusión, recolector
    frontend/   React 19 + TypeScript — comparador, canasta y mapa

Cada carpeta conserva el historial completo de su repositorio de origen
(`preciojusto-backend` y `preciojusto-frontend`), importado con `git subtree`.

## La regla que sostiene todo

Las dos aplicaciones siguen la misma arquitectura (Clean + Hexagonal) y las
dependencias apuntan **siempre hacia adentro**:

    infraestructura  ->  aplicacion  ->  dominio

- `dominio/` no importa nada de fuera. Ni FastAPI, ni SQLAlchemy, ni React.
- `aplicacion/` importa solo `dominio` y sus propios puertos (interfaces).
- `infraestructura/` importa lo que quiera: es el borde del sistema.

No es una convención de estilo: hay pruebas automatizadas que leen los
archivos y fallan si alguien la rompe. En el backend,
`backend/tests/test_arquitectura.py`.

Consecuencia práctica, medida: actualizar el frontend de React 18 a React 19
no tocó una sola línea de dominio ni de aplicación.

## Cómo correrlo todo con un solo comando

    arrancar.cmd

Levanta la API en `http://localhost:8000` (uvicorn, con recarga) y la
interfaz en `http://localhost:5173` (vite) apuntando a esa API, cada una en
su ventana. Requiere `backend\.venv` con `requirements.txt` instalado y
`frontend
ode_modules` (`npm install`); el script avisa si falta alguno.

Con `BASE_DATOS_URL` definida (en `backend\.env` o en el entorno) la API usa
esa base y el mapa muestra los 88 puntos de venta reales con sus precios;
sin ella arranca con los repositorios en memoria.

Para trabajar el frontend sin backend: `cd frontend && npm run dev` con
`VITE_ORIGEN_DATOS=memoria` (el valor por defecto de `.env.example`). Pasar
de memoria a la API real es cambiar esa variable a `http`: ningún componente
se entera.

## Stack

| Pieza | Elección |
|---|---|
| API | FastAPI (Python) |
| Interfaz | React 19 + TypeScript |
| Relacional | PostgreSQL (Neon) |
| Documental | MongoDB — respuestas crudas de fuentes, fotos y resultados de OCR |
| Imágenes | S3 |
| OCR | AWS Textract, detrás de un puerto, con adaptador local de respaldo |
| Mapas | Leaflet + OpenStreetMap |
| Modelo | scikit-learn |

## Cómo correrlo

    # backend
    cd backend
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    pytest
    uvicorn src.infraestructura.adaptadores.entrada.api.main:app --reload

    # frontend
    cd frontend
    npm ci
    npm test
    npm run dev

## Integración continua

Dos workflows independientes, cada uno disparado solo por cambios en su
carpeta: `.github/workflows/backend.yml` y `.github/workflows/frontend.yml`.
Tocar el frontend no vuelve a correr las pruebas de Python.
