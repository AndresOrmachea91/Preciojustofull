"""
Lista de compras de un usuario: qué productos, cuánto y en qué presentación.

"2 arrobas de papa, 1 quintal de arroz, 1 maple de huevo". La cantidad se
guarda tal como la piensa la persona (en su presentación); para cotizar se
lleva a la unidad base del producto, que es en la que se comparan precios.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from src.dominio.excepciones import DatoInvalido, PresentacionInvalida
from src.dominio.modelo.presentacion import Presentacion
from src.dominio.modelo.producto import Producto

MAXIMO_ITEMS = 60


@dataclass(frozen=True, slots=True)
class ItemLista:
    codigo_producto: str
    cantidad: float
    presentacion: Presentacion

    def __post_init__(self):
        if self.cantidad <= 0:
            raise DatoInvalido("La cantidad tiene que ser mayor a cero")

    def en_unidad_base(self) -> float:
        """2 arrobas -> 23 kg. Es lo que se le pide a la cotización."""
        return self.cantidad * self.presentacion.factor

    def validar_contra(self, producto: Producto) -> None:
        if self.presentacion not in producto.presentaciones:
            raise PresentacionInvalida(
                f"{producto.nombre} no se vende por {self.presentacion.value}"
            )


@dataclass(frozen=True, slots=True)
class ListaCompras:
    id_usuario: int
    nombre: str
    items: tuple[ItemLista, ...] = field(default=())
    creado_en: datetime | None = None
    id: int | None = None

    def __post_init__(self):
        if not self.nombre.strip():
            raise DatoInvalido("La lista necesita un nombre")
        if len(self.items) > MAXIMO_ITEMS:
            raise DatoInvalido(f"Una lista puede tener hasta {MAXIMO_ITEMS} productos")
        codigos = [i.codigo_producto for i in self.items]
        if len(codigos) != len(set(codigos)):
            # Dos renglones del mismo producto confunden la cotización: se suman antes.
            raise DatoInvalido("Cada producto puede aparecer una sola vez en la lista")

    def es_de(self, id_usuario: int) -> bool:
        return self.id_usuario == id_usuario

    def con(self, nombre: str, items: tuple[ItemLista, ...]) -> ListaCompras:
        return replace(self, nombre=nombre, items=items)
