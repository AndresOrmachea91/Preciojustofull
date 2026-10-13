"""
El borde HTTP de cuentas y reportes: códigos de estado, que el hash nunca
salga por la API y que cada ruta protegida exija sesión y permiso.
"""
import pytest
from fastapi.testclient import TestClient

from src.dominio.modelo import Rol
from src.infraestructura.adaptadores.entrada.api import dependencias
from src.infraestructura.adaptadores.entrada.api.main import app

API = "/api/v1"


@pytest.fixture
def cliente():
    # Repositorios en memoria nuevos en cada prueba: sin estado compartido.
    dependencias._cuentas.cache_clear()
    dependencias._repositorios.cache_clear()
    dependencias.caso_registrar_usuario().crear_como_sistema(
        "admin@pj.bo", "Admin", "clave1234", Rol.ADMINISTRADOR,
    )
    with TestClient(app) as c:
        yield c
    dependencias._cuentas.cache_clear()
    dependencias._repositorios.cache_clear()


def _token(cliente, correo="admin@pj.bo", contrasena="clave1234"):
    r = cliente.post(f"{API}/auth/ingresar", json={"correo": correo, "contrasena": contrasena})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _registrar(cliente, correo="ana@pj.bo"):
    r = cliente.post(f"{API}/auth/registro", json={"correo": correo, "nombre": "Ana", "contrasena": "clave1234"})
    assert r.status_code == 201, r.text
    return r.json()


def test_registro_ingreso_y_yo(cliente):
    creado = _registrar(cliente)
    assert creado["rol"] == "usuario"
    assert "hash_contrasena" not in creado

    r = cliente.get(f"{API}/auth/yo", headers=_token(cliente, "ana@pj.bo"))
    assert r.status_code == 200
    assert r.json()["correo"] == "ana@pj.bo"
    assert r.json()["permisos"] == ["gestionar_listas", "reportar_precio"]


def test_errores_de_cuenta_con_su_codigo(cliente):
    _registrar(cliente)
    assert cliente.post(f"{API}/auth/registro", json={"correo": "ana@pj.bo", "contrasena": "clave1234"}).status_code == 409
    assert cliente.post(f"{API}/auth/registro", json={"correo": "x@pj.bo", "contrasena": "corta"}).status_code == 400
    assert cliente.post(f"{API}/auth/ingresar", json={"correo": "ana@pj.bo", "contrasena": "mala1234"}).status_code == 401


@pytest.mark.parametrize("metodo,ruta", [
    ("get", "/auth/yo"), ("get", "/admin/usuarios"), ("post", "/admin/usuarios"),
    ("patch", "/admin/usuarios/1"), ("get", "/admin/reportes"), ("post", "/reportes"),
    ("post", "/admin/reportes/1/aprobar"),
])
def test_las_rutas_protegidas_exigen_sesion(cliente, metodo, ruta):
    r = getattr(cliente, metodo)(f"{API}{ruta}", headers={"Authorization": "Bearer falso"})
    assert r.status_code == 401
    r = getattr(cliente, metodo)(f"{API}{ruta}")
    assert r.status_code == 401


def test_un_usuario_comun_no_administra(cliente):
    _registrar(cliente)
    ana = _token(cliente, "ana@pj.bo")
    assert cliente.get(f"{API}/admin/usuarios", headers=ana).status_code == 403
    assert cliente.get(f"{API}/admin/reportes", headers=ana).status_code == 403


def test_el_administrador_gestiona_cuentas(cliente):
    admin = _token(cliente)
    r = cliente.post(f"{API}/admin/usuarios", headers=admin,
                     json={"correo": "vend@pj.bo", "nombre": "Vend", "contrasena": "clave1234", "rol": "vendedor"})
    assert r.status_code == 201
    id_vend = r.json()["id"]

    r = cliente.patch(f"{API}/admin/usuarios/{id_vend}", headers=admin, json={"activo": False})
    assert r.status_code == 200 and r.json()["activo"] is False and r.json()["permisos"] == []

    assert cliente.patch(f"{API}/admin/usuarios/9999", headers=admin, json={"activo": False}).status_code == 404
    lista = cliente.get(f"{API}/admin/usuarios", headers=admin).json()
    assert [u["correo"] for u in lista] == ["admin@pj.bo", "vend@pj.bo"]
    assert all("hash_contrasena" not in u for u in lista)


