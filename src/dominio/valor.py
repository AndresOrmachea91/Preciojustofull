"""
Objetos de valor: inmutables, sin identidad, se comparan por contenido.

Acá vive la conversión de unidades, que es una regla de negocio y no un
detalle técnico: si el quintal se convierte mal, todos los precios del
sistema quedan mal.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

from src.dominio.excepciones import UnidadDesconocida


class UnidadCanonica(str, Enum):
    KILOGRAMO = "kg"
    LITRO = "l"
    UNIDAD = "u"


# Cuántas unidades canónicas hay en una unidad comercial.
# El quintal boliviano son 100 libras castellanas, no el quintal métrico.
_EQUIVALENCIAS: dict[str, tuple[UnidadCanonica, float]] = {
    "KILO": (UnidadCanonica.KILOGRAMO, 1.0),
    "KILOS": (UnidadCanonica.KILOGRAMO, 1.0),
    "KG": (UnidadCanonica.KILOGRAMO, 1.0),
    "LIBRA": (UnidadCanonica.KILOGRAMO, 0.46),
    "LIBRAS": (UnidadCanonica.KILOGRAMO, 0.46),
    "LB": (UnidadCanonica.KILOGRAMO, 0.46),
    "ARROBA": (UnidadCanonica.KILOGRAMO, 11.5),
    "QUINTAL": (UnidadCanonica.KILOGRAMO, 46.0),
    "QQ": (UnidadCanonica.KILOGRAMO, 46.0),
    "TONELADA": (UnidadCanonica.KILOGRAMO, 1000.0),
    "LITRO": (UnidadCanonica.LITRO, 1.0),
    "LITROS": (UnidadCanonica.LITRO, 1.0),
    "LT": (UnidadCanonica.LITRO, 1.0),
    "UNIDAD": (UnidadCanonica.UNIDAD, 1.0),
    "DOCENA": (UnidadCanonica.UNIDAD, 12.0),
    "MAPLE": (UnidadCanonica.UNIDAD, 30.0),
}


@dataclass(frozen=True, slots=True)
class Unidad:
    """Una unidad comercial tal como la declara la fuente."""

    texto: str

    def normalizada(self) -> str:
        return self.texto.strip().upper().rstrip(".").replace("(S)", "S")

    def equivalencia(self) -> tuple[UnidadCanonica, float]:
        clave = self.normalizada()
        if clave not in _EQUIVALENCIAS:
            raise UnidadDesconocida(self.texto)
        return _EQUIVALENCIAS[clave]

    def es_conocida(self) -> bool:
        return self.normalizada() in _EQUIVALENCIAS


@dataclass(frozen=True, slots=True)
class Dinero:
    """Un monto en bolivianos. Se guarda con la unidad a la que corresponde."""

    monto: float
    unidad: Unidad

    def __post_init__(self):
        if self.monto <= 0:
            raise ValueError("El precio debe ser mayor a cero")

    def por_unidad_canonica(self) -> tuple[float, UnidadCanonica]:
        canonica, factor = self.unidad.equivalencia()
        return round(self.monto / factor, 6), canonica

    def escalar(self, factor: float) -> "Dinero":
        return Dinero(self.monto * factor, self.unidad)


@dataclass(frozen=True, slots=True)
class Periodo:
    anio: int
    mes: int | None = None
    dia: int | None = None

    @property
    def es_diario(self) -> bool:
        return self.dia is not None

    def __str__(self) -> str:
        if self.dia:
            return f"{self.anio:04d}-{self.mes:02d}-{self.dia:02d}"
        if self.mes:
            return f"{self.anio:04d}-{self.mes:02d}"
        return str(self.anio)


class NivelConfianza(str, Enum):
    """
    Cuánto se puede creer un precio publicado. Nunca se muestra un precio
    sin este dato: presentar una estimación como si fuera una medición
    verificada es deshonesto con el usuario.
    """

    VERIFICADO = "verificado"   # medido en campo
    ALTO = "alto"               # fuente oficial reciente
    MEDIO = "medio"             # estimado o fuente secundaria
    BAJO = "bajo"               # dato viejo o fuente única sin contraste

    @property
    def peso(self) -> float:
        return {"verificado": 1.0, "alto": 0.8, "medio": 0.5, "bajo": 0.25}[self.value]

