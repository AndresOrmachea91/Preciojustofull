"""
Objetos de valor: inmutables, sin identidad, se comparan por contenido.

Acá vive la conversión de unidades, que es una regla de negocio y no un
detalle técnico: si el quintal se convierte mal, todos los precios del
sistema quedan mal.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from enum import Enum

from src.dominio.excepciones import UnidadDesconocida


class UnidadCanonica(str, Enum):
    KILOGRAMO = "kg"
    LITRO = "l"
    UNIDAD = "u"
    # Un atado (de cebolla verde, de perejil) no se pesa: se vende como
    # bulto de tamaño convenido. No convierte a kilo y no se pretende.
    ATADO = "atado"


class NivelPrecio(str, Enum):
    """
    A qué altura de la cadena se midió el precio. Lo comparten las fuentes
    y los puntos de venta: un mayorista y la fuente que cotiza mayorista
    hablan del mismo nivel, y ninguno de los dos habla del precio que paga
    una familia en el puesto.
    """

    MAYORISTA = "mayorista"
    MINORISTA = "minorista"


class TipoPrecio(str, Enum):
    """
    Qué clase de precio es el que se observó. Un cartel no es lo mismo que
    lo que se pagó después de regatear.
    """

    ANUNCIADO = "anunciado"     # el cartel o la lista
    COTIZADO = "cotizado"       # lo que dijeron al preguntar
    PAGADO = "pagado"           # lo que efectivamente se pagó
    DESCONOCIDO = "desconocido" # la fuente no lo dice; marcador explícito, no un valor plausible


# Marcador explícito para "no se sabe qué variedad". No es None: una
# observación sin variedad conocida sigue siendo una observación completa,
# y el motor la trata como su propio grupo en vez de mezclarla con todas.
VARIEDAD_DESCONOCIDA = "desconocida"


class Ambito(str, Enum):
    """
    De qué lugar habla una observación.

    PUNTO_VENTA: alguien midió en un local concreto (el Rodríguez, el
    Ketal de San Pedro). Es una medición.

    CIUDAD: la fuente publica un solo valor para toda la ciudad (el IPC da
    "La Paz" mensual). No es una medición en ningún puesto: es la
    referencia sobre la que se ESTIMA un local aplicando su factor_mercado.
    """

    PUNTO_VENTA = "punto_venta"
    CIUDAD = "ciudad"


# Cuántas unidades canónicas hay en una unidad comercial.
# El quintal boliviano son 100 libras castellanas, no el quintal métrico.
_EQUIVALENCIAS: dict[str, tuple[UnidadCanonica, float]] = {
    "KILO": (UnidadCanonica.KILOGRAMO, 1.0),
    "KILOS": (UnidadCanonica.KILOGRAMO, 1.0),
    "KILOGRAMO": (UnidadCanonica.KILOGRAMO, 1.0),
    "KILOGRAMOS": (UnidadCanonica.KILOGRAMO, 1.0),
    "KG": (UnidadCanonica.KILOGRAMO, 1.0),
    "KGR": (UnidadCanonica.KILOGRAMO, 1.0),
    "GRAMO": (UnidadCanonica.KILOGRAMO, 0.001),
    "GRAMOS": (UnidadCanonica.KILOGRAMO, 0.001),
    "GR": (UnidadCanonica.KILOGRAMO, 0.001),
    "GRS": (UnidadCanonica.KILOGRAMO, 0.001),
    "LIBRA": (UnidadCanonica.KILOGRAMO, 0.46),
    "LIBRAS": (UnidadCanonica.KILOGRAMO, 0.46),
    "LB": (UnidadCanonica.KILOGRAMO, 0.46),
    "ARROBA": (UnidadCanonica.KILOGRAMO, 11.5),
    "@": (UnidadCanonica.KILOGRAMO, 11.5),       # así abrevia el SIIP la arroba
    # Un cuarto de arroba. Potosí y Cochabamba cotizan el arroz así.
    "CUARTILLA": (UnidadCanonica.KILOGRAMO, 2.875),
    "QUINTAL": (UnidadCanonica.KILOGRAMO, 46.0),
    "QQ": (UnidadCanonica.KILOGRAMO, 46.0),
    "TONELADA": (UnidadCanonica.KILOGRAMO, 1000.0),
    "LITRO": (UnidadCanonica.LITRO, 1.0),
    "LITROS": (UnidadCanonica.LITRO, 1.0),
    "LT": (UnidadCanonica.LITRO, 1.0),
    "L": (UnidadCanonica.LITRO, 1.0),
    "MILILITRO": (UnidadCanonica.LITRO, 0.001),
    "MILILITROS": (UnidadCanonica.LITRO, 0.001),
    "ML": (UnidadCanonica.LITRO, 0.001),
    "CC": (UnidadCanonica.LITRO, 0.001),
    "UNIDAD": (UnidadCanonica.UNIDAD, 1.0),
    "UNIDADES": (UnidadCanonica.UNIDAD, 1.0),
    "UNID": (UnidadCanonica.UNIDAD, 1.0),
    "U": (UnidadCanonica.UNIDAD, 1.0),
    "DOCENA": (UnidadCanonica.UNIDAD, 12.0),
    "CIENTO": (UnidadCanonica.UNIDAD, 100.0),
    "MAPLE": (UnidadCanonica.UNIDAD, 30.0),
    "ATADO": (UnidadCanonica.ATADO, 1.0),
    "ATADOS": (UnidadCanonica.ATADO, 1.0),
}

# Cómo escribe el SIIP una unidad: un envase opcional, una cantidad
# opcional y la unidad. "qq.", "SACO qq.", "46 Kg.", "LATA 2500 grs.",
# "BIDON 946 ml.", "CAJA 17 Kg.", "100 unid.", "BOLSA @".
# El envase solo no dice nada ("CAJA" a secas): eso se rechaza. Nunca se
# adivina un peso para colarlo como Bs/kg.
_ENVASES = r"CAJA|CAJON|BOLSA|SACO|BULTO|JABA|LATA|BIDON|BOTELLA|PAQUETE|SOBRE"
_UNIDAD_COMERCIAL = re.compile(
    rf"^(?:(?:{_ENVASES})\s+(?:DE\s+)?)?"
    r"(?:(\d+(?:[.,]\d+)?)\s*)?"
    r"([A-Z@]+)$"
)


@dataclass(frozen=True, slots=True)
class Unidad:
    """Una unidad comercial tal como la declara la fuente."""

    texto: str

    def normalizada(self) -> str:
        texto = self.texto.strip().upper()
        texto = texto.replace("(S)", "S").replace("(ES)", "ES")
        texto = re.sub(r"[.,]+$", "", texto.strip())   # "Kg." y también "Kg,"
        return re.sub(r"\s+", " ", texto).strip()

    def equivalencia(self) -> tuple[UnidadCanonica, float]:
        clave = self.normalizada()
        if clave in _EQUIVALENCIAS:
            return _EQUIVALENCIAS[clave]
        m = _UNIDAD_COMERCIAL.match(clave)
        if m and m.group(2) in _EQUIVALENCIAS:
            cantidad = float(m.group(1).replace(",", ".")) if m.group(1) else 1.0
            canonica, factor = _EQUIVALENCIAS[m.group(2)]
            return canonica, cantidad * factor
        raise UnidadDesconocida(self.texto)

    def es_conocida(self) -> bool:
        try:
            self.equivalencia()
        except UnidadDesconocida:
            return False
        return True


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

