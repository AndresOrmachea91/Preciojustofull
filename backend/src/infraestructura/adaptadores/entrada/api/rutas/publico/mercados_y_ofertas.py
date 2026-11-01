"""
Entrar a un mercado y ver las ofertas de los caseros (C133, C134). Públicas:
no piden sesión.

    GET /api/v1/mercados/directorio        cada lugar con sus puestos y ofertas
    GET /api/v1/mercados/{codigo}/ficha    precios, puestos y ofertas de un lugar
    GET /api/v1/ofertas                    ofertas vigentes, de mayor a menor ahorro real
    GET /api/v1/verificaciones             qué conviene medir primero y cuánto varía cada producto
    GET /api/v1/mercados/{codigo}/puestos  sus puestos con foto e inventario (la ventana del mapa)
    GET /api/v1/fotos/{nombre}             la foto de un puesto
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.cache_fichas import recordar
from src.infraestructura.adaptadores.entrada.api.dependencias import (
    almacen_fotos, caso_directorio_mercados, caso_ficha_mercado, caso_ofertas_vigentes,
    caso_priorizar_verificaciones, caso_puestos_del_mercado,
)
from src.infraestructura.adaptadores.entrada.api.mapeo import (
    entrada_directorio_a_salida, ficha_a_salida, oferta_a_salida, plan_verificacion_a_salida,
    puestos_del_mercado_a_salida,
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


@router.get("/verificaciones", response_model=e.PlanVerificacionSalida)
def verificaciones(caso=Depends(caso_priorizar_verificaciones)):
    """
    Recolección adaptativa (A4230): qué productos y lugares conviene medir
    primero, y cuánto se mueve cada precio de un mes a otro (A5020). Es
    público a propósito: muestra dónde el sistema todavía estima.
    """
    return recordar("verificaciones", lambda: plan_verificacion_a_salida(caso.ejecutar()))


@router.get("/mercados/{codigo}/puestos", response_model=e.PuestosDelMercadoSalida)
def puestos_del_mercado(codigo: str, producto: str | None = Query(default=None, max_length=64),
                        articulos: int | None = Query(default=None, ge=1, le=50),
                        caso=Depends(caso_puestos_del_mercado)):
    """
    Los puestos del mercado con su foto y su inventario. Con producto,
    primero los que lo tienen; con articulos, cuántos mostrar de cada uno.
    """
    return recordar(f"puestos:{codigo}:{producto}:{articulos}",
                    lambda: puestos_del_mercado_a_salida(caso.ejecutar(codigo, producto, articulos)))


@router.get("/fotos/{nombre}", include_in_schema=False)
def foto(nombre: str):
    ruta = almacen_fotos().ruta(nombre)
    if ruta is None:
        raise HTTPException(status_code=404, detail="No existe esa foto")
    # El nombre es aleatorio y una foto nueva tiene otro: se puede guardar mucho tiempo.
    return FileResponse(ruta, headers={"Cache-Control": "public, max-age=2592000, immutable"})
