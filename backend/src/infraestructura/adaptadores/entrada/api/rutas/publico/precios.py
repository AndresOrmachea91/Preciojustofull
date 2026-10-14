from fastapi import APIRouter, Depends, HTTPException, Query

from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.dependencias import (
    caso_comparar_mercados, caso_consultar_precio, caso_historial_precio,
)
from src.infraestructura.adaptadores.entrada.api.mapeo import precio_a_salida, precio_en_mercado_a_salida
from src.dominio.excepciones import ProductoNoEncontrado, SinObservaciones

router = APIRouter(prefix="/precios", tags=["precios"])


@router.get("/{codigo_producto}/comparar", response_model=list[e.PrecioEnMercadoSalida])
def comparar(
    codigo_producto: str,
    zona: str | None = Query(default=None),
    caso=Depends(caso_comparar_mercados),
):
    """Mismo producto en todos los puntos de venta, del más barato al más caro."""
    try:
        return [precio_en_mercado_a_salida(x) for x in caso.ejecutar(codigo_producto, zona)]
    except ProductoNoEncontrado as ex:
        raise HTTPException(status_code=404, detail=str(ex))


@router.get("/{codigo_producto}/historial", response_model=e.HistorialSalida)
def historial(codigo_producto: str, meses: int = Query(default=24, ge=1, le=120),
              caso=Depends(caso_historial_precio)):
    """El precio de referencia de la ciudad (SIIP) mes a mes: consumidor final y mayorista."""
    try:
        unidad, puntos = caso.ejecutar(codigo_producto, meses)
    except ProductoNoEncontrado as ex:
        raise HTTPException(status_code=404, detail=str(ex))
    return e.HistorialSalida(codigo_producto=codigo_producto, unidad=unidad, puntos=[
        e.PuntoHistorialSalida(periodo=f"{p.anio:04d}-{p.mes:02d}", nivel=p.nivel, precio=p.precio,
                               observaciones=p.observaciones)
        for p in puntos
    ])


@router.get("/{codigo_producto}/mercado/{codigo_mercado}", response_model=e.PrecioSalida)
def consultar(codigo_producto: str, codigo_mercado: str, caso=Depends(caso_consultar_precio)):
    try:
        return precio_a_salida(caso.ejecutar(codigo_producto, codigo_mercado))
    except ProductoNoEncontrado as ex:
        raise HTTPException(status_code=404, detail=str(ex))
    except SinObservaciones:
        raise HTTPException(status_code=404, detail="Sin datos para ese producto en ese mercado")

