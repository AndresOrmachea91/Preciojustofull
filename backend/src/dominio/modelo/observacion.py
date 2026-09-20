from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum

from src.dominio.valor import (
    VARIEDAD_DESCONOCIDA, Ambito, Dinero, NivelConfianza, NivelPrecio, Periodo,
    TipoPrecio, UnidadCanonica,
)

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
    # El par ORIGINAL (monto, unidad) tal como lo dijo la fuente, más la
    # cantidad de esa unidad que cubre el monto: "Bs 75,87 por 760 gramos".
    # Se conserva siempre; la conversión canónica se deriva y nunca lo pisa.
    precio: Dinero
    # Cuándo el sistema lo capturó. NO es cuándo se observó el precio.
    capturada_en: datetime
    # Para reportes ciudadanos: cuánto vale la palabra de quien reportó.
    reputacion_informante: float = 1.0
    # Si es CIUDAD, codigo_mercado es el código de la ciudad ("la_paz") y
    # el dato es referencia para estimar, no medición de un local.
    ambito: Ambito = Ambito.PUNTO_VENTA
    cantidad: float = 1.0
    # Variedad o presentación ("holandesa", "en gancho"). DESCONOCIDA es un
    # marcador explícito: no se rellena con algo plausible.
    variedad: str = VARIEDAD_DESCONOCIDA
    # Cuándo se observó el precio, según el DATO (la columna del día en la
    # tabla del SIIP, la fecha que declaró el informante). None significa
    # "no la tengo", que es distinto de "es la de captura": rellenarla con
    # la captura inventaría precisión justo en el campo que decide qué es
    # reciente.
    fecha_observacion: date | None = None
    tipo_precio: TipoPrecio = TipoPrecio.DESCONOCIDO
    # Foto, URL del boletín, número de ticket. Opcional.
    evidencia: str | None = None

    def __post_init__(self):
        if self.cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor a cero")
        if not self.variedad or not self.variedad.strip():
            raise ValueError(
                f"La variedad no puede ir vacía: usar {VARIEDAD_DESCONOCIDA!r} si no se conoce"
            )
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
    def es_convertible(self) -> bool:
        """
        Si el par original se puede llevar a una unidad canónica. Una
        "bolsa" o un "montón" sin peso declarado no convierten: la
        observación se conserva igual, pero queda fuera de todo cálculo
        que exija unidad canónica.
        """
        return self.precio.unidad.es_conocida()

    @property
    def unidad_canonica(self) -> UnidadCanonica | None:
        if not self.es_convertible:
            return None
        return self.precio.unidad.equivalencia()[0]

    @property
    def variedad_conocida(self) -> bool:
        return self.variedad != VARIEDAD_DESCONOCIDA

    @property
    def fecha_observacion_conocida(self) -> bool:
        return self.fecha_observacion is not None

    @property
    def confianza(self) -> NivelConfianza:
        if self.fuente is Fuente.CIUDADANO and self.reputacion_informante < 0.4:
            return NivelConfianza.BAJO
        return self.fuente.confianza_base

    def precio_canonico(self) -> float:
        """Precio por UNA unidad canónica. Lanza UnidadDesconocida si no convierte."""
        valor, _ = self.precio.por_unidad_canonica()
        return round(valor / self.cantidad, 6)

