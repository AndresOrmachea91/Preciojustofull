"""
Raíz de composición: el único lugar donde se decide qué adaptador concreto
se enchufa a cada puerto.

Cambiar de repositorios en memoria a PostgreSQL es cambiar estas líneas.
Ningún caso de uso ni entidad del dominio se entera.
"""
from __future__ import annotations
from functools import lru_cache

import logging

from src.infraestructura.adaptadores.salida.memoria.repositorios import datos_de_ejemplo
from src.infraestructura.adaptadores.salida.persistencia.repositorios import (
    MercadosPostgres, ObservacionesPostgres, ProductosPostgres,
)
from src.infraestructura.adaptadores.salida.persistencia.sesion import (
    crear_esquema, crear_motor, fabrica_sesiones,
)
from src.aplicacion.casos_uso.calcular_canasta import CalcularCanastaCasoUso
from src.aplicacion.casos_uso.comparar_mercados import CompararMercadosCasoUso
from src.aplicacion.casos_uso.consultar_precio import ConsultarPrecioProducto
from src.aplicacion.casos_uso.registrar_reporte import RegistrarReporteCiudadano
from src.configuracion import config
from src.dominio.servicio.motor_fusion import MotorFusion

log = logging.getLogger(__name__)


@lru_cache
def _repositorios():
    """
    Acá —y solo acá— se decide qué adaptador se enchufa a cada puerto.

    Con BASE_DATOS_URL configurada usa PostgreSQL; sin ella, los
    repositorios en memoria, para poder levantar la API sin instalar nada.
    Ni el dominio ni los casos de uso se enteran de la diferencia.
    """
    if not config.base_datos_url:
        log.warning("Sin BASE_DATOS_URL: usando repositorios en memoria")
        return datos_de_ejemplo()

    motor = crear_motor(config.base_datos_url)
    crear_esquema(motor)
    fabrica = fabrica_sesiones(motor)
    log.info("Conectado a la base de datos")
    return (
        ProductosPostgres(fabrica),
        MercadosPostgres(fabrica),
        ObservacionesPostgres(fabrica),
    )


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
    p, m, o = _repositorios()
    return ConsultarPrecioProducto(p, o, obtener_motor(), mercados=m)


def caso_comparar_mercados() -> CompararMercadosCasoUso:
    p, m, o = _repositorios()
    return CompararMercadosCasoUso(p, m, o, obtener_motor())


def caso_calcular_canasta() -> CalcularCanastaCasoUso:
    _, m, o = _repositorios()
    return CalcularCanastaCasoUso(m, o, obtener_motor())


def caso_registrar_reporte() -> RegistrarReporteCiudadano:
    p, m, o = _repositorios()
    return RegistrarReporteCiudadano(p, m, o)

