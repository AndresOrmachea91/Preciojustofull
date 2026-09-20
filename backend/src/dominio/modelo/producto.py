from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

from src.dominio.valor import UnidadCanonica


class Categoria(str, Enum):
    HORTALIZA = "hortaliza"
    TUBERCULO = "tuberculo"
    FRUTA = "fruta"
    CARNE = "carne"
    PESCADO = "pescado"
    LACTEO = "lacteo"
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
    # En qué unidad se publica el precio de este producto. Un huevo o un
    # choclo se venden por unidad; un atado de cebolla verde no se pesa.
    unidad_base: UnidadCanonica = UnidadCanonica.KILOGRAMO

    @property
    def es_perecedero(self) -> bool:
        return self.dias_conservacion <= 7

