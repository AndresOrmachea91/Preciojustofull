from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.dominio.valor import Dinero, Periodo, NivelConfianza


class Fuente(str, Enum):
    SIIP_DIARIO = "siip_diario"       # mayorista, automático
    SIIP_IPC = "siip_ipc"             # minorista de referencia, automático
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


class NivelPrecio(str, Enum):
    MAYORISTA = "mayorista"
    MINORISTA = "minorista"


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

    @property
    def confianza(self) -> NivelConfianza:
        if self.fuente is Fuente.CIUDADANO and self.reputacion_informante < 0.4:
            return NivelConfianza.BAJO
        return self.fuente.confianza_base

    def precio_canonico(self) -> float:
        valor, _ = self.precio.por_unidad_canonica()
        return valor

