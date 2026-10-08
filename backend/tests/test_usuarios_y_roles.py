"""
Reglas de cuentas, sesiones y revisión de reportes, sobre los casos de uso.

No pasan por HTTP: son las reglas que la web, la app móvil y la consola
comparten, y se prueban donde viven.
"""
from datetime import datetime, timezone

import pytest

from src.aplicacion.casos_uso.administracion.gestionar_usuarios import AdministrarUsuarios
from src.aplicacion.casos_uso.cuentas.iniciar_sesion import IniciarSesion, ResolverSesion
from src.aplicacion.casos_uso.cuentas.registrar_usuario import RegistrarUsuario
from src.aplicacion.casos_uso.administracion.validar_reportes import ValidarReportes
from src.aplicacion.casos_uso.usuario.reportar_precio import RegistrarReporteCiudadano
from src.dominio.excepciones import (
    ContrasenaDebil, CorreoInvalido, CorreoYaRegistrado, CredencialesInvalidas, PermisoDenegado,
    ReporteYaRevisado, SinAdministradores, UnidadDesconocida,
)
from src.dominio.modelo import EstadoReporte, Fuente, Permiso, Rol, Usuario
from src.infraestructura.adaptadores.salida.memoria.cuentas import (
    ReportesEnMemoria, UsuariosEnMemoria,
)
from src.infraestructura.adaptadores.salida.seguridad.cifrador import CifradorScrypt
from src.infraestructura.adaptadores.salida.seguridad.tokens import EmisorJwt

SECRETO = "x" * 40


@pytest.fixture
def entorno(repositorios):
    productos, mercados, observaciones = repositorios
    usuarios, reportes = UsuariosEnMemoria(), ReportesEnMemoria()
    cifrador, tokens = CifradorScrypt(), EmisorJwt(SECRETO)
    alta = RegistrarUsuario(usuarios, cifrador)
    admin = alta.crear_como_sistema("admin@pj.bo", "Admin", "clave1234", Rol.ADMINISTRADOR)
    return {
        "usuarios": usuarios, "reportes": reportes, "observaciones": observaciones,
        "alta": alta, "admin": admin,
        "ingresar": IniciarSesion(usuarios, cifrador, tokens),
        "resolver": ResolverSesion(usuarios, tokens),
        "administrar": AdministrarUsuarios(usuarios, cifrador, mercados),
        "reportar": RegistrarReporteCiudadano(productos, mercados, reportes),
        "validar": ValidarReportes(reportes, observaciones, usuarios),
    }


# --- dominio ------------------------------------------------------------------

def _usuario(rol, activo=True):
    return Usuario("a@b.co", "A", rol, "h", datetime.now(timezone.utc), activo=activo, id=1)


def test_cada_rol_tiene_solo_sus_permisos():
    assert _usuario(Rol.USUARIO).puede(Permiso.REPORTAR_PRECIO)
    assert not _usuario(Rol.USUARIO).puede(Permiso.PUBLICAR_PRECIO_PROPIO)
    assert _usuario(Rol.VENDEDOR).puede(Permiso.PUBLICAR_PRECIO_PROPIO)
    assert not _usuario(Rol.VENDEDOR).puede(Permiso.GESTIONAR_USUARIOS)
    assert all(_usuario(Rol.ADMINISTRADOR).puede(p) for p in Permiso)


def test_una_cuenta_desactivada_no_puede_nada():
    assert not any(_usuario(Rol.ADMINISTRADOR, activo=False).puede(p) for p in Permiso)


def test_el_cifrador_no_guarda_la_contrasena_y_la_verifica():
    c = CifradorScrypt()
    h = c.cifrar("clave1234")
    assert "clave1234" not in h
    assert c.cifrar("clave1234") != h          # sal distinta cada vez
    assert c.verificar("clave1234", h)
    assert not c.verificar("clave1235", h)
    assert not c.verificar("clave1234", "basura")


def test_un_token_ajeno_o_vencido_no_identifica_a_nadie():
    emisor = EmisorJwt(SECRETO)
    token = emisor.emitir(_usuario(Rol.USUARIO))
    assert emisor.leer(token) == 1
    assert EmisorJwt("y" * 40).leer(token) is None
    assert EmisorJwt(SECRETO, horas_validez=-1).leer(EmisorJwt(SECRETO, horas_validez=-1).emitir(_usuario(Rol.USUARIO))) is None
    assert emisor.leer("no.es.un.token") is None


# --- registro e ingreso ---------------------------------------------------

def test_el_registro_publico_siempre_crea_un_usuario_comun(entorno):
    u = entorno["alta"].registrarse("  Ana@Correo.BO ", "Ana", "clave1234")
    assert u.rol is Rol.USUARIO
    assert u.correo == "ana@correo.bo"
    assert u.id is not None


