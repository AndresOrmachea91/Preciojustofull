"""
Puertos de ENTRADA: qué se le puede pedir al sistema.

La API REST y la línea de comandos son adaptadores que invocan estos casos
de uso. Si mañana se agrega un bot de mensajería, es otro adaptador más
sobre los mismos puertos.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol

from src.dominio.modelo import PrecioConsolidado


@dataclass(frozen=True, slots=True)
class ItemCanasta:
    codigo_producto: str
    cantidad: float = 1.0


@dataclass(frozen=True, slots=True)
class PrecioEnMercado:
    codigo_mercado: str
    nombre_mercado: str
    tipo: str
    zona: str
    precio: PrecioConsolidado
    # mayorista o minorista: dos números que no compiten entre sí.
    nivel_precio: str = "minorista"


@dataclass(frozen=True, slots=True)
class CostoCanastaEnMercado:
    codigo_mercado: str
    nombre_mercado: str
    zona: str
    costo_total: float
    productos_cubiertos: int
    productos_pedidos: int
    faltantes: list[str] = field(default_factory=list)

    @property
    def cobertura(self) -> float:
        return self.productos_cubiertos / self.productos_pedidos if self.productos_pedidos else 0.0


class ConsultarPrecio(Protocol):
    def ejecutar(self, codigo_producto: str, codigo_mercado: str) -> PrecioConsolidado: ...


class CompararMercados(Protocol):
    def ejecutar(self, codigo_producto: str, zona: str | None = None) -> list[PrecioEnMercado]: ...


class CalcularCanasta(Protocol):
    def ejecutar(
        self, items: list[ItemCanasta], zona: str | None = None
    ) -> list[CostoCanastaEnMercado]: ...

