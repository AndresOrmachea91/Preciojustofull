from __future__ import annotations

from src.aplicacion.puertos.salida import RepositorioObservaciones, RepositorioProductos
from src.dominio.excepciones import ProductoNoEncontrado
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
    ):
        self._productos = productos
        self._observaciones = observaciones
        self._motor = motor or MotorFusion()

    def ejecutar(self, codigo_producto: str, codigo_mercado: str) -> PrecioConsolidado:
        if self._productos.obtener(codigo_producto) is None:
            raise ProductoNoEncontrado(codigo_producto)
        obs = self._observaciones.buscar(codigo_producto, codigo_mercado)
        # Grupos distintos (otra variedad, otro mes) no se fusionan: se
        # publica el más reciente. Decidir si "reciente" alcanza es otra
        # historia, todavía no escrita.
        return self._motor.consolidar_grupos(obs)[0]

