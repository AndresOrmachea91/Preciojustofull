from __future__ import annotations
from datetime import datetime, timezone

from src.aplicacion.casos_uso.gestionar_usuarios import exigir
from src.aplicacion.puertos.salida import (
    RepositorioMercados,
    RepositorioObservaciones,
    RepositorioProductos,
    RepositorioReportes,
    RepositorioUsuarios,
)
from src.dominio.excepciones import (
    MercadoNoEncontrado, ProductoNoEncontrado, ReporteNoEncontrado,
)
from src.dominio.modelo import (
    EstadoReporte, Fuente, NivelPrecio, Observacion, Permiso, Reporte, Rol, Usuario,
)
from src.dominio.valor import Dinero, Periodo, Unidad

# Cuánto pesa en el motor de fusión el reporte de cada rol, una vez
# aprobado. El recolector sigue un instrumento de campo; un ciudadano no.
REPUTACION_POR_ROL = {
    Rol.USUARIO: 0.5,
    Rol.RECOLECTOR: 0.8,
    Rol.ADMINISTRADOR: 0.8,
}


class RegistrarReporteCiudadano:
    """
    Un reporte NO se publica directo ni entra directo al motor de fusión:
    queda pendiente hasta que un administrador lo revisa. Recién aprobado
    se convierte en una observación más, con la reputación de quien lo hizo.
    """

    def __init__(
        self,
        productos: RepositorioProductos,
        mercados: RepositorioMercados,
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


class ValidarReportes:
    def __init__(
        self,
        reportes: RepositorioReportes,
        observaciones: RepositorioObservaciones,
        usuarios: RepositorioUsuarios,
    ):
        self._reportes = reportes
        self._observaciones = observaciones
        self._usuarios = usuarios

    def listar(self, actor: Usuario, estado: EstadoReporte | None = EstadoReporte.PENDIENTE) -> list[Reporte]:
        exigir(actor, Permiso.VALIDAR_REPORTES)
        return sorted(self._reportes.listar(estado), key=lambda r: r.creado_en)

    def aprobar(self, actor: Usuario, id_reporte: int) -> Reporte:
        exigir(actor, Permiso.VALIDAR_REPORTES)
        ahora = datetime.now(timezone.utc)
        reporte = self._obtener(id_reporte).aprobar(actor.id, ahora)
        autor = self._usuarios.obtener(reporte.id_autor)
        reputacion = REPUTACION_POR_ROL[autor.rol] if autor else REPUTACION_POR_ROL[Rol.USUARIO]
        # El hecho se fecha cuando se REPORTÓ, no cuando se aprobó: el
        # precio que alguien vio el lunes no es un precio del miércoles.
        creado = reporte.creado_en
        self._observaciones.guardar_varias([Observacion(
            fuente=Fuente.CIUDADANO,
            nivel=NivelPrecio.MINORISTA,
            codigo_producto=reporte.codigo_producto,
            codigo_mercado=reporte.codigo_mercado,
            periodo=Periodo(creado.year, creado.month, creado.day),
            precio=Dinero(reporte.monto, Unidad(reporte.unidad)),
            capturada_en=creado,
            fecha_observacion=creado.date(),
            reputacion_informante=reputacion,
            evidencia=f"reporte:{reporte.id}",
        )])
        return self._reportes.guardar(reporte)

    def rechazar(self, actor: Usuario, id_reporte: int, motivo: str) -> Reporte:
        exigir(actor, Permiso.VALIDAR_REPORTES)
        reporte = self._obtener(id_reporte).rechazar(actor.id, datetime.now(timezone.utc), motivo)
        return self._reportes.guardar(reporte)

    def _obtener(self, id_reporte: int) -> Reporte:
        reporte = self._reportes.obtener(id_reporte)
        if reporte is None:
            raise ReporteNoEncontrado(id_reporte)
        return reporte
