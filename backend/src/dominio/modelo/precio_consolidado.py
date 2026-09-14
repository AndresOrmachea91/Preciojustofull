from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime

from src.dominio.valor import Periodo, NivelConfianza, UnidadCanonica


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
    observaciones_usadas: int
    calculado_en: datetime
    conflictos: list[str] = field(default_factory=list)

    @property
    def hay_conflicto(self) -> bool:
        return bool(self.conflictos)

