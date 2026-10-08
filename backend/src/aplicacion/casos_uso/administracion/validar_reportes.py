"""El administrador revisa los reportes de precio: los aprueba (entran al motor) o los rechaza con motivo."""
from __future__ import annotations

from datetime import datetime, timezone

from src.aplicacion.casos_uso.cuentas.permisos import exigir
from src.aplicacion.puertos.salida import (
    EscritorObservaciones, RepositorioReportes, RepositorioUsuarios,
)
from src.dominio.excepciones import ReporteNoEncontrado
from src.dominio.modelo import (
    EstadoReporte, Fuente, NivelPrecio, Observacion, Permiso, Reporte, Rol, Usuario,
)
from src.dominio.valor import Dinero, Periodo, Unidad

# Cuánto pesa en el motor de fusión el reporte de cada rol, una vez
# aprobado. El administrador hace las rondas de campo con un instrumento
# validado; un vendedor conoce el mercado; un ciudadano reporta de paso.
REPUTACION_POR_ROL = {
    Rol.USUARIO: 0.5,
    Rol.VENDEDOR: 0.6,
    Rol.ADMINISTRADOR: 0.8,
}


class ValidarReportes:
    def __init__(
        self,
        reportes: RepositorioReportes,
        observaciones: EscritorObservaciones,
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
