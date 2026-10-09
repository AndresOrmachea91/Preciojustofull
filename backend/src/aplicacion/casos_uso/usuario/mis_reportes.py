"""El usuario ve sus reportes y en qué quedó cada uno (pendiente, aprobado o rechazado con motivo)."""
from __future__ import annotations

from src.aplicacion.casos_uso.cuentas.permisos import exigir
from src.aplicacion.puertos.salida import LectorReportesDeAutor
from src.dominio.modelo import Permiso, Reporte, Usuario


class MisReportes:
    def __init__(self, reportes: LectorReportesDeAutor):
        self._reportes = reportes

    def ejecutar(self, actor: Usuario) -> list[Reporte]:
        exigir(actor, Permiso.REPORTAR_PRECIO)
        # Solo los propios: el id sale de la sesión, nunca de la petición.
        return self._reportes.listar_de_autor(actor.id)
