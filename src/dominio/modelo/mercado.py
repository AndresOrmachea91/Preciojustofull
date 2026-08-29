from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class TipoPuntoVenta(str, Enum):
    """
    La distinción no es cosmética: define qué se puede publicar.

    En un mercado grande hay decenas de puestos y se regatea, así que se
    publica un rango. En una tienda o minimarket hay un dueño y el precio
    está puesto, así que se puede publicar el precio de ese local.
    """

    MERCADO = "mercado"
    MINIMARKET = "minimarket"
    TIENDA = "tienda"
    SUPERMERCADO = "supermercado"

    @property
    def admite_precio_puntual(self) -> bool:
        return self is not TipoPuntoVenta.MERCADO


@dataclass(frozen=True, slots=True)
class Mercado:
    codigo: str
    nombre: str
    tipo: TipoPuntoVenta
    zona: str
    latitud: float | None = None
    longitud: float | None = None
    # Cuánto se aparta este punto de venta del precio de referencia de la
    # ciudad. Se aprende del levantamiento de campo; 1.0 significa "igual
    # a la referencia".
    factor_mercado: float = 1.0

    @property
    def publica_rango(self) -> bool:
        return not self.tipo.admite_precio_puntual

