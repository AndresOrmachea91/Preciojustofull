"""
Cómo cambió el precio de un producto en la ciudad, mes a mes.

Sale de la referencia de ciudad (el SIIP): el IPC da el precio al
consumidor final y el diario el mayorista. Un mes con varios datos (el
diario publica casi todos los días) se resume en su MEDIANA, que un día
raro no mueve. Los dos niveles se devuelven por separado: el mayorista no
compite con el minorista, pero mirarlos juntos muestra el margen.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from src.aplicacion.casos_uso.precios.comparar_mercados import CIUDAD_POR_DEFECTO, en_unidad_del_producto
from src.aplicacion.puertos.salida import LectorObservaciones, LectorProductos
from src.dominio.excepciones import ProductoNoEncontrado
from src.dominio.valor import NivelPrecio

MESES_POR_DEFECTO = 24


@dataclass(frozen=True, slots=True)
class PuntoHistorial:
    anio: int
    mes: int
    nivel: str
    precio: float
    observaciones: int


class HistorialPrecio:
    def __init__(self, productos: LectorProductos, observaciones: LectorObservaciones,
                 ciudad: str = CIUDAD_POR_DEFECTO):
        self._productos = productos
        self._observaciones = observaciones
        self._ciudad = ciudad

    def ejecutar(self, codigo_producto: str, meses: int = MESES_POR_DEFECTO) -> tuple[str, list[PuntoHistorial]]:
        """La unidad del precio y los puntos, del mes más viejo al más nuevo."""
        producto = self._productos.obtener(codigo_producto)
        if producto is None:
            raise ProductoNoEncontrado(codigo_producto)
        referencia = [
            o for o in en_unidad_del_producto(self._observaciones.buscar(codigo_producto, ciudad=self._ciudad), producto)
            if o.es_referencia_de_ciudad and o.periodo.mes is not None
        ]
        por_mes: dict[tuple[NivelPrecio, int, int], list[float]] = {}
        for o in referencia:
            por_mes.setdefault((o.nivel, o.periodo.anio, o.periodo.mes), []).append(o.precio_canonico())

        meses_con_dato = sorted({(a, m) for _, a, m in por_mes}, reverse=True)[:max(1, min(meses, 120))]
        recientes = set(meses_con_dato)
        puntos = [
            PuntoHistorial(anio, mes, nivel.value, round(median(valores), 2), len(valores))
            for (nivel, anio, mes), valores in por_mes.items()
            if (anio, mes) in recientes
        ]
        puntos.sort(key=lambda p: (p.anio, p.mes, p.nivel))
        return producto.unidad_base.value, puntos
