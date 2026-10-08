"""El usuario reporta un precio que vio. Queda pendiente hasta que un administrador lo revisa."""
from __future__ import annotations

from datetime import datetime, timezone

from src.aplicacion.casos_uso.cuentas.permisos import exigir
from src.aplicacion.puertos.salida import LectorMercados, LectorProductos, RepositorioReportes
from src.dominio.excepciones import MercadoNoEncontrado, ProductoNoEncontrado
from src.dominio.modelo import Permiso, Reporte, Usuario
from src.dominio.valor import Unidad


class RegistrarReporteCiudadano:
    """
    Un reporte NO se publica directo ni entra directo al motor de fusión:
    queda pendiente hasta que un administrador lo revisa. Recién aprobado
    se convierte en una observación más, con la reputación de quien lo hizo.
    """

    def __init__(
        self,
        productos: LectorProductos,
        mercados: LectorMercados,
        reportes: RepositorioReportes,
    ):
        self._productos = productos
        self._mercados = mercados
        self._reportes = reportes

    def ejecutar(
        self,
        autor: Usuario,
        codigo_producto: str,
        codigo_mercado: str,
        monto: float,
        unidad: str,
    ) -> Reporte:
        exigir(autor, Permiso.REPORTAR_PRECIO)
        if self._productos.obtener(codigo_producto) is None:
            raise ProductoNoEncontrado(codigo_producto)
        if self._mercados.obtener(codigo_mercado) is None:
            raise MercadoNoEncontrado(codigo_mercado)
        # Se valida al recibirlo, no al aprobarlo: el informante es quien
        # puede corregir la unidad, no el revisor días después. Lanza
        # UnidadDesconocida si no es convertible.
        Unidad(unidad).equivalencia()
        return self._reportes.guardar(Reporte(
            codigo_producto=codigo_producto,
            codigo_mercado=codigo_mercado,
            monto=monto,
            unidad=unidad,
            id_autor=autor.id,
            creado_en=datetime.now(timezone.utc),
        ))
