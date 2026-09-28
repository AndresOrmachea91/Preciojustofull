"""
Adaptador de entrada HTTP.

FastAPI es un detalle del borde: se puede reemplazar sin tocar el dominio
ni los casos de uso. Eso es lo que la arquitectura hexagonal compra.
"""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.infraestructura.adaptadores.entrada.api.rutas import canasta, catalogo, precios, reportes
from src.configuracion import config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# La interfaz ya construida (frontend/dist). Si está, este mismo proceso la
# sirve: un solo servidor, un solo puerto, sin CORS y sin levantar Vite
# aparte. Si no está, la API funciona igual y la interfaz se sirve con
# `npm run dev` en 5173, como en desarrollo.
INTERFAZ = Path(__file__).resolve().parents[6] / "frontend" / "dist"

app = FastAPI(
    title="PrecioJusto Bolivia — API",
    description=(
        "Inteligencia de precios de la canasta familiar en La Paz. "
        "Arquitectura hexagonal: esta API es un adaptador de entrada."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.origenes,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalogo.router, prefix="/api/v1")
app.include_router(precios.router, prefix="/api/v1")
app.include_router(canasta.router, prefix="/api/v1")
app.include_router(reportes.router, prefix="/api/v1")


@app.get("/api/v1/salud", tags=["salud"])
def salud():
    return {
        "estado": "ok",
        "entorno": config.app_entorno,
        "interfaz_servida": INTERFAZ.is_dir(),
    }


# Va al FINAL, después de las rutas: montado en "/" se queda con todo lo
# que no reclamó la API, que es exactamente lo que tiene que servir.
if INTERFAZ.is_dir():
    app.mount("/", StaticFiles(directory=INTERFAZ, html=True), name="interfaz")
    log.info("Interfaz servida desde %s", INTERFAZ)
else:
    log.info("Sin interfaz construida en %s: solo API", INTERFAZ)

