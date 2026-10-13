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
    # Cómo se vende (kilo, libra, arroba, quintal...). Vacío = las habituales
    # de su categoría (presentaciones_habituales); el administrador las cambia.
    presentaciones: tuple[Presentacion, ...] = field(default=())

    def __post_init__(self):
        if not self.nombre.strip():
            raise ValueError("Un producto necesita nombre")
        if self.presentaciones:
            validar_presentaciones(self.unidad_base, self.presentaciones)
        else:
            object.__setattr__(self, "presentaciones", presentaciones_habituales(self.unidad_base, self.categoria))

    @property
    def es_perecedero(self) -> bool:
        return self.dias_conservacion <= 7


# Cómo se compra de verdad cada categoría por peso. Ofrecer "carne por
# arroba" no es un error de cuenta (60 Bs/kg x 11,5 = 690 Bs), pero es una
# opción que nadie usa en un mercado y que muestra cifras que confunden.
_POR_PESO: dict[Categoria, tuple[Presentacion, ...]] = {
    Categoria.CARNE: (Presentacion.LIBRA, Presentacion.KILO),
    Categoria.PESCADO: (Presentacion.LIBRA, Presentacion.KILO),
    Categoria.LACTEO: (Presentacion.LIBRA, Presentacion.KILO),
    Categoria.FRUTA: (Presentacion.LIBRA, Presentacion.KILO, Presentacion.ARROBA),
    Categoria.HORTALIZA: (Presentacion.LIBRA, Presentacion.KILO, Presentacion.ARROBA),
}


def presentaciones_habituales(unidad_base: UnidadCanonica, categoria: Categoria) -> tuple[Presentacion, ...]:
    """
    Las presentaciones que se ofrecen si el administrador no eligió otras.
    Tubérculos y abarrotes llegan al quintal; carne, pescado y lácteos se
    quedan en libra y kilo; el maple (30) es solo del huevo.
    """
    if unidad_base is UnidadCanonica.KILOGRAMO and categoria in _POR_PESO:
        return _POR_PESO[categoria]
    if unidad_base is UnidadCanonica.UNIDAD and categoria is not Categoria.CARNE:
        return (Presentacion.UNIDAD, Presentacion.DOCENA)
    return compatibles(unidad_base)
