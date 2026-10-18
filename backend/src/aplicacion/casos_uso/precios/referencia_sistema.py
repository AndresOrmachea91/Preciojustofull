"""
El precio del sistema en un lugar, con la misma regla que todo lo demás
(precio_del_local): lo medido ahí si lo hay; si no, estimado desde la
referencia de la ciudad.

Lo usan las ofertas (C133) para medir el ahorro, con una diferencia que es
el candado principal: se calcula SIN la voz del propio casero. Si no, un
vendedor podría declarar hoy su papa a Bs 120 la arroba y mañana "ofertarla"
a 100: el ahorro lo habría elegido él.

Guarda las observaciones de cada producto mientras vive, para que una
pantalla con muchas ofertas o muchos productos haga una consulta por
producto y no una por oferta.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import date

from src.aplicacion.casos_uso.precios.comparar_mercados import (
    CIUDAD_POR_DEFECTO, en_unidad_del_producto, precio_del_local,
)
from src.aplicacion.puertos.salida import LectorObservaciones, LectorProductos
from src.dominio.modelo import Mercado, Observacion, PrecioConsolidado, Producto
from src.dominio.servicio.motor_fusion import MotorFusion


class ReferenciaDelSistema:
    def __init__(self, productos: LectorProductos, observaciones: LectorObservaciones, motor: MotorFusion,
                 ciudad: str = CIUDAD_POR_DEFECTO, reloj: Callable[[], date] | None = None):
        self._productos = productos
        self._observaciones = observaciones
        self._motor = motor
        self._ciudad = ciudad
        self._reloj = reloj
        self._por_producto: dict[str, tuple[Producto | None, list[Observacion]]] = {}

    def producto(self, codigo: str) -> Producto | None:
        return self._cargar(codigo)[0]

    def precio(self, codigo_producto: str, mercado: Mercado,
               sin_informante: str | None = None) -> PrecioConsolidado | None:
        """El precio de ese producto en ese lugar; sin_informante deja fuera a esa voz."""
        producto, todas = self._cargar(codigo_producto)
        if producto is None:
            return None
        if sin_informante is not None:
            todas = [o for o in todas if o.informante != sin_informante]
        referencia = [o for o in todas if o.es_referencia_de_ciudad and o.ciudad == self._ciudad]
        locales = [o for o in todas if o.codigo_mercado == mercado.codigo]
        return precio_del_local(self._motor, mercado, locales, referencia,
                                self._reloj() if self._reloj else None)

    def de_la_ciudad(self, codigo_producto: str, mercado: Mercado) -> PrecioConsolidado | None:
        """
        La referencia de la ciudad del nivel de ese lugar, sin el ajuste del
        lugar: contra esto se dice "este mercado está 6 % arriba de la ciudad".
        """
        _, todas = self._cargar(codigo_producto)
        referencia = [o for o in todas if o.es_referencia_de_ciudad and o.ciudad == self._ciudad
                      and o.nivel is mercado.nivel_precio]
        grupos = self._motor.agrupar(referencia)
        if not grupos:
            return None
        # Estimar con factor 1 es exactamente "la ciudad, en este nivel".
        return self._motor.estimar_desde_ciudad(next(iter(grupos.values())), replace(mercado, factor_mercado=1.0))

    def observaciones(self, codigo_producto: str) -> list[Observacion]:
        return self._cargar(codigo_producto)[1]

    def _cargar(self, codigo: str) -> tuple[Producto | None, list[Observacion]]:
        if codigo not in self._por_producto:
            producto = self._productos.obtener(codigo)
            todas = self._observaciones.buscar(codigo) if producto else []
            self._por_producto[codigo] = (producto, en_unidad_del_producto(todas, producto) if producto else [])
        return self._por_producto[codigo]
