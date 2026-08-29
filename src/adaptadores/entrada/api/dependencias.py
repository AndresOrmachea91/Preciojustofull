"""
Raíz de composición: el único lugar donde se decide qué adaptador concreto
se enchufa a cada puerto.

Cambiar de repositorios en memoria a PostgreSQL es cambiar estas líneas.
Ningún caso de uso ni entidad del dominio se entera.
"""
from __future__ import annotations
from functools import lru_cache

from src.adaptadores.salida.memoria.repositorios import datos_de_ejemplo
from src.aplicacion.casos_uso.calcular_canasta import CalcularCanastaCasoUso
from src.aplicacion.casos_uso.comparar_mercados import CompararMercadosCasoUso
from src.aplicacion.casos_uso.consultar_precio import ConsultarPrecioProducto
from src.aplicacion.casos_uso.registrar_reporte import RegistrarReporteCiudadano
from src.dominio.servicio.motor_fusion import MotorFusion


@lru_cache
def _repositorios():
    # TODO: cuando exista el adaptador de PostgreSQL, elegir acá según
    # config.base_datos_url. El resto del sistema no cambia.
    return datos_de_ejemplo()


@lru_cache
def obtener_motor() -> MotorFusion:
    return MotorFusion()


def obtener_productos():
    return _repositorios()[0]


def obtener_mercados():
    return _repositorios()[1]


def obtener_observaciones():
    return _repositorios()[2]


def caso_consultar_precio() -> ConsultarPrecioProducto:
    p, _, o = _repositorios()
    return ConsultarPrecioProducto(p, o, obtener_motor())


def caso_comparar_mercados() -> CompararMercadosCasoUso:
    p, m, o = _repositorios()
    return CompararMercadosCasoUso(p, m, o, obtener_motor())


def caso_calcular_canasta() -> CalcularCanastaCasoUso:
    _, m, o = _repositorios()
    return CalcularCanastaCasoUso(m, o, obtener_motor())


def caso_registrar_reporte() -> RegistrarReporteCiudadano:
    p, m, o = _repositorios()
    return RegistrarReporteCiudadano(p, m, o)

