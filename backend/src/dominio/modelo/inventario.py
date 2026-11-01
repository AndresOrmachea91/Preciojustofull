"""
El inventario de un puesto: qué vende, a cuánto y si le queda.

No todos los mercados ni todos los puestos venden lo mismo: el inventario
es lo que dice qué hay en cada uno. El casero lo maneja desde el celular
en un toque ("hay", "poco", "se acabó"), porque si cuesta más que eso no
lo va a mantener al día.

El precio del inventario es el precio que el casero declara: cuando cambia,
se publica además como una observación de fuente VENDEDOR (como siempre
desde C106), y el motor de fusión lo pesa como declarado, no como medido.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.dominio.excepciones import DatoInvalido
from src.dominio.modelo.auditoria import Auditoria
from src.dominio.modelo.presentacion import Presentacion

# Un precio de mercado por encima de esto es casi siempre un error de tipeo
# (un cero de más), no un producto caro: ni un quintal de carne llega.
MONTO_MAXIMO = 20_000.0


class Disponibilidad(str, Enum):
    HAY = "hay"
    POCO = "poco"
    AGOTADO = "agotado"

    @property
    def se_puede_comprar(self) -> bool:
        return self is not Disponibilidad.AGOTADO


@dataclass(frozen=True, slots=True)
class ArticuloInventario:
    id_puesto: int
    codigo_producto: str
    monto: float
    presentacion: Presentacion
    disponibilidad: Disponibilidad = Disponibilidad.HAY
    actualizado_en: datetime | None = None
    id: int | None = None
    auditoria: Auditoria | None = field(default=None, compare=False)

    def __post_init__(self):
        if not self.monto or self.monto <= 0:
            raise DatoInvalido("El precio tiene que ser mayor a cero")
        if self.monto > MONTO_MAXIMO:
            raise DatoInvalido(f"Bs {self.monto:,.2f} parece un error de tipeo: revise el precio")

    @property
    def precio_por_unidad_base(self) -> float:
        return self.monto / self.presentacion.factor
