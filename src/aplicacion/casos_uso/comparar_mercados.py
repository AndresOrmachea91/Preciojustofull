from __future__ import annotations

from src.aplicacion.puertos.entrada import PrecioEnMercado
from src.aplicacion.puertos.salida import (
    RepositorioMercados,
    RepositorioObservaciones,
    RepositorioProductos,
)
from src.dominio.excepciones import ProductoNoEncontrado, SinObservaciones
from src.dominio.servicio.motor_fusion import MotorFusion


class CompararMercadosCasoUso:
    """Mismo producto en varios puntos de venta, ordenado de más barato a más caro."""

    def __init__(
        self,
        productos: RepositorioProductos,
        mercados: RepositorioMercados,
        observaciones: RepositorioObservaciones,
        motor: MotorFusion | None = None,
    ):
        self._productos = productos
        self._mercados = mercados
        self._observaciones = observaciones
        self._motor = motor or MotorFusion()

    def ejecutar(self, codigo_producto: str, zona: str | None = None) -> list[PrecioEnMercado]:
        if self._productos.obtener(codigo_producto) is None:
            raise ProductoNoEncontrado(codigo_producto)

        resultado: list[PrecioEnMercado] = []
        for mercado in self._mercados.listar(zona):
            obs = self._observaciones.buscar(codigo_producto, mercado.codigo)
            if not obs:
                continue   # un mercado sin datos se omite, no se inventa
            try:
                consolidado = self._motor.consolidar(obs)
            except SinObservaciones:
                continue
            resultado.append(
                PrecioEnMercado(
                    codigo_mercado=mercado.codigo,
                    nombre_mercado=mercado.nombre,
                    tipo=mercado.tipo.value,
                    zona=mercado.zona,
                    precio=consolidado,
                )
            )

        resultado.sort(key=lambda p: p.precio.rango.centro)
        return resultado

