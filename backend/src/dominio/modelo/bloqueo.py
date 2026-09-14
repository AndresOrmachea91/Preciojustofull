from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True, slots=True)
class Ruta:
    codigo: str
    nombre: str
    zonas_origen: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Bloqueo:
    """
    Un bloqueo de ruta. Entra al modelo predictivo como variable exógena:
    su efecto sobre el precio es rezagado y distinto según el producto.
    """

    ruta: Ruta
    inicio: date
    fin: date | None = None
    intensidad: float = 1.0   # 0 a 1

    def esta_activo(self, en_fecha: date) -> bool:
        if en_fecha < self.inicio:
            return False
        return self.fin is None or en_fecha <= self.fin

    def dias_transcurridos(self, en_fecha: date) -> int:
        if not self.esta_activo(en_fecha):
            return 0
        return (en_fecha - self.inicio).days

