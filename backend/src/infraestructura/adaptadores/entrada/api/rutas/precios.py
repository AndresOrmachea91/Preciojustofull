from fastapi import APIRouter, Depends, HTTPException, Query

from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.dependencias import (
    caso_comparar_mercados, caso_consultar_precio,
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


@router.get("/{codigo_producto}/mercado/{codigo_mercado}", response_model=e.PrecioSalida)
def consultar(codigo_producto: str, codigo_mercado: str, caso=Depends(caso_consultar_precio)):
    try:
        return precio_a_salida(caso.ejecutar(codigo_producto, codigo_mercado))
    except ProductoNoEncontrado as ex:
        raise HTTPException(status_code=404, detail=str(ex))
    except SinObservaciones:
        raise HTTPException(status_code=404, detail="Sin datos para ese producto en ese mercado")

