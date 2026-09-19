from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

from src.dominio.modelo.observacion import NivelPrecio


class TipoPuntoVenta(str, Enum):
    """
    La distinción no es cosmética: define qué se puede publicar.

    En un mercado grande hay decenas de puestos y se regatea, así que se
    publica un rango. En una tienda o minimarket hay un dueño y el precio
    está puesto, así que se puede publicar el precio de ese local.

    Un mayorista también tiene precio puesto, pero es un precio de OTRO
    nivel: vende por bulto a comerciantes, no a familias. Ese precio no se
    puede poner al lado de uno de consumidor final como si compitieran.
    """

    MERCADO = "mercado"
    MINIMARKET = "minimarket"
    TIENDA = "tienda"
    SUPERMERCADO = "supermercado"
    MAYORISTA = "mayorista"

    @property
    def admite_precio_puntual(self) -> bool:
        return self is not TipoPuntoVenta.MERCADO

    @property
    def nivel_precio(self) -> NivelPrecio:
        """A qué nivel de la cadena pertenece lo que se observa en este tipo de local."""
        if self is TipoPuntoVenta.MAYORISTA:
            return NivelPrecio.MAYORISTA
        return NivelPrecio.MINORISTA

    @property
    def puede_ser_padre(self) -> bool:
        """Solo un mercado agrupa puestos; una tienda no contiene locales."""
        return self is TipoPuntoVenta.MERCADO


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
    macrodistrito: str = ""
    # Código del mercado que contiene a este local (un sector del Rodríguez
    # apunta a "rodriguez"). Se guarda el código y no el objeto: una entidad
    # no debe arrastrar el grafo entero para existir. Las reglas que
    # necesitan mirar al padre viven en dominio.servicio.jerarquia.
    codigo_padre: str | None = None

    def __post_init__(self):
        if self.codigo_padre == self.codigo:
            raise ValueError(f"El punto de venta {self.codigo} no puede ser su propio padre")

    @property
    def publica_rango(self) -> bool:
        return not self.tipo.admite_precio_puntual

    @property
    def nivel_precio(self) -> NivelPrecio:
        return self.tipo.nivel_precio

    @property
    def tiene_padre(self) -> bool:
        return self.codigo_padre is not None

    def es_comparable_con(self, otro: "Mercado") -> bool:
        """
        Dos puntos de venta se pueden poner lado a lado solo si venden al
        mismo nivel: el precio por quintal de un mayorista no compite con
        el precio por libra de un puesto de mercado.
        """
        return self.nivel_precio is otro.nivel_precio
