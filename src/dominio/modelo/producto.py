from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class Categoria(str, Enum):
    HORTALIZA = "hortaliza"
    TUBERCULO = "tuberculo"
    FRUTA = "fruta"
    CARNE = "carne"
    ABARROTE = "abarrote"
    OTRO = "otro"


@dataclass(frozen=True, slots=True)
class Producto:
    codigo: str
    nombre: str
    categoria: Categoria = Categoria.OTRO
    # Días que aguanta almacenado. Determina cuán rápido le pega un bloqueo:
    # una hortaliza reacciona en días, un abarrote tarda semanas.
    dias_conservacion: int = 30
    zona_origen: str | None = None

    @property
    def es_perecedero(self) -> bool:
        return self.dias_conservacion <= 7

