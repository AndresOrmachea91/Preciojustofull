from __future__ import annotations

from src.aplicacion.casos_uso.precios.comparar_mercados import CIUDAD_POR_DEFECTO, precio_del_local
from src.aplicacion.puertos.entrada import CostoCanastaEnMercado, ItemCanasta
from src.aplicacion.puertos.salida import (
    LectorMercados,
    LectorObservaciones,
)
from src.dominio.modelo import Observacion
from src.dominio.servicio.motor_fusion import MotorFusion


class CalcularCanastaCasoUso:
    """
    La funcionalidad estrella: cuánto sale la lista completa de compras en
    cada punto de venta.

    Es más robusta que el precio individual: aunque la estimación tenga
    error, ese error afecta a todos los mercados en la misma dirección, así
    que el ORDEN entre ellos se mantiene. El sistema entrega valor aun con
    un modelo imperfecto.

    El precio de cada producto en cada lugar sale de la MISMA regla que el
    comparador (precio_del_local): lo medido ahí si lo hay; si no, estimado
    desde la referencia de la ciudad. Y se cuenta cuántos fueron estimados,
    para no presentar como conocido lo que es inferido.
    """

    def __init__(
        self,
        mercados: LectorMercados,
        observaciones: LectorObservaciones,
        motor: MotorFusion,
        ciudad: str = CIUDAD_POR_DEFECTO,
    ):
        self._mercados = mercados
        self._observaciones = observaciones
        self._motor = motor
        self._ciudad = ciudad

    def ejecutar(
        self, items: list[ItemCanasta], zona: str | None = None
    ) -> list[CostoCanastaEnMercado]:
        # UNA consulta por producto, no una por producto y mercado.
        por_producto = {item.codigo_producto: self._separar(item.codigo_producto) for item in items}

        resultado: list[CostoCanastaEnMercado] = []
        for mercado in self._mercados.listar(zona):
            total = 0.0
            cubiertos = 0
            estimados = 0
            faltantes: list[str] = []

            for item in items:
                locales, referencia = por_producto[item.codigo_producto]
                precio = precio_del_local(self._motor, mercado, locales.get(mercado.codigo, []), referencia)
                if precio is None:
                    faltantes.append(item.codigo_producto)
                    continue
                total += precio.rango.centro * item.cantidad
                cubiertos += 1
                estimados += precio.es_estimado

            if cubiertos == 0:
                continue

            resultado.append(
                CostoCanastaEnMercado(
                    codigo_mercado=mercado.codigo,
                    nombre_mercado=mercado.nombre,
                    zona=mercado.zona,
                    costo_total=round(total, 2),
                    productos_cubiertos=cubiertos,
                    productos_pedidos=len(items),
                    faltantes=faltantes,
                    productos_estimados=estimados,
                    nivel_precio=mercado.nivel_precio.value,
                )
            )

        # Primero los que cubren más productos; a igual cobertura, el más barato.
        resultado.sort(key=lambda c: (-c.cobertura, c.costo_total))
        return resultado

    def _separar(self, codigo_producto: str) -> tuple[dict[str, list[Observacion]], list[Observacion]]:
        """Las observaciones de un producto: por punto de venta, y la referencia de la ciudad."""
        todas = self._observaciones.buscar(codigo_producto)
        referencia = [o for o in todas if o.es_referencia_de_ciudad and o.ciudad == self._ciudad]
        locales: dict[str, list[Observacion]] = {}
        for o in todas:
            if o.codigo_mercado is not None:
                locales.setdefault(o.codigo_mercado, []).append(o)
        return locales, referencia
