"""
Las ofertas de los caseros que se pueden mostrar ahora (C133).

Cada oferta sale con el precio del sistema en ese mercado —calculado sin
la voz del casero— y el ahorro contra ESE precio. Si el sistema ya no la ve
más barata (el mercado bajó, o llegaron mediciones), deja de mostrarse:
una "oferta" más cara que el precio de todos no es oferta.

El orden es la recomendación, y es explicable: primero el mayor ahorro
relativo; a igual ahorro, la más confirmada por compradores. Nadie paga por
aparecer arriba.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from src.aplicacion.casos_uso.precios.referencia_sistema import ReferenciaDelSistema
from src.aplicacion.puertos.salida import (
    LectorMercados, LectorObservaciones, LectorProductos, RepositorioOfertas, RepositorioPuestos,
)
from src.dominio.modelo import Confirmacion, Mercado, Oferta, PrecioConsolidado, Producto, Puesto
from src.dominio.modelo.oferta import ahorro_frente_al_sistema
from src.dominio.servicio.motor_fusion import MotorFusion


@dataclass(frozen=True, slots=True)
class OfertaVista:
    oferta: Oferta
    producto: Producto
    mercado: Mercado
    puesto: Puesto | None
    # El precio del sistema en ese mercado, por unidad base, sin el casero.
    precio_sistema: PrecioConsolidado
    ahorro_por_unidad: float
    confirmaron: int
    desmintieron: int

    @property
    def ahorro_relativo(self) -> float:
        centro = self.precio_sistema.rango.centro
        return round(self.ahorro_por_unidad / centro, 4) if centro else 0.0


def informante_de(id_vendedor: int) -> str:
    """Cómo queda anotado un vendedor en sus observaciones: su voz, para dejarla fuera."""
    return f"usuario:{id_vendedor}"


def vista_de(oferta: Oferta, referencia: ReferenciaDelSistema, mercados: LectorMercados,
             puestos: RepositorioPuestos, confirmaciones: list[Confirmacion]) -> OfertaVista | None:
    """La oferta con su comparación; None si ya no se puede mostrar como oferta."""
    producto = referencia.producto(oferta.codigo_producto)
    mercado = mercados.obtener(oferta.codigo_mercado)
    if producto is None or mercado is None:
        return None
    sistema = referencia.precio(producto.codigo, mercado, sin_informante=informante_de(oferta.id_vendedor))
    if sistema is None:
        return None
    ahorro = ahorro_frente_al_sistema(oferta.precio_por_unidad_base, sistema.rango.centro)
    if ahorro is None:
        return None
    puesto = (puestos.obtener_por_numero(mercado.codigo, oferta.numero_puesto)
              if oferta.numero_puesto else None)
    return OfertaVista(
        oferta=oferta, producto=producto, mercado=mercado, puesto=puesto, precio_sistema=sistema,
        ahorro_por_unidad=ahorro,
        confirmaron=len({c.id_usuario for c in confirmaciones if c.la_vio_asi}),
        desmintieron=len({c.id_usuario for c in confirmaciones if not c.la_vio_asi}),
    )


class VerOfertasVigentes:
    def __init__(self, productos: LectorProductos, mercados: LectorMercados, observaciones: LectorObservaciones,
                 motor: MotorFusion, ofertas: RepositorioOfertas, puestos: RepositorioPuestos,
                 reloj: Callable[[], object] | None = None, ahora: Callable[[], datetime] | None = None):
        self._productos = productos
        self._mercados = mercados
        self._observaciones = observaciones
        self._motor = motor
        self._ofertas = ofertas
        self._puestos = puestos
        self._reloj = reloj
        self._ahora = ahora or (lambda: datetime.now(timezone.utc))

    def ejecutar(self, codigo_mercado: str | None = None, codigo_producto: str | None = None) -> list[OfertaVista]:
        ofertas = self._ofertas.vigentes(self._ahora(), codigo_mercado, codigo_producto)
        confirmaciones = self._ofertas.confirmaciones([o.id for o in ofertas])
        # Una sola referencia para todas: una consulta por producto, no por oferta.
        referencia = ReferenciaDelSistema(self._productos, self._observaciones, self._motor, reloj=self._reloj)
        vistas = [
            v for o in ofertas
            if (v := vista_de(o, referencia, self._mercados, self._puestos, confirmaciones.get(o.id, [])))
        ]
        vistas.sort(key=lambda v: (-v.ahorro_relativo, -(v.confirmaron - v.desmintieron), v.oferta.hasta))
        return vistas
