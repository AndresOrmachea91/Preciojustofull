"""
Raíz de composición: el único lugar donde se decide qué adaptador concreto
se enchufa a cada puerto.

Cambiar de repositorios en memoria a PostgreSQL es cambiar estas líneas.
Ningún caso de uso ni entidad del dominio se entera.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

import logging

from src.infraestructura.adaptadores.salida.memoria.cuentas import (
    AuditoriaEnMemoria, ReportesEnMemoria, UsuariosEnMemoria,
)
from src.infraestructura.adaptadores.salida.memoria.listas import ListasEnMemoria
from src.infraestructura.adaptadores.salida.memoria.repositorios import datos_de_ejemplo
from src.infraestructura.adaptadores.salida.persistencia.auditoria import AuditoriaPostgres
from src.infraestructura.adaptadores.salida.persistencia.cuentas import (
    ReportesPostgres, UsuariosPostgres,
)
from src.infraestructura.adaptadores.salida.persistencia.listas import ListasPostgres
from src.infraestructura.adaptadores.salida.persistencia.repositorios import (
    MercadosPostgres, ObservacionesPostgres, ProductosPostgres,
)
from src.infraestructura.adaptadores.salida.persistencia.sesion import (
    crear_esquema, crear_motor, fabrica_sesiones,
)
from src.infraestructura.adaptadores.salida.seguridad.cifrador import CifradorScrypt
from src.infraestructura.adaptadores.salida.correo.smtp import CorreoEnBitacora, CorreoSmtp
from src.infraestructura.adaptadores.salida.seguridad.enlaces import EnlacesJwt
from src.infraestructura.adaptadores.salida.seguridad.tokens import EmisorJwt
from src.aplicacion.casos_uso.precios.calcular_canasta import CalcularCanastaCasoUso
from src.aplicacion.casos_uso.precios.comparar_mercados import CompararMercadosCasoUso
from src.aplicacion.casos_uso.precios.consultar_precio import ConsultarPrecioProducto
from src.aplicacion.casos_uso.precios.historial_precio import HistorialPrecio
from src.aplicacion.casos_uso.precios.evaluar_estimador import EvaluarEstimador
from src.aplicacion.casos_uso.administracion.importar_campo import ImportarCotizacionesCampo
from src.aplicacion.casos_uso.administracion.salud_sistema import VerSaludSistema
from src.infraestructura.adaptadores.salida.memoria.salud import SaludEnMemoria
from src.infraestructura.adaptadores.salida.persistencia.salud import SaludPostgres
from src.infraestructura.adaptadores.salida.respaldos.estado_archivo import RespaldosEnArchivo
from src.aplicacion.casos_uso.administracion.gestionar_usuarios import AdministrarUsuarios
from src.aplicacion.casos_uso.cuentas.iniciar_sesion import IniciarSesion, ResolverSesion
from src.aplicacion.casos_uso.cuentas.recuperar_contrasena import RecuperarContrasena
from src.aplicacion.casos_uso.cuentas.registrar_usuario import RegistrarUsuario
from src.aplicacion.casos_uso.administracion.gestionar_catalogo import (
    GestionarProductos, GestionarPuntosVenta,
)
from src.aplicacion.casos_uso.administracion.validar_reportes import ValidarReportes
from src.aplicacion.casos_uso.administracion.ver_auditoria import ConsultarReferencias, VerAuditoria
from src.aplicacion.casos_uso.usuario.listas_compras import GestionarListas
from src.aplicacion.casos_uso.usuario.mis_reportes import MisReportes
from src.aplicacion.casos_uso.usuario.reportar_precio import RegistrarReporteCiudadano
from src.aplicacion.casos_uso.vendedor.publicar_precio import MisPrecios, PublicarPrecioPropio
from src.configuracion import config
from src.dominio.modelo import Rol
from src.dominio.servicio.motor_fusion import MotorFusion

log = logging.getLogger(__name__)

# Bolivia no tiene horario de verano: UTC-4 todo el año. "Hoy" es el día
# del mercado, no el del servidor (que corre en UTC).
_BOLIVIA = timezone(timedelta(hours=-4))


def hoy_en_bolivia() -> date:
    return datetime.now(_BOLIVIA).date()


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
def _listas():
    fabrica = _fabrica()
    return ListasEnMemoria() if fabrica is None else ListasPostgres(fabrica)


@lru_cache
def _cifrador() -> CifradorScrypt:
    return CifradorScrypt()


@lru_cache
def _tokens() -> EmisorJwt:
    return EmisorJwt(config.secreto_tokens(), horas_validez=config.sesion_horas)


@lru_cache
def _enlaces() -> EnlacesJwt:
    return EnlacesJwt(config.secreto_tokens())


@lru_cache
def _correo():
    if not config.smtp_host:
        return CorreoEnBitacora()
    return CorreoSmtp(config.smtp_host, config.smtp_puerto, config.smtp_remitente,
                      config.smtp_usuario, config.smtp_clave, config.smtp_tls)


def caso_recuperar_contrasena() -> RecuperarContrasena:
    return RecuperarContrasena(_cuentas()[0], _enlaces(), _correo(), _cifrador(), config.url_publica)


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
    return ConsultarPrecioProducto(p, o, obtener_motor(), mercados=m, reloj=hoy_en_bolivia)


def caso_comparar_mercados() -> CompararMercadosCasoUso:
    p, m, o = _repositorios()
    return CompararMercadosCasoUso(p, m, o, obtener_motor(), reloj=hoy_en_bolivia)


def caso_historial_precio() -> HistorialPrecio:
    p, _, o = _repositorios()
    return HistorialPrecio(p, o)


def caso_calcular_canasta() -> CalcularCanastaCasoUso:
    p, m, o = _repositorios()
    return CalcularCanastaCasoUso(m, o, obtener_motor(), productos=p, reloj=hoy_en_bolivia)


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


def caso_ver_auditoria() -> VerAuditoria:
    fabrica = _fabrica()
    return VerAuditoria(AuditoriaEnMemoria(_cuentas()[0]) if fabrica is None else AuditoriaPostgres(fabrica))


def caso_consultar_referencias() -> ConsultarReferencias:
    return ConsultarReferencias()


def caso_administrar_usuarios() -> AdministrarUsuarios:
    return AdministrarUsuarios(_cuentas()[0], _cifrador(), _repositorios()[1])


def caso_gestionar_puntos_venta() -> GestionarPuntosVenta:
    return GestionarPuntosVenta(_repositorios()[1], _cuentas()[0])


def caso_gestionar_productos() -> GestionarProductos:
    return GestionarProductos(_repositorios()[0])


# --- usuario -------------------------------------------------------------------

def caso_mis_reportes() -> MisReportes:
    return MisReportes(_cuentas()[1])


def caso_gestionar_listas() -> GestionarListas:
    return GestionarListas(_listas(), _repositorios()[0], caso_calcular_canasta())


def caso_evaluar_estimador() -> EvaluarEstimador:
    p, m, o = _repositorios()
    return EvaluarEstimador(p, m, o, obtener_motor())


def caso_importar_campo() -> ImportarCotizacionesCampo:
    p, m, o = _repositorios()
    return ImportarCotizacionesCampo(p, m, o)


def caso_salud_sistema() -> VerSaludSistema:
    fabrica = _fabrica()
    salud = SaludEnMemoria(*_repositorios()) if fabrica is None else SaludPostgres(fabrica)
    return VerSaludSistema(salud, RespaldosEnArchivo(config.respaldos_dir))


# --- vendedor ------------------------------------------------------------------

def caso_publicar_precio() -> PublicarPrecioPropio:
    p, m, o = _repositorios()
    return PublicarPrecioPropio(p, m, o)


def caso_mis_precios() -> MisPrecios:
    p, m, o = _repositorios()
    return MisPrecios(p, m, o)


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
