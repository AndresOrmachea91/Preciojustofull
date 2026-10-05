"""
Reporte de precio enviado por una persona.

Un reporte NO es todavía una observación: es una afirmación pendiente de
revisión. Solo cuando un administrador lo aprueba pasa a ser una
observación más, y desde ahí el motor de fusión decide cuánto pesa. Un
reporte rechazado no se borra: queda con su motivo, porque la reputación
del informante se calcula sobre su historial.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum

from src.dominio.excepciones import ReporteYaRevisado


class EstadoReporte(str, Enum):
    PENDIENTE = "pendiente"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"


@dataclass(frozen=True, slots=True)
class Reporte:
    codigo_producto: str
    codigo_mercado: str
    monto: float
    unidad: str
    id_autor: int
    creado_en: datetime
    estado: EstadoReporte = EstadoReporte.PENDIENTE
    id_revisor: int | None = None
    revisado_en: datetime | None = None
    motivo_rechazo: str | None = None
    id: int | None = None

    def _revisar(self, estado: EstadoReporte, id_revisor: int, cuando: datetime,
                 motivo: str | None) -> Reporte:
        # Una decisión no se pisa: aprobar dos veces duplicaría la
        # observación, y rechazar algo aprobado dejaría el dato publicado.
        if self.estado is not EstadoReporte.PENDIENTE:
            raise ReporteYaRevisado(self.id, self.estado.value)
        return replace(self, estado=estado, id_revisor=id_revisor, revisado_en=cuando,
                       motivo_rechazo=motivo)

    def aprobar(self, id_revisor: int, cuando: datetime) -> Reporte:
        return self._revisar(EstadoReporte.APROBADO, id_revisor, cuando, None)

    def rechazar(self, id_revisor: int, cuando: datetime, motivo: str) -> Reporte:
        return self._revisar(EstadoReporte.RECHAZADO, id_revisor, cuando, motivo.strip() or None)
