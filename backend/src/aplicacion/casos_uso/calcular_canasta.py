from __future__ import annotations

from src.aplicacion.puertos.entrada import CostoCanastaEnMercado, ItemCanasta
from src.aplicacion.puertos.salida import (
    RepositorioMercados,
    RepositorioObservaciones,
)
from src.dominio.excepciones import SinObservaciones
from src.dominio.servicio.motor_fusion import MotorFusion


class CalcularCanastaCasoUso:
    """
    La funcionalidad estrella: cuánto sale la lista completa de compras en
    cada punto de venta.

    Es más robusta que el precio individual: aunque la estimación tenga
    error, ese error afecta a todos los mercados en la misma dirección, así
    que el ORDEN entre ellos se mantiene. El sistema entrega valor aun con
    un modelo imperfecto.
    """

    def __init__(
        self,
        mercados: RepositorioMercados,
        observaciones: RepositorioObservaciones,
        motor: MotorFusion | None = None,
    ):
        self._mercados = mercados
        self._observaciones = observaciones
        self._motor = motor or MotorFusion()

    def ejecutar(
        self, items: list[ItemCanasta], zona: str | None = None
    ) -> list[CostoCanastaEnMercado]:
        resultado: list[CostoCanastaEnMercado] = []

        for mercado in self._mercados.listar(zona):
            total = 0.0
            cubiertos = 0
            faltantes: list[str] = []

            for item in items:
                obs = self._observaciones.buscar(item.codigo_producto, mercado.codigo)
                obs = [o for o in obs if o.nivel is mercado.nivel_precio]
                if not obs:
                    faltantes.append(item.codigo_producto)
                    continue
                try:
                    consolidado = self._motor.consolidar(obs)
                except SinObservaciones:
                    faltantes.append(item.codigo_producto)
                    continue
                total += consolidado.rango.centro * item.cantidad
                cubiertos += 1

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
                )
            )

        # Primero los que cubren más productos; a igual cobertura, el más barato.
        resultado.sort(key=lambda c: (-c.cobertura, c.costo_total))
        return resultado

