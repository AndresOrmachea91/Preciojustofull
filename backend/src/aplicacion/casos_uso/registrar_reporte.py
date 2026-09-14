from __future__ import annotations
from datetime import datetime, timezone

from src.aplicacion.puertos.salida import (
    RepositorioMercados,
    RepositorioObservaciones,
    RepositorioProductos,
)
from src.dominio.excepciones import MercadoNoEncontrado, ProductoNoEncontrado
from src.dominio.modelo import Fuente, NivelPrecio, Observacion
from src.dominio.valor import Dinero, Periodo, Unidad


class RegistrarReporteCiudadano:
    """
    Un reporte ciudadano entra como una observación más, con la reputación
    de quien lo hizo. No se publica directo: el motor de fusión decide
    cuánto pesa frente a las demás fuentes.
    """

    def __init__(
        self,
        productos: RepositorioProductos,
        mercados: RepositorioMercados,
        observaciones: RepositorioObservaciones,
    ):
        self._productos = productos
        self._mercados = mercados
        self._observaciones = observaciones

    def ejecutar(
        self,
        codigo_producto: str,
        codigo_mercado: str,
        monto: float,
        unidad: str,
        reputacion: float = 0.5,
    ) -> Observacion:
        if self._productos.obtener(codigo_producto) is None:
            raise ProductoNoEncontrado(codigo_producto)
        if self._mercados.obtener(codigo_mercado) is None:
            raise MercadoNoEncontrado(codigo_mercado)

        ahora = datetime.now(timezone.utc)
        observacion = Observacion(
            fuente=Fuente.CIUDADANO,
            nivel=NivelPrecio.MINORISTA,
            codigo_producto=codigo_producto,
            codigo_mercado=codigo_mercado,
            periodo=Periodo(ahora.year, ahora.month, ahora.day),
            precio=Dinero(monto, Unidad(unidad)),
            capturada_en=ahora,
            reputacion_informante=reputacion,
        )
        self._observaciones.guardar_varias([observacion])
        return observacion

