"""
Lo que se sabe del estado del sistema (C132). Son hechos leídos, no
juicios: el caso de uso decide qué está bien y qué hay que revisar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DatosDeFuente:
    fuente: str
    observaciones: int
    ultima_captura: datetime | None


@dataclass(frozen=True, slots=True)
class UltimaRecoleccion:
    fuente: str
    ocurrido_en: datetime
    exito: bool
    detalle: str | None
    hechos_nuevos_24h: int


@dataclass(frozen=True, slots=True)
class EstadoRespaldo:
    fecha: datetime | None
    archivo: str | None
    tamano_bytes: int | None
    verificado: bool
    filas_observaciones: int | None
    detalle: str | None


@dataclass(frozen=True, slots=True)
class DatosSalud:
    fuentes: list[DatosDeFuente] = field(default_factory=list)
    recolecciones: list[UltimaRecoleccion] = field(default_factory=list)
    # Pares (punto de venta, producto) con un precio OBSERVADO en la
    # ventana, y cuántos pares hay en el catálogo.
    pares_observados: int = 0
    pares_posibles: int = 0
