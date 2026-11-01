"""
El puesto de un casero dentro de un mercado.

Un mercado grande no es un vendedor: son decenas de puestos, cada uno con
su número, su rubro y su dueño. El precio del MERCADO sigue siendo un rango
(se regatea y cada puesto cobra distinto); el puesto es a quién se le
compra, y es lo que una oferta o una medición de campo nombra: "puesto 14
del Rodríguez".

No es un punto de venta del catálogo: no se dibuja en el mapa ni compite
en el comparador. Pertenece a un mercado y se identifica por (mercado,
número), que es como lo dice la gente.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.dominio.excepciones import DatoInvalido
from src.dominio.modelo.auditoria import Auditoria
from src.dominio.modelo.producto import Categoria

# El "puesto" de una distribuidora es su local entero: no tiene número de
# pasillo, pero sí foto, rubros e inventario como cualquier casero.
NUMERO_LOCAL = "LOCAL"
LARGO_MAXIMO_NUMERO = 16
LARGO_MAXIMO_NOMBRE = 80
LARGO_MAXIMO_REFERENCIA = 160
_NUMERO_VALIDO = re.compile(r"^[A-Z0-9][A-Z0-9 \-/]*$")


def normalizar_numero(numero: str) -> str:
    """ "  b-3 " → "B-3". El mismo puesto escrito de dos formas es uno solo."""
    limpio = " ".join((numero or "").split()).upper()
    if not limpio:
        raise DatoInvalido("El número del puesto no puede ir vacío")
    if len(limpio) > LARGO_MAXIMO_NUMERO or not _NUMERO_VALIDO.match(limpio):
        raise DatoInvalido(
            f"Número de puesto {numero!r} no válido: use letras, números y guiones (máx. {LARGO_MAXIMO_NUMERO})"
        )
    return limpio


def orden_de_numero(numero: str) -> tuple:
    """El 2 antes que el 10: los números de puesto se ordenan como números."""
    return (0, int(numero), "") if numero.isdigit() else (1, 0, numero)


@dataclass(frozen=True, slots=True)
class Puesto:
    codigo_mercado: str
    numero: str
    nombre: str
    # Qué vende: categorías del catálogo (hortaliza, carne...). Sirve para
    # buscar "¿quién vende carne en el Rodríguez?" sin tener que listar
    # producto por producto.
    rubros: tuple[Categoria, ...] = ()
    # Cómo encontrarlo adentro: "pasillo de verduras, frente a la puerta 2".
    referencia: str = ""
    # El vendedor dueño del puesto. Un vendedor tiene a lo sumo uno.
    id_vendedor: int | None = None
    # Nombre del archivo de la foto del puesto (lo da el almacén de fotos).
    foto: str | None = None
    id: int | None = None
    auditoria: Auditoria | None = field(default=None, compare=False)

    def __post_init__(self):
        object.__setattr__(self, "numero", normalizar_numero(self.numero))
        nombre = " ".join((self.nombre or "").split())
        if len(nombre) > LARGO_MAXIMO_NOMBRE:
            raise DatoInvalido(f"El nombre del puesto pasa de {LARGO_MAXIMO_NOMBRE} caracteres")
        object.__setattr__(self, "nombre", nombre)
        referencia = " ".join((self.referencia or "").split())
        if len(referencia) > LARGO_MAXIMO_REFERENCIA:
            raise DatoInvalido(f"La referencia pasa de {LARGO_MAXIMO_REFERENCIA} caracteres")
        object.__setattr__(self, "referencia", referencia)
        # Sin repetidos y en un orden estable: el orden del catálogo.
        unicos = tuple(c for c in Categoria if c in set(self.rubros))
        object.__setattr__(self, "rubros", unicos)

    @property
    def es_local(self) -> bool:
        """El local entero de una distribuidora, no un puesto de mercado."""
        return self.numero == NUMERO_LOCAL

    @property
    def titulo(self) -> str:
        """ "Puesto 14 · Verduras Doña Juana", como se muestra."""
        if self.es_local:
            return self.nombre or "Local"
        return f"Puesto {self.numero}" + (f" · {self.nombre}" if self.nombre else "")
