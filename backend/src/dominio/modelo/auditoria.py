"""
Los 5 campos de auditoría de un registro, vistos desde el dominio.

Los escribe SOLO la persistencia (`Auditable`): el dominio los lee para
mostrarlos, nunca los cambia. Por eso es un valor inmutable aparte y no
campos sueltos en cada entidad.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Auditoria:
    creado_en: datetime
    creado_por: str
    modificado_en: datetime | None = None
    modificado_por: str | None = None
    eliminado: bool = False
