from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.dominio.valor import Ambito, Dinero, NivelConfianza, NivelPrecio, Periodo

__all__ = ["Fuente", "NivelPrecio", "Observacion"]


class Fuente(str, Enum):
    SIIP_DIARIO = "siip_diario"       # mayorista, por ciudad, automático
    SIIP_IPC = "siip_ipc"             # consumidor final, por ciudad, automático
    MEDIOS = "medios"                 # reportes audiovisuales
    CIUDADANO = "ciudadano"           # reporte desde el celular
    CAMPO = "campo"                   # levantamiento verificado

    @property
    def confianza_base(self) -> NivelConfianza:
        return {
            Fuente.CAMPO: NivelConfianza.VERIFICADO,
            Fuente.SIIP_DIARIO: NivelConfianza.ALTO,
            Fuente.SIIP_IPC: NivelConfianza.ALTO,
            Fuente.MEDIOS: NivelConfianza.MEDIO,
            Fuente.CIUDADANO: NivelConfianza.BAJO,
        }[self]

    @property
    def nivel_fijo(self) -> NivelPrecio | None:
        """
        El nivel que la fuente cotiza SIEMPRE. El SIIP diario es el precio
        mayorista (arroz por quintal, carne en gancho); el IPC es lo que
        paga el consumidor. Una fuente de campo no tiene nivel fijo: mide
        donde está parada, sea un puesto o un mayorista.
        """
        return {
            Fuente.SIIP_DIARIO: NivelPrecio.MAYORISTA,
            Fuente.SIIP_IPC: NivelPrecio.MINORISTA,
        }.get(self)

    @property
    def ambito(self) -> Ambito:
        """Las dos fuentes del SIIP publican un valor por ciudad, no por puesto."""
        if self in (Fuente.SIIP_DIARIO, Fuente.SIIP_IPC):
            return Ambito.CIUDAD
        return Ambito.PUNTO_VENTA


@dataclass(frozen=True, slots=True)
class Observacion:
    """
    Lo que una fuente afirmó, tal cual lo afirmó. Es INMUTABLE.

    Nunca se corrige ni se sobrescribe: si el motor de fusión cambia, se
    recalcula el consolidado a partir de las observaciones originales. Sin
    eso no se podría comparar dos configuraciones del motor sobre los
    mismos datos, que es lo que permite demostrar que fusionar aporta algo.
    """

    fuente: Fuente
    nivel: NivelPrecio
    codigo_producto: str
    codigo_mercado: str
    periodo: Periodo
    precio: Dinero
    capturada_en: datetime
    # Para reportes ciudadanos: cuánto vale la palabra de quien reportó.
    reputacion_informante: float = 1.0
    # Si es CIUDAD, codigo_mercado es el código de la ciudad ("la_paz") y
    # el dato es referencia para estimar, no medición de un local.
    ambito: Ambito = Ambito.PUNTO_VENTA

    def __post_init__(self):
        fijo = self.fuente.nivel_fijo
        if fijo is not None and self.nivel is not fijo:
            raise ValueError(
                f"La fuente {self.fuente.value} solo cotiza {fijo.value}, no {self.nivel.value}"
            )
        if self.ambito is not self.fuente.ambito:
            raise ValueError(
                f"La fuente {self.fuente.value} publica por {self.fuente.ambito.value}, "
                f"no por {self.ambito.value}"
            )

    @property
    def es_referencia_de_ciudad(self) -> bool:
        return self.ambito is Ambito.CIUDAD

    @property
    def confianza(self) -> NivelConfianza:
        if self.fuente is Fuente.CIUDADANO and self.reputacion_informante < 0.4:
            return NivelConfianza.BAJO
        return self.fuente.confianza_base

    def precio_canonico(self) -> float:
        valor, _ = self.precio.por_unidad_canonica()
        return valor