@pytest.mark.parametrize("correo,contrasena,error", [
    ("sin-arroba", "clave1234", CorreoInvalido),
    ("ana@correo.bo", "corta1", ContrasenaDebil),
    ("ana@correo.bo", "soloLetras", ContrasenaDebil),
    ("ana@correo.bo", "12345678", ContrasenaDebil),
])
def test_el_registro_valida_correo_y_contrasena(entorno, correo, contrasena, error):
    with pytest.raises(error):
        entorno["alta"].registrarse(correo, "Ana", contrasena)


def test_no_se_repite_un_correo_aunque_cambien_las_mayusculas(entorno):
    entorno["alta"].registrarse("ana@correo.bo", "Ana", "clave1234")
    with pytest.raises(CorreoYaRegistrado):
        entorno["alta"].registrarse("ANA@correo.bo", "Otra", "clave1234")


def test_ingresar_devuelve_un_token_que_resuelve_al_usuario(entorno):
    sesion = entorno["ingresar"].ejecutar("ADMIN@pj.bo", "clave1234")
    assert sesion.usuario.id == entorno["admin"].id
    assert entorno["resolver"].ejecutar(sesion.token).id == entorno["admin"].id


@pytest.mark.parametrize("correo,contrasena", [
    ("admin@pj.bo", "equivocada1"), ("nadie@pj.bo", "clave1234"), ("no-es-correo", "x"),
])
def test_cualquier_fallo_de_ingreso_da_el_mismo_error(entorno, correo, contrasena):
    with pytest.raises(CredencialesInvalidas):
        entorno["ingresar"].ejecutar(correo, contrasena)


def test_desactivar_una_cuenta_corta_su_sesion_y_su_ingreso(entorno):
    ana = entorno["alta"].registrarse("ana@correo.bo", "Ana", "clave1234")
    token = entorno["ingresar"].ejecutar("ana@correo.bo", "clave1234").token

    entorno["administrar"].actualizar(entorno["admin"], ana.id, activo=False)

    assert entorno["resolver"].ejecutar(token) is None
    with pytest.raises(CredencialesInvalidas):
        entorno["ingresar"].ejecutar("ana@correo.bo", "clave1234")


# --- administración ------------------------------------------------------

def test_solo_el_administrador_crea_y_lista_cuentas(entorno):
    ana = entorno["alta"].registrarse("ana@correo.bo", "Ana", "clave1234")
    with pytest.raises(PermisoDenegado):
        entorno["alta"].crear(ana, "x@y.bo", "X", "clave1234", Rol.ADMINISTRADOR)
    with pytest.raises(PermisoDenegado):
        entorno["administrar"].listar(ana)

    vend = entorno["alta"].crear(entorno["admin"], "vend@pj.bo", "Vend", "clave1234", Rol.VENDEDOR)
    assert vend.rol is Rol.VENDEDOR
    assert [u.correo for u in entorno["administrar"].listar(entorno["admin"])] == [
        "admin@pj.bo", "ana@correo.bo", "vend@pj.bo",
    ]


def test_el_cambio_de_rol_rige_en_la_siguiente_peticion(entorno):
    ana = entorno["alta"].registrarse("ana@correo.bo", "Ana", "clave1234")
    token = entorno["ingresar"].ejecutar("ana@correo.bo", "clave1234").token

    entorno["administrar"].actualizar(entorno["admin"], ana.id, rol=Rol.VENDEDOR)

    assert entorno["resolver"].ejecutar(token).rol is Rol.VENDEDOR


def test_no_se_puede_quedar_sin_administradores(entorno):
    admin = entorno["admin"]
    with pytest.raises(SinAdministradores):
        entorno["administrar"].actualizar(admin, admin.id, rol=Rol.USUARIO)
    with pytest.raises(SinAdministradores):
        entorno["administrar"].actualizar(admin, admin.id, activo=False)

    otro = entorno["alta"].crear(admin, "otro@pj.bo", "Otro", "clave1234", Rol.ADMINISTRADOR)
    entorno["administrar"].actualizar(otro, admin.id, activo=False)   # ahora sí: queda otro
    assert entorno["usuarios"].contar_administradores_activos() == 1


def test_restablecer_contrasena_cambia_la_que_sirve_para_ingresar(entorno):
    ana = entorno["alta"].registrarse("ana@correo.bo", "Ana", "clave1234")
    entorno["administrar"].restablecer_contrasena(entorno["admin"], ana.id, "nueva5678")
    with pytest.raises(CredencialesInvalidas):
        entorno["ingresar"].ejecutar("ana@correo.bo", "clave1234")
    assert entorno["ingresar"].ejecutar("ana@correo.bo", "nueva5678").usuario.id == ana.id