def test_el_ultimo_administrador_no_se_puede_quitar(cliente):
    admin = _token(cliente)
    yo = cliente.get(f"{API}/auth/yo", headers=admin).json()
    r = cliente.patch(f"{API}/admin/usuarios/{yo['id']}", headers=admin, json={"rol": "usuario"})
    assert r.status_code == 409


def test_flujo_de_reporte_hasta_la_aprobacion(cliente):
    _registrar(cliente)
    ana, admin = _token(cliente, "ana@pj.bo"), _token(cliente)

    r = cliente.post(f"{API}/reportes", headers=ana,
                     json={"codigo_producto": "tomate", "codigo_mercado": "rodriguez", "monto": 9.5, "unidad": "KILO"})
    assert r.status_code == 201

    pendientes = cliente.get(f"{API}/admin/reportes", headers=admin).json()
    assert len(pendientes) == 1 and pendientes[0]["estado"] == "pendiente"
    id_rep = pendientes[0]["id"]

    assert cliente.post(f"{API}/admin/reportes/{id_rep}/aprobar", headers=admin).json()["estado"] == "aprobado"
    assert cliente.post(f"{API}/admin/reportes/{id_rep}/aprobar", headers=admin).status_code == 409
    assert cliente.get(f"{API}/admin/reportes", headers=admin).json() == []
    assert len(cliente.get(f"{API}/admin/reportes?estado=todos", headers=admin).json()) == 1


def test_reporte_de_producto_inexistente_es_404(cliente):
    r = cliente.post(f"{API}/reportes", headers=_token(cliente),
                     json={"codigo_producto": "caviar", "codigo_mercado": "rodriguez", "monto": 1, "unidad": "KILO"})
    assert r.status_code == 404


def test_eliminar_cuenta_es_logico_y_se_lista_aparte(cliente):
    admin = _token(cliente)
    ana = _registrar(cliente)
    _token(cliente, "ana@pj.bo")

    assert cliente.delete(f"{API}/admin/usuarios/{ana['id']}", headers=admin).status_code == 204
    # Ya no ingresa ni aparece en el listado normal...
    r = cliente.post(f"{API}/auth/ingresar", json={"correo": "ana@pj.bo", "contrasena": "clave1234"})
    assert r.status_code == 401
    vigentes = cliente.get(f"{API}/admin/usuarios", headers=admin).json()
    assert [u["correo"] for u in vigentes] == ["admin@pj.bo"]
    assert vigentes[0]["auditoria"]["eliminado"] is False
    # ...pero sigue, marcada, si se piden también los eliminados.
    todos = cliente.get(f"{API}/admin/usuarios?incluir_eliminados=true", headers=admin).json()
    assert [(u["correo"], u["auditoria"]["eliminado"]) for u in todos] == [
        ("admin@pj.bo", False), ("ana@pj.bo", True),
    ]
    assert cliente.delete(f"{API}/admin/usuarios/{ana['id']}", headers=admin).status_code == 404


def test_no_se_elimina_a_si_mismo_ni_otro_lo_hace_sin_permiso(cliente):
    admin = _token(cliente)
    yo = cliente.get(f"{API}/auth/yo", headers=admin).json()
    assert "auditoria" not in yo  # el DTO propio no lleva auditoría
    assert cliente.delete(f"{API}/admin/usuarios/{yo['id']}", headers=admin).status_code == 409
    _registrar(cliente)
    ana = _token(cliente, "ana@pj.bo")
    assert cliente.delete(f"{API}/admin/usuarios/{yo['id']}", headers=ana).status_code == 403
