from __future__ import annotations

from src.aplicacion.casos_uso.comparar_mercados import CIUDAD_POR_DEFECTO, precio_del_local
from src.aplicacion.puertos.salida import (
    RepositorioMercados, RepositorioObservaciones, RepositorioProductos,
)
from src.dominio.excepciones import ProductoNoEncontrado, SinObservaciones
from src.dominio.modelo import PrecioConsolidado
from src.dominio.servicio.motor_fusion import MotorFusion


class ConsultarPrecioProducto:
    """
    Un caso de uso solo orquesta: pide datos por los puertos, llama al
    dominio y devuelve el resultado. La lógica de negocio vive en el
    dominio, no acá.
    """

    def __init__(
        self,
        productos: RepositorioProductos,
        observaciones: RepositorioObservaciones,
        motor: MotorFusion | None = None,
        mercados: RepositorioMercados | None = None,
        ciudad: str = CIUDAD_POR_DEFECTO,
    ):
        self._productos = productos
        self._observaciones = observaciones
        self._motor = motor or MotorFusion()
        self._mercados = mercados
        self._ciudad = ciudad

    def ejecutar(self, codigo_producto: str, codigo_mercado: str) -> PrecioConsolidado:
        if self._productos.obtener(codigo_producto) is None:
            raise ProductoNoEncontrado(codigo_producto)
        locales = self._observaciones.buscar(codigo_producto, codigo_mercado)
        mercado = self._mercados.obtener(codigo_mercado) if self._mercados else None
        if mercado is None:
            # Sin catálogo no hay factor ni nivel: solo lo medido en el local.
            # Grupos distintos (otra variedad, otro mes) no se fusionan: se
            # publica el más reciente.
            return self._motor.consolidar_grupos(locales)[0]
        referencia = self._observaciones.buscar(codigo_producto, ciudad=self._ciudad)
        precio = precio_del_local(self._motor, mercado, locales, referencia)
        if precio is None:
            raise SinObservaciones(f"Sin mediciones ni referencia para {codigo_producto} en {codigo_mercado}")
        return precio

