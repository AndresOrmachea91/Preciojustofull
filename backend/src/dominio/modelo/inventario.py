"""
El inventario de un puesto: qué vende, a cuánto y cuánto le queda.

No todos los mercados ni todos los puestos venden lo mismo: el inventario
es lo que dice qué hay en cada uno. El casero lo maneja desde el celular.
Puede decir solo "hay", "poco" o "se acabó", o llevar la cantidad (C148):
cuántas arrobas o kilos le quedan y desde cuánto quiere que se le avise.
Con la cantidad, el estado se calcula solo y nunca queda desactualizado.

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
    # Cuánto le queda, en la misma presentación del precio (12 arrobas, 30 kilos). None: no lo lleva.
    cantidad: float | None = None
    # Desde cuánto avisar que "queda poco". None: se usa una cuarta parte de lo que suele tener.
    minimo: float | None = None

    def __post_init__(self):
        if not self.monto or self.monto <= 0:
            raise DatoInvalido("El precio tiene que ser mayor a cero")
        if self.monto > MONTO_MAXIMO:
            raise DatoInvalido(f"Bs {self.monto:,.2f} parece un error de tipeo: revise el precio")
        if self.cantidad is not None and (self.cantidad < 0 or self.cantidad > 100_000):
            raise DatoInvalido("La cantidad tiene que estar entre 0 y 100 000")
        if self.minimo is not None and self.minimo < 0:
            raise DatoInvalido("El aviso de «queda poco» no puede ser negativo")

    @staticmethod
    def disponibilidad_para(cantidad: float, minimo: float | None) -> Disponibilidad:
        """Con la cantidad a la vista, el estado sale solo: 0 se acabó, hasta el mínimo queda poco."""
        if cantidad <= 0:
            return Disponibilidad.AGOTADO
        if minimo is not None and cantidad <= minimo:
            return Disponibilidad.POCO
        return Disponibilidad.HAY

    @property
    def valor(self) -> float | None:
        """Lo que vale lo que le queda, al precio que pide."""
        return None if self.cantidad is None else round(self.cantidad * self.monto, 2)

    @property
    def precio_por_unidad_base(self) -> float:
        return self.monto / self.presentacion.factor
