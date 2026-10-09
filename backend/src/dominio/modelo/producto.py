from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

from src.dominio.modelo.presentacion import Presentacion, compatibles, validar_presentaciones
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
    # Cómo se vende (kilo, libra, arroba, quintal...). Vacío = todas las
    # compatibles con la unidad base; las elige el administrador.
    presentaciones: tuple[Presentacion, ...] = field(default=())

    def __post_init__(self):
        if not self.nombre.strip():
            raise ValueError("Un producto necesita nombre")
        if self.presentaciones:
            validar_presentaciones(self.unidad_base, self.presentaciones)
        else:
            object.__setattr__(self, "presentaciones", compatibles(self.unidad_base))

    @property
    def es_perecedero(self) -> bool:
        return self.dias_conservacion <= 7

