"""
Los precios referenciales de La Paz (C144): una lista de todos los productos
con el precio de la ciudad, al consumidor y por mayor.

Es la referencia oficial sin el ajuste de ningún lugar: lo que el sistema
usa para estimar donde nadie midió, y contra lo que se dice "este mercado
está 6 % arriba de la ciudad". No inventa nada: sale de la misma regla que
la ficha del mercado (ReferenciaDelSistema.de_la_ciudad).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from src.aplicacion.casos_uso.precios.referencia_sistema import ReferenciaDelSistema
from src.aplicacion.puertos.salida import LectorMercados, LectorObservaciones, LectorProductos
from src.dominio.modelo import Mercado, PrecioConsolidado, Producto
from src.dominio.servicio.motor_fusion import MotorFusion
from src.dominio.valor import NivelPrecio


@dataclass(frozen=True, slots=True)
class PrecioReferencial:
    producto: Producto
    consumidor: PrecioConsolidado | None
    mayorista: PrecioConsolidado | None


class PreciosReferenciales:
    def __init__(self, productos: LectorProductos, mercados: LectorMercados, observaciones: LectorObservaciones,
                 motor: MotorFusion, reloj: Callable[[], date] | None = None):
        self._productos = productos
        self._mercados = mercados
        self._observaciones = observaciones
        self._motor = motor
        self._reloj = reloj

    def ejecutar(self) -> list[PrecioReferencial]:
        # La referencia de la ciudad depende solo del NIVEL del lugar: basta un
        # lugar de cada nivel para pedirla (de_la_ciudad le quita su ajuste).
        lugares = self._mercados.listar()
        minorista = _uno_del_nivel(lugares, NivelPrecio.MINORISTA)
        mayorista = _uno_del_nivel(lugares, NivelPrecio.MAYORISTA)
        referencia = ReferenciaDelSistema(self._productos, self._observaciones, self._motor, reloj=self._reloj)

        salida = [
            PrecioReferencial(
                producto=p,
                consumidor=referencia.de_la_ciudad(p.codigo, minorista) if minorista else None,
                mayorista=referencia.de_la_ciudad(p.codigo, mayorista) if mayorista else None,
            )
            for p in self._productos.listar()
        ]
        salida.sort(key=lambda r: (r.producto.categoria.value, r.producto.nombre))
        return salida


def _uno_del_nivel(lugares: list[Mercado], nivel: NivelPrecio) -> Mercado | None:
    return next((m for m in lugares if m.nivel_precio is nivel), None)
