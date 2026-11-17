import threading
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.cache_fichas import recordar
from src.infraestructura.adaptadores.entrada.api.dependencias import (
    caso_comparar_mercados, caso_consultar_precio, caso_evaluar_estimador, caso_historial_precio,
    caso_precios_referenciales,
)
from src.infraestructura.adaptadores.entrada.api.mapeo import (
    precio_a_salida, precio_en_mercado_a_salida, producto_a_salida,
)
from src.dominio.excepciones import ProductoNoEncontrado, SinObservaciones

router = APIRouter(prefix="/precios", tags=["precios"])

# El backtest recorre todas las observaciones: se recalcula cada 10 minutos
# como mucho, no en cada visita a la página.
_CACHE_EVALUACION: dict[str, object] = {}
_CANDADO_EVALUACION = threading.Lock()
_VIGENCIA_EVALUACION = 600


@router.get("/confiabilidad", response_model=e.EvaluacionSalida)
def confiabilidad(caso=Depends(caso_evaluar_estimador)):
    """Backtest del estimador: cuánto se equivoca el estimado frente a los precios observados."""
    with _CANDADO_EVALUACION:
        guardada = _CACHE_EVALUACION.get("salida")
        if guardada is not None and time.monotonic() - _CACHE_EVALUACION["en"] < _VIGENCIA_EVALUACION:
            return guardada
        ev = caso.ejecutar()
        salida = e.EvaluacionSalida(
            casos=ev.casos, error_medio=ev.error_medio, sesgo=ev.sesgo, cobertura=ev.cobertura,
            error_medio_sin_factor=ev.error_medio_sin_factor, el_factor_ayuda=ev.el_factor_ayuda,
            mercados=ev.mercados, productos=ev.productos,
            por_producto=[e.ResumenProductoSalida(
                codigo_producto=r.codigo_producto, nombre_producto=r.nombre_producto, casos=r.casos,
                error_medio=r.error_medio, cobertura=r.cobertura,
            ) for r in ev.por_producto],
            detalle=[e.CasoEvaluadoSalida(
                codigo_producto=c.codigo_producto, nombre_producto=c.nombre_producto,
                codigo_mercado=c.codigo_mercado, nombre_mercado=c.nombre_mercado, periodo=c.periodo,
                observado=c.observado, estimado=c.estimado, estimado_minimo=c.estimado_minimo,
                estimado_maximo=c.estimado_maximo, sin_factor=c.sin_factor, error=round(c.error, 4),
                dentro_del_rango=c.dentro_del_rango, voces=c.voces,
            ) for c in ev.detalle],
            calculado_en=datetime.now(timezone.utc),
        )
        _CACHE_EVALUACION.update(salida=salida, en=time.monotonic())
        return salida


@router.get("/referencia", response_model=list[e.PrecioReferencialSalida])
def referencia(caso=Depends(caso_precios_referenciales)):
    """Los precios referenciales de La Paz: cada producto, al consumidor y por mayor, sin ajuste de lugar."""
    # Son 45 productos por dos niveles: se guarda dos minutos, como las fichas de mercado.
    return recordar("referencia", lambda: [
        e.PrecioReferencialSalida(
            producto=producto_a_salida(r.producto),
            consumidor=precio_a_salida(r.consumidor) if r.consumidor else None,
            mayorista=precio_a_salida(r.mayorista) if r.mayorista else None,
        )
        for r in caso.ejecutar()
    ])


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

