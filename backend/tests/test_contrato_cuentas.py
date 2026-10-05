"""
Prueba de CONTRATO de los repositorios de usuarios y reportes: los mismos
casos contra el adaptador en memoria y contra el de SQLAlchemy (sobre
SQLite en memoria, sin servidor).
"""
from datetime import datetime, timedelta, timezone

import pytest

from src.dominio.modelo import EstadoReporte, Reporte, Rol, Usuario
from src.infraestructura.adaptadores.salida.memoria.cuentas import (
    ReportesEnMemoria, UsuariosEnMemoria,
)
from src.infraestructura.adaptadores.salida.persistencia.cuentas import (
    ReportesPostgres, UsuariosPostgres,
)
from src.infraestructura.adaptadores.salida.persistencia.sesion import (
    crear_esquema, crear_motor, fabrica_sesiones,
)

AHORA = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)


def _sqlalchemy():
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    fabrica = fabrica_sesiones(motor)
    return UsuariosPostgres(fabrica), ReportesPostgres(fabrica)


@pytest.fixture(params=["memoria", "sqlalchemy"], ids=["memoria", "sqlalchemy"])
def repos(request):
    return (UsuariosEnMemoria(), ReportesEnMemoria()) if request.param == "memoria" else _sqlalchemy()


def _usuario(correo="ana@pj.bo", rol=Rol.USUARIO, activo=True):
    return Usuario(correo, "Ana", rol, "scrypt$hash", AHORA, activo=activo)


def test_guardar_asigna_id_y_se_recupera_por_id_y_por_correo(repos):
    usuarios, _ = repos
    guardado = usuarios.guardar(_usuario())

    assert guardado.id is not None
    assert usuarios.obtener(guardado.id) == guardado
    assert usuarios.obtener_por_correo("ana@pj.bo") == guardado
    assert usuarios.obtener_por_correo("otro@pj.bo") is None
    assert usuarios.obtener(9999) is None


def test_guardar_con_id_actualiza_sin_duplicar(repos):
    usuarios, _ = repos
    u = usuarios.guardar(_usuario())
    usuarios.guardar(u.con_rol(Rol.RECOLECTOR).con_activo(False))

    assert len(usuarios.listar()) == 1
    leido = usuarios.obtener(u.id)
    assert leido.rol is Rol.RECOLECTOR and leido.activo is False
    assert leido.creado_en == AHORA


def test_cuenta_solo_administradores_activos(repos):
    usuarios, _ = repos
    usuarios.guardar(_usuario("a@pj.bo", Rol.ADMINISTRADOR))
    usuarios.guardar(_usuario("b@pj.bo", Rol.ADMINISTRADOR, activo=False))
    usuarios.guardar(_usuario("c@pj.bo", Rol.RECOLECTOR))
    assert usuarios.contar_administradores_activos() == 1


def test_reportes_se_guardan_filtran_y_revisan(repos):
    usuarios, reportes = repos
    autor = usuarios.guardar(_usuario())
    revisor = usuarios.guardar(_usuario("admin@pj.bo", Rol.ADMINISTRADOR))
    primero = reportes.guardar(Reporte("tomate", "rodriguez", 9.5, "KILO", autor.id, AHORA))
    segundo = reportes.guardar(Reporte("papa", "lanza", 4.0, "KILO", autor.id, AHORA + timedelta(hours=1)))

    reportes.guardar(primero.rechazar(revisor.id, AHORA + timedelta(hours=2), "Muy alto"))

    assert [r.id for r in reportes.listar()] == [primero.id, segundo.id]
    assert [r.id for r in reportes.listar(EstadoReporte.PENDIENTE)] == [segundo.id]
    leido = reportes.obtener(primero.id)
    assert leido.estado is EstadoReporte.RECHAZADO
    assert leido.id_revisor == revisor.id
    assert leido.motivo_rechazo == "Muy alto"
    assert leido.revisado_en == AHORA + timedelta(hours=2)
    assert reportes.obtener(9999) is None
