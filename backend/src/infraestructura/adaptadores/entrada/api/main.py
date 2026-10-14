"""
Adaptador de entrada HTTP.

FastAPI es un detalle del borde: se puede reemplazar sin tocar el dominio
ni los casos de uso. Eso es lo que la arquitectura hexagonal compra.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.infraestructura.adaptadores.entrada.api.dependencias import asegurar_admin_inicial
from src.infraestructura.adaptadores.entrada.api.rutas import cuentas
from src.infraestructura.adaptadores.entrada.api.rutas.administracion import (
    auditoria as admin_auditoria, catalogo as admin_catalogo, reportes as admin_reportes,
    usuarios as admin_usuarios,
)
from src.infraestructura.adaptadores.entrada.api.rutas.publico import canasta, catalogo, precios
from src.infraestructura.adaptadores.entrada.api.rutas.usuario import listas, reportes
from src.infraestructura.adaptadores.entrada.api.rutas.vendedor import precios as vendedor_precios
from src.infraestructura.adaptadores.entrada.api.seguridad import ActorPorPeticion, manejar_error_dominio
from src.configuracion import config
from src.dominio.excepciones import ErrorDominio

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# La interfaz ya construida (frontend/dist). Si está, este mismo proceso la
# sirve: un solo servidor, un solo puerto, sin CORS y sin levantar Vite
# aparte. Si no está, la API funciona igual y la interfaz se sirve con
# `npm run dev` en 5173, como en desarrollo.
INTERFAZ = Path(__file__).resolve().parents[6] / "frontend" / "dist"


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    # Un fallo acá no debe tumbar la API pública de precios: se registra y
    # el administrador se puede crear después desde la consola.
    try:
        asegurar_admin_inicial()
    except Exception:
        log.exception("No se pudo crear el administrador inicial")
    yield


app = FastAPI(
    title="PrecioJusto Bolivia — API",
    description=(
        "Inteligencia de precios de la canasta familiar en La Paz. "
        "Arquitectura hexagonal: esta API es un adaptador de entrada."
    ),
    version="0.2.0",
    lifespan=ciclo_de_vida,
)

# Los errores del dominio que una ruta no atrapa se traducen acá a su
# código HTTP (401, 403, 404, 409 o 400), en un solo lugar.
app.add_exception_handler(ErrorDominio, manejar_error_dominio)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.origenes,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(ActorPorPeticion)

# Rutas agrupadas por quién las usa (ver rutas/<rol>/).
# Públicas: no piden sesión.
app.include_router(catalogo.router, prefix="/api/v1")
app.include_router(precios.router, prefix="/api/v1")
app.include_router(canasta.router, prefix="/api/v1")
# Cuentas: registro, ingreso, mi cuenta.
app.include_router(cuentas.router, prefix="/api/v1")
# Usuario.
app.include_router(reportes.router, prefix="/api/v1")
app.include_router(listas.router, prefix="/api/v1")
# Vendedor: todo bajo /api/v1/vendedor.
app.include_router(vendedor_precios.router, prefix="/api/v1")
# Administrador: todo bajo /api/v1/admin.
app.include_router(admin_usuarios.router, prefix="/api/v1")
app.include_router(admin_reportes.router, prefix="/api/v1")
app.include_router(admin_catalogo.router, prefix="/api/v1")
app.include_router(admin_auditoria.router, prefix="/api/v1")


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

