"""
La vista de auditoría del administrador: lee los 5 campos de todas las
tablas sin una tabla de logs, solo con permiso, y sin dejar inyectar SQL.
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from src.aplicacion.casos_uso.administracion.ver_auditoria import VerAuditoria
from src.dominio.excepciones import DatoInvalido, PermisoDenegado
from src.dominio.modelo import Producto, Rol, Usuario
from src.infraestructura.adaptadores.entrada.api import dependencias
from src.infraestructura.adaptadores.entrada.api.main import app
from src.infraestructura.adaptadores.salida.persistencia.auditable import como_actor
from src.infraestructura.adaptadores.salida.persistencia.auditoria import AuditoriaPostgres
from src.infraestructura.adaptadores.salida.persistencia.cuentas import UsuariosPostgres
from src.infraestructura.adaptadores.salida.persistencia.repositorios import ProductosPostgres
from src.infraestructura.adaptadores.salida.persistencia.sesion import (
    crear_esquema, crear_motor, fabrica_sesiones,
)

AHORA = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
ADMIN = Usuario("admin@pj.bo", "Admin", Rol.ADMINISTRADOR, "h", AHORA, id=1)
ANA = Usuario("ana@pj.bo", "Ana", Rol.USUARIO, "h", AHORA, id=2)


@pytest.fixture
def base():
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    fabrica = fabrica_sesiones(motor)
    with como_actor("admin@pj.bo"):
        usuarios = UsuariosPostgres(fabrica)
        ana = usuarios.guardar(Usuario("ana@pj.bo", "Ana", Rol.USUARIO, "h", AHORA))
        ProductosPostgres(fabrica).guardar(Producto("papa", "Papa"))
        usuarios.eliminar(ana.id)
    return VerAuditoria(AuditoriaPostgres(fabrica))


def test_junta_los_cambios_de_todas_las_tablas_con_quien_y_cuando(base):
    registros = base.recientes(ADMIN, limite=200)
    por_tabla = {(r.tabla, r.clave): r for r in registros}

    ana = por_tabla[("usuario", "ana@pj.bo")]
    assert ana.accion == "eliminado" and ana.auditoria.modificado_por == "admin@pj.bo"
    assert por_tabla[("producto", "papa")].auditoria.creado_por == "admin@pj.bo"
    # Los catálogos sincronizados al arrancar también están auditados.
    assert ("rol", "vendedor") in por_tabla and ("fuente", "siip_ipc") in por_tabla
    assert [r.ultimo_cambio for r in registros] == sorted((r.ultimo_cambio for r in registros), reverse=True)


def test_filtra_por_tabla_y_respeta_el_limite(base):
    solo = base.recientes(ADMIN, tabla="rol", limite=2)
    assert len(solo) == 2 and {r.tabla for r in solo} == {"rol"}


def test_una_tabla_inventada_no_llega_al_sql(base):
    with pytest.raises(DatoInvalido):
        base.recientes(ADMIN, tabla="usuario; DROP TABLE usuario")


def test_solo_quien_tiene_permiso_ve_la_auditoria(base):
    with pytest.raises(PermisoDenegado):
        base.recientes(ANA)


@pytest.fixture
def cliente():
    dependencias._cuentas.cache_clear()
    dependencias._repositorios.cache_clear()
    dependencias.caso_registrar_usuario().crear_como_sistema("admin@pj.bo", "Admin", "clave1234", Rol.ADMINISTRADOR)
    with TestClient(app) as c:
        yield c
    dependencias._cuentas.cache_clear()
    dependencias._repositorios.cache_clear()


def _token(cliente, correo="admin@pj.bo"):
    r = cliente.post("/api/v1/auth/ingresar", json={"correo": correo, "contrasena": "clave1234"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_api_auditoria_y_referencias(cliente):
    admin = _token(cliente)
    registros = cliente.get("/api/v1/admin/auditoria", headers=admin).json()
    assert registros[0]["tabla"] == "usuario" and registros[0]["accion"] == "creado"

    ref = cliente.get("/api/v1/admin/referencias", headers=admin).json()
    roles = {r["codigo"]: [p["codigo"] for p in r["permisos"]] for r in ref["roles"]}
    assert roles["usuario"] == ["reportar_precio", "gestionar_listas"]
    assert len(roles["administrador"]) == 7
    ipc = next(f for f in ref["fuentes"] if f["codigo"] == "siip_ipc")
    assert ipc["automatica"] is True and ipc["confianza_base"] == "alto"

    cliente.post("/api/v1/auth/registro", json={"correo": "ana@pj.bo", "nombre": "Ana", "contrasena": "clave1234"})
    ana = _token(cliente, "ana@pj.bo")
    assert cliente.get("/api/v1/admin/auditoria", headers=ana).status_code == 403
    assert cliente.get("/api/v1/admin/referencias", headers=ana).status_code == 403
    assert cliente.get("/api/v1/admin/auditoria?tabla=nada", headers=admin).status_code == 400
