"""
Entrar a un mercado y ver las ofertas de los caseros (C133, C134). Públicas:
no piden sesión.

    GET /api/v1/mercados/directorio        cada lugar con sus puestos y ofertas
    GET /api/v1/mercados/{codigo}/ficha    precios, puestos y ofertas de un lugar
    GET /api/v1/ofertas                    ofertas vigentes, de mayor a menor ahorro real
"""
from fastapi import APIRouter, Depends, Query

from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.cache_fichas import recordar
from src.infraestructura.adaptadores.entrada.api.dependencias import (
    caso_directorio_mercados, caso_ficha_mercado, caso_ofertas_vigentes,
)
from src.infraestructura.adaptadores.entrada.api.mapeo import (
    entrada_directorio_a_salida, ficha_a_salida, oferta_a_salida,
)

router = APIRouter(tags=["mercados y ofertas"])


@router.get("/mercados/directorio", response_model=list[e.EntradaDirectorioSalida])
def directorio(caso=Depends(caso_directorio_mercados)):
    return recordar("directorio", lambda: [entrada_directorio_a_salida(x) for x in caso.ejecutar()])


@router.get("/mercados/{codigo}/ficha", response_model=e.FichaMercadoSalida)
def ficha(codigo: str, caso=Depends(caso_ficha_mercado)):
    """Todo lo que se sabe de un lugar: el precio de cada producto, sus puestos y sus ofertas."""
    return recordar(f"ficha:{codigo}", lambda: ficha_a_salida(caso.ejecutar(codigo)))


@router.get("/ofertas", response_model=list[e.OfertaSalida])
def ofertas(mercado: str | None = Query(default=None), producto: str | None = Query(default=None),
            caso=Depends(caso_ofertas_vigentes)):
    """
    Las ofertas vigentes que de verdad son más baratas que el precio del
    sistema (sin la voz del casero). Primero el mayor ahorro relativo.
    """
    return [oferta_a_salida(v) for v in caso.ejecutar(mercado, producto)]
