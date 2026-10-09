"""
Raíz de composición: el único lugar donde se decide qué adaptador concreto
se enchufa a cada puerto.

Cambiar de repositorios en memoria a PostgreSQL es cambiar estas líneas.
Ningún caso de uso ni entidad del dominio se entera.
"""
from __future__ import annotations
from functools import lru_cache

import logging

from src.infraestructura.adaptadores.salida.memoria.cuentas import (
    ReportesEnMemoria, UsuariosEnMemoria,
)
from src.infraestructura.adaptadores.salida.memoria.repositorios import datos_de_ejemplo
from src.infraestructura.adaptadores.salida.persistencia.cuentas import (
    ReportesPostgres, UsuariosPostgres,
)
from src.infraestructura.adaptadores.salida.persistencia.repositorios import (
    MercadosPostgres, ObservacionesPostgres, ProductosPostgres,
)
from src.infraestructura.adaptadores.salida.persistencia.sesion import (
    crear_esquema, crear_motor, fabrica_sesiones,
)
from src.infraestructura.adaptadores.salida.seguridad.cifrador import CifradorScrypt
from src.infraestructura.adaptadores.salida.seguridad.tokens import EmisorJwt
from src.aplicacion.casos_uso.precios.calcular_canasta import CalcularCanastaCasoUso
from src.aplicacion.casos_uso.precios.comparar_mercados import CompararMercadosCasoUso
from src.aplicacion.casos_uso.precios.consultar_precio import ConsultarPrecioProducto
from src.aplicacion.casos_uso.administracion.gestionar_usuarios import AdministrarUsuarios
from src.aplicacion.casos_uso.cuentas.iniciar_sesion import IniciarSesion, ResolverSesion
from src.aplicacion.casos_uso.cuentas.registrar_usuario import RegistrarUsuario
from src.aplicacion.casos_uso.administracion.gestionar_catalogo import (
    GestionarProductos, GestionarPuntosVenta,
)
from src.aplicacion.casos_uso.administracion.validar_reportes import ValidarReportes
from src.aplicacion.casos_uso.usuario.reportar_precio import RegistrarReporteCiudadano
from src.configuracion import config
from src.dominio.modelo import Rol
from src.dominio.servicio.motor_fusion import MotorFusion

log = logging.getLogger(__name__)


@lru_cache
def _fabrica():
    """La conexión, una sola vez por proceso. None si no hay base configurada."""
    if not config.base_datos_url:
        return None
    motor = crear_motor(config.base_datos_url)
    crear_esquema(motor)
    log.info("Conectado a la base de datos")
    return fabrica_sesiones(motor)


@lru_cache
def _repositorios():
    """
    Acá —y solo acá— se decide qué adaptador se enchufa a cada puerto.

    Con BASE_DATOS_URL configurada usa PostgreSQL; sin ella, los
    repositorios en memoria, para poder levantar la API sin instalar nada.
    Ni el dominio ni los casos de uso se enteran de la diferencia.
    """
    fabrica = _fabrica()
    if fabrica is None:
        log.warning("Sin BASE_DATOS_URL: usando repositorios en memoria")
        return datos_de_ejemplo()
    return (
        ProductosPostgres(fabrica),
        MercadosPostgres(fabrica),
        ObservacionesPostgres(fabrica),
    )


@lru_cache
def _cuentas():
    fabrica = _fabrica()
    if fabrica is None:
        return UsuariosEnMemoria(), ReportesEnMemoria()
    return UsuariosPostgres(fabrica), ReportesPostgres(fabrica)


@lru_cache
def _cifrador() -> CifradorScrypt:
    return CifradorScrypt()


@lru_cache
def _tokens() -> EmisorJwt:
    return EmisorJwt(config.secreto_tokens(), horas_validez=config.sesion_horas)


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
    p, m, _ = _repositorios()
    return RegistrarReporteCiudadano(p, m, _cuentas()[1])


def caso_validar_reportes() -> ValidarReportes:
    usuarios, reportes = _cuentas()
    return ValidarReportes(reportes, _repositorios()[2], usuarios)


def caso_registrar_usuario() -> RegistrarUsuario:
    return RegistrarUsuario(_cuentas()[0], _cifrador())


def caso_iniciar_sesion() -> IniciarSesion:
    return IniciarSesion(_cuentas()[0], _cifrador(), _tokens())


def caso_resolver_sesion() -> ResolverSesion:
    return ResolverSesion(_cuentas()[0], _tokens())


def caso_administrar_usuarios() -> AdministrarUsuarios:
    return AdministrarUsuarios(_cuentas()[0], _cifrador(), _repositorios()[1])


def caso_gestionar_puntos_venta() -> GestionarPuntosVenta:
    return GestionarPuntosVenta(_repositorios()[1], _cuentas()[0])


def caso_gestionar_productos() -> GestionarProductos:
    return GestionarProductos(_repositorios()[0])


def asegurar_admin_inicial() -> None:
    """
    Crea el primer administrador desde ADMIN_INICIAL_CORREO y
    ADMIN_INICIAL_CONTRASENA, solo si todavía no hay ninguno. Es lo que
    permite levantar un servidor nuevo (o un contenedor) sin entrar a la
    consola a crear la cuenta a mano.
    """
    if not (config.admin_inicial_correo and config.admin_inicial_contrasena):
        return
    usuarios = _cuentas()[0]
    if usuarios.contar_administradores_activos() > 0:
        return
    caso_registrar_usuario().crear_como_sistema(
        config.admin_inicial_correo, "Administrador", config.admin_inicial_contrasena, Rol.ADMINISTRADOR,
    )
    log.info("Administrador inicial creado: %s", config.admin_inicial_correo)
