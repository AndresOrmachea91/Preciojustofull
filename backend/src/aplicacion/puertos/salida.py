"""
Puertos de SALIDA: lo que el sistema necesita del mundo exterior.

Son interfaces (Protocol). El dominio y la aplicación dependen de ellas;
los adaptadores las implementan. Esta es la inversión de dependencias que
sostiene toda la arquitectura.

Nótese que FuentePrecios es UNA sola interfaz: SIIP mayorista, SIIP IPC,
medios y reportes ciudadanos son cuatro adaptadores del mismo puerto. Por
eso perder una fuente no obliga a tocar nada más.
"""
from __future__ import annotations
from typing import Protocol, runtime_checkable

from src.dominio.modelo import Mercado, Observacion, Producto
from src.dominio.valor import Periodo


@runtime_checkable
class RepositorioProductos(Protocol):
    def obtener(self, codigo: str) -> Producto | None: ...
    def listar(self) -> list[Producto]: ...
    def guardar(self, producto: Producto) -> None: ...


@runtime_checkable
class RepositorioMercados(Protocol):
    def obtener(self, codigo: str) -> Mercado | None: ...
    def listar(self, zona: str | None = None) -> list[Mercado]: ...
    def guardar(self, mercado: Mercado) -> None: ...


@runtime_checkable
class RepositorioObservaciones(Protocol):
    def buscar(
        self,
        codigo_producto: str,
        codigo_mercado: str | None = None,
        periodo: Periodo | None = None,
    ) -> list[Observacion]: ...
    def guardar_varias(self, observaciones: list[Observacion]) -> int: ...


@runtime_checkable
class FuentePrecios(Protocol):
    """Un puerto, muchos adaptadores. El núcleo no sabe cuál está usando."""

    @property
    def nombre(self) -> str: ...
    def esta_disponible(self) -> bool: ...
    def recolectar(self, codigo_producto: str) -> list[Observacion]: ...


@runtime_checkable
class ServicioPrediccion(Protocol):
    def predecir(
        self, codigo_producto: str, codigo_mercado: str, dias_adelante: int
    ) -> tuple[float, float]:
        """Devuelve (valor estimado, amplitud del intervalo)."""
        ...

