from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime

from src.dominio.valor import NivelConfianza, Periodo, Procedencia, UnidadCanonica


@dataclass(frozen=True, slots=True)
class RangoPrecio:
    minimo: float
    maximo: float

    def __post_init__(self):
        if self.minimo > self.maximo:
            raise ValueError("El mínimo no puede ser mayor que el máximo")

    @property
    def centro(self) -> float:
        return round((self.minimo + self.maximo) / 2, 2)

    @property
    def amplitud(self) -> float:
        return round(self.maximo - self.minimo, 2)


@dataclass(frozen=True, slots=True)
class PrecioConsolidado:
    """
    El precio que el sistema publica. Es DERIVADO: se recalcula desde las
    observaciones cada vez que cambia el motor de fusión.
    """

    codigo_producto: str
    codigo_mercado: str
    periodo: Periodo
    rango: RangoPrecio
    unidad: UnidadCanonica
    confianza: NivelConfianza
    # Cuántas observaciones lo respaldan y de dónde sale. Obligatorios: sin
    # ellos no hay precio.
    observaciones_usadas: int
    procedencia: Procedencia
    # Fecha de OBSERVACIÓN de la más reciente de las usadas. None si ninguna
    # la trae: no se sustituye por la de captura.
    fecha_observacion_mas_reciente: date | None
    calculado_en: datetime
    conflictos: list[str] = field(default_factory=list)
    # PROCEDENCIA en detalle: cuántas voces INDEPENDIENTES de cada fuente
    # sostienen el precio ({"vendedor": 1, "ciudadano": 2}). Es lo que la
    # pantalla traduce a "visto el 12/10 por un vendedor y 2 compradores".
    voces: dict[str, int] = field(default_factory=dict)
    # Solo en un ESTIMADO: el factor del local que multiplicó la referencia
    # de la ciudad. Sin él no se puede explicar de dónde salió la cifra.
    factor_mercado: float | None = None
    # Días entre la observación más reciente y hoy, si se calculó el rango
    # honesto. None = no se ajustó por antigüedad.
    antiguedad_dias: int | None = None
    # Por qué el rango es más ancho de lo que da la dispersión sola.
    motivos_rango: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.observaciones_usadas < 1:
            raise ValueError("Un precio consolidado necesita al menos una observación")

    @property
    def hay_conflicto(self) -> bool:
        return bool(self.conflictos)

    @property
    def es_estimado(self) -> bool:
        return self.procedencia is Procedencia.ESTIMADO

