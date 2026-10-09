"""
Presentaciones de venta: kilo, libra, arroba, quintal...

El sistema guarda y compara todo en la unidad BASE del producto (kilo,
litro, unidad o atado): es lo único que permite poner lado a lado el precio
del SIIP por quintal y el de un puesto por libra. La presentación es cómo
lo compra la gente; convertir de una a otra es multiplicar por el factor.

Solo se puede ofrecer una presentación de la MISMA magnitud que la unidad
base: el arroz (kilo) se vende por quintal, pero no por litro ni por docena.
"""
from __future__ import annotations

from enum import Enum

from src.dominio.excepciones import PresentacionInvalida
from src.dominio.valor import UnidadCanonica


class Presentacion(str, Enum):
    KILO = "kilo"
    LIBRA = "libra"
    ARROBA = "arroba"
    QUINTAL = "quintal"
    LITRO = "litro"
    UNIDAD = "unidad"
    DOCENA = "docena"
    # 30 huevos: así se venden en los mercados de La Paz.
    MAPLE = "maple"
    ATADO = "atado"

    @property
    def unidad_base(self) -> UnidadCanonica:
        return _DEFINICION[self][0]

    @property
    def factor(self) -> float:
        """Cuántas unidades base trae esta presentación (un quintal = 46 kg)."""
        return _DEFINICION[self][1]

    @property
    def nombre(self) -> str:
        return _DEFINICION[self][2]


# Las equivalencias son las mismas que usa el lector de unidades del SIIP
# (dominio/valor.py): una libra boliviana de mercado son 0,46 kg, una
# arroba 11,5 kg y un quintal 46 kg.
_DEFINICION: dict[Presentacion, tuple[UnidadCanonica, float, str]] = {
    Presentacion.KILO: (UnidadCanonica.KILOGRAMO, 1.0, "Kilo"),
    Presentacion.LIBRA: (UnidadCanonica.KILOGRAMO, 0.46, "Libra"),
    Presentacion.ARROBA: (UnidadCanonica.KILOGRAMO, 11.5, "Arroba"),
    Presentacion.QUINTAL: (UnidadCanonica.KILOGRAMO, 46.0, "Quintal"),
    Presentacion.LITRO: (UnidadCanonica.LITRO, 1.0, "Litro"),
    Presentacion.UNIDAD: (UnidadCanonica.UNIDAD, 1.0, "Unidad"),
    Presentacion.DOCENA: (UnidadCanonica.UNIDAD, 12.0, "Docena"),
    Presentacion.MAPLE: (UnidadCanonica.UNIDAD, 30.0, "Maple (30)"),
    Presentacion.ATADO: (UnidadCanonica.ATADO, 1.0, "Atado"),
}


def compatibles(unidad_base: UnidadCanonica) -> tuple[Presentacion, ...]:
    """Todas las presentaciones que tienen sentido para esa unidad base, de menor a mayor."""
    return tuple(sorted((p for p in Presentacion if p.unidad_base is unidad_base), key=lambda p: p.factor))


def validar_presentaciones(unidad_base: UnidadCanonica, presentaciones: tuple[Presentacion, ...]) -> None:
    if not presentaciones:
        raise PresentacionInvalida("Un producto necesita al menos una presentación")
    ajenas = [p.value for p in presentaciones if p.unidad_base is not unidad_base]
    if ajenas:
        raise PresentacionInvalida(
            f"No se puede vender por {', '.join(ajenas)} un producto que se mide en {unidad_base.value}"
        )
    if not any(p.factor == 1.0 for p in presentaciones):
        # La presentación de factor 1 es la unidad en la que se publica el
        # precio; sin ella no habría una cifra de referencia que mostrar.
        raise PresentacionInvalida("Falta la presentación de la unidad base (kilo, litro, unidad o atado)")


def precio_en(precio_por_unidad_base: float, presentacion: Presentacion) -> float:
    """El precio por kilo (o litro, o unidad) llevado a la presentación pedida."""
    return precio_por_unidad_base * presentacion.factor
