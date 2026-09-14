"""
Adaptador de entrada HTTP.

FastAPI es un detalle del borde: se puede reemplazar sin tocar el dominio
ni los casos de uso. Eso es lo que la arquitectura hexagonal compra.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.infraestructura.adaptadores.entrada.api.rutas import canasta, catalogo, precios, reportes
from src.configuracion import config

logging.basicConfig(level=logging.INFO)

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
    return {"estado": "ok", "entorno": config.app_entorno}