# --- reportes ----------------------------------------------------------------

def _ciudadanas(entorno):
    return [o for o in entorno["observaciones"].buscar("tomate", "rodriguez") if o.fuente is Fuente.CIUDADANO]


def test_un_reporte_queda_pendiente_y_no_entra_al_motor(entorno):
    ana = entorno["alta"].registrarse("ana@correo.bo", "Ana", "clave1234")
    antes = len(_ciudadanas(entorno))

    r = entorno["reportar"].ejecutar(ana, "tomate", "rodriguez", 9.5, "KILO")

    assert r.estado is EstadoReporte.PENDIENTE and r.id_autor == ana.id
    assert len(_ciudadanas(entorno)) == antes


def test_un_reporte_con_unidad_desconocida_se_rechaza_al_recibirlo(entorno):
    ana = entorno["alta"].registrarse("ana@correo.bo", "Ana", "clave1234")
    with pytest.raises(UnidadDesconocida):
        entorno["reportar"].ejecutar(ana, "tomate", "rodriguez", 9.5, "PUÑADO")


def test_aprobar_convierte_el_reporte_en_observacion_con_la_reputacion_del_rol(entorno):
    admin = entorno["admin"]
    vend = entorno["alta"].crear(admin, "vend@pj.bo", "Vend", "clave1234", Rol.VENDEDOR)
    antes = len(_ciudadanas(entorno))
    r = entorno["reportar"].ejecutar(vend, "tomate", "rodriguez", 9.5, "KILO")

    aprobado = entorno["validar"].aprobar(admin, r.id)

    assert aprobado.estado is EstadoReporte.APROBADO and aprobado.id_revisor == admin.id
    nuevas = _ciudadanas(entorno)[antes:]
    assert len(nuevas) == 1
    assert nuevas[0].reputacion_informante == 0.6
    assert nuevas[0].evidencia == f"reporte:{r.id}"
    assert nuevas[0].fecha_observacion == r.creado_en.date()


def test_rechazar_guarda_el_motivo_y_no_crea_observacion(entorno):
    ana = entorno["alta"].registrarse("ana@correo.bo", "Ana", "clave1234")
    antes = len(_ciudadanas(entorno))
    r = entorno["reportar"].ejecutar(ana, "tomate", "rodriguez", 95, "KILO")

    rechazado = entorno["validar"].rechazar(entorno["admin"], r.id, "Precio fuera de rango")

    assert rechazado.estado is EstadoReporte.RECHAZADO
    assert rechazado.motivo_rechazo == "Precio fuera de rango"
    assert len(_ciudadanas(entorno)) == antes
    assert entorno["validar"].listar(entorno["admin"]) == []


def test_un_reporte_revisado_no_se_vuelve_a_revisar(entorno):
    ana = entorno["alta"].registrarse("ana@correo.bo", "Ana", "clave1234")
    r = entorno["reportar"].ejecutar(ana, "tomate", "rodriguez", 9.5, "KILO")
    entorno["validar"].aprobar(entorno["admin"], r.id)
    with pytest.raises(ReporteYaRevisado):
        entorno["validar"].aprobar(entorno["admin"], r.id)
    with pytest.raises(ReporteYaRevisado):
        entorno["validar"].rechazar(entorno["admin"], r.id, "tarde")


def test_solo_el_administrador_revisa_reportes(entorno):
    vend = entorno["alta"].crear(entorno["admin"], "vend@pj.bo", "Vend", "clave1234", Rol.VENDEDOR)
    r = entorno["reportar"].ejecutar(vend, "tomate", "rodriguez", 9.5, "KILO")
    with pytest.raises(PermisoDenegado):
        entorno["validar"].aprobar(vend, r.id)
    with pytest.raises(PermisoDenegado):
        entorno["validar"].listar(vend)


def test_el_vendedor_tiene_su_puesto_y_solo_uno_que_exista(entorno):
    from src.dominio.excepciones import MercadoNoEncontrado
    admin = entorno["admin"]
    vend = entorno["alta"].crear(admin, "vend@pj.bo", "Vend", "clave1234", Rol.VENDEDOR)

    asignado = entorno["administrar"].actualizar(admin, vend.id, punto_venta="rodriguez")
    assert asignado.codigo_punto_venta == "rodriguez"
    # Cambiar otra cosa no le quita el puesto.
    assert entorno["administrar"].actualizar(admin, vend.id, activo=False).codigo_punto_venta == "rodriguez"
    with pytest.raises(MercadoNoEncontrado):
        entorno["administrar"].actualizar(admin, vend.id, punto_venta="no_existe")
    assert entorno["administrar"].actualizar(admin, vend.id, punto_venta=None).codigo_punto_venta is None
