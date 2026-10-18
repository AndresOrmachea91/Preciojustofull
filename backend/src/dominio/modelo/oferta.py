"""
La oferta del casero "con candado" (C133).

Una oferta es una DECLARACIÓN del vendedor sobre su puesto: "hoy el tomate
a Bs 5 el kilo". Para que no sea publicidad engañosa lleva candados, todos
acá en el dominio y no en la pantalla:

1. Vence sola: dura 24, 48 o 72 horas. Una oferta eterna es un precio.
2. Máximo tres activas por vendedor: si todo está en oferta, nada lo está.
3. El ahorro se mide contra el precio del SISTEMA en ese mercado (observado
   o estimado, diciendo cuál) calculado SIN la voz del propio casero. Nunca
   contra un "antes" que escribe el casero: ese número lo elige él.
4. Si no es de verdad más barata que ese precio, no se publica como oferta.
5. No entra al motor de fusión: una rebaja la elige el casero (sesgo de
   selección) y no debe hundir la referencia del mercado.
6. Los compradores la confirman o la desmienten. Dos desmentidos de
   personas distintas la pausan y la mandan a revisión.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from enum import Enum

from src.dominio.excepciones import DatoInvalido
from src.dominio.modelo.auditoria import Auditoria
from src.dominio.modelo.presentacion import Presentacion

DURACIONES_HORAS = (24, 48, 72)
MAXIMO_ACTIVAS = 3
DESMENTIDOS_PARA_PAUSAR = 2
LARGO_MAXIMO_NOTA = 80


class EstadoOferta(str, Enum):
    ACTIVA = "activa"
    # Dos compradores distintos dijeron que no estaba así: no se muestra
    # hasta que un administrador la revise.
    EN_REVISION = "en_revision"
    # La retiró el casero o el administrador. No se borra: queda el rastro.
    RETIRADA = "retirada"


@dataclass(frozen=True, slots=True)
class Oferta:
    id_vendedor: int
    codigo_mercado: str
    codigo_producto: str
    monto: float
    presentacion: Presentacion
    desde: datetime
    hasta: datetime
    # Número del puesto dentro del mercado; None en una tienda (el local es el puesto).
    numero_puesto: str | None = None
    # "Hasta agotar stock", "solo por la mañana". Corta: no es un aviso publicitario.
    nota: str = ""
    estado: EstadoOferta = EstadoOferta.ACTIVA
    id: int | None = None
    auditoria: Auditoria | None = field(default=None, compare=False)

    def __post_init__(self):
        if self.monto <= 0:
            raise DatoInvalido("El precio de la oferta tiene que ser mayor a cero")
        if self.hasta <= self.desde:
            raise DatoInvalido("La oferta tiene que terminar después de empezar")
        nota = " ".join((self.nota or "").split())
        if len(nota) > LARGO_MAXIMO_NOTA:
            raise DatoInvalido(f"La nota pasa de {LARGO_MAXIMO_NOTA} caracteres")
        object.__setattr__(self, "nota", nota)

    @classmethod
    def nueva(cls, *, id_vendedor: int, codigo_mercado: str, codigo_producto: str, monto: float,
              presentacion: Presentacion, horas: int, ahora: datetime, numero_puesto: str | None = None,
              nota: str = "") -> Oferta:
        if horas not in DURACIONES_HORAS:
            raise DatoInvalido("La oferta dura 24, 48 o 72 horas")
        return cls(
            id_vendedor=id_vendedor, codigo_mercado=codigo_mercado, codigo_producto=codigo_producto,
            monto=monto, presentacion=presentacion, desde=ahora, hasta=ahora + timedelta(hours=horas),
            numero_puesto=numero_puesto, nota=nota,
        )

    @property
    def precio_por_unidad_base(self) -> float:
        """Bs por kilo (o litro, o unidad): con eso se compara contra el sistema."""
        return round(self.monto / self.presentacion.factor, 4)

    def vigente(self, ahora: datetime) -> bool:
        return self.estado is EstadoOferta.ACTIVA and self.desde <= ahora < self.hasta

    def vencida(self, ahora: datetime) -> bool:
        return ahora >= self.hasta

    def a_revision(self) -> Oferta:
        return replace(self, estado=EstadoOferta.EN_REVISION)

    def reactivar(self) -> Oferta:
        return replace(self, estado=EstadoOferta.ACTIVA)

    def retirar(self) -> Oferta:
        return replace(self, estado=EstadoOferta.RETIRADA)


@dataclass(frozen=True, slots=True)
class Confirmacion:
    """Un comprador dice si la oferta estaba así ("¿Lo viste así?"). Una por persona y oferta."""

    id_oferta: int
    id_usuario: int
    la_vio_asi: bool
    creado_en: datetime


def ahorro_frente_al_sistema(precio_oferta: float, precio_sistema: float) -> float | None:
    """
    Cuánto se ahorra por unidad base frente al precio del sistema. None si
    la oferta no es más barata: entonces no es una oferta, es un precio.
    """
    ahorro = round(precio_sistema - precio_oferta, 2)
    return ahorro if ahorro > 0 else None


def hay_que_pausar(confirmaciones: list[Confirmacion]) -> bool:
    """Dos personas DISTINTAS dijeron que no estaba así."""
    return len({c.id_usuario for c in confirmaciones if not c.la_vio_asi}) >= DESMENTIDOS_PARA_PAUSAR
