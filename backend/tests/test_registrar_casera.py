"""
Registrar a una casera con puesto fijo desde el mercado (C144): el
administrador la da de alta con su celular, ella entra con ese celular y la
clave temporal, y su puesto ya aparece en el mapa. Si algo no cuadra, no
queda una cuenta suelta.
"""
import pytest
from fastapi.testclient import TestClient

from src.dominio.excepciones import DatoInvalido
from src.dominio.modelo import Rol
from src.dominio.modelo.usuario import celular_boliviano, identificador_de_ingreso
from src.infraestructura.adaptadores.entrada.api import dependencias
from src.infraestructura.adaptadores.entrada.api.cache_fichas import olvidar
from src.infraestructura.adaptadores.entrada.api.main import app
from src.aplicacion.casos_uso.administracion.registrar_casera import clave_temporal
from src.dominio.modelo.usuario import validar_contrasena

API = "/api/v1"
CACHES = (dependencias._cuentas, dependencias._repositorios, dependencias._puestos_y_ofertas, dependencias._inventario)


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    for f in CACHES:
        f.cache_clear()
    olvidar()
    monkeypatch.setattr(dependencias.config, "fotos_dir", str(tmp_path / "fotos"))
    dependencias.caso_registrar_usuario().crear_como_sistema("admin@pj.bo", "Admin", "clave1234", Rol.ADMINISTRADOR)
    with TestClient(app) as c:
        yield c
    for f in CACHES:
        f.cache_clear()
    olvidar()


def _admin(cliente):
    r = cliente.post(f"{API}/auth/ingresar", json={"correo": "admin@pj.bo", "contrasena": "clave1234"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


CASERA = {"nombre": "Doña Rosa", "celular": "712 34 567", "codigo_mercado": "lanza", "numero": "b-12",
          "nombre_puesto": "Verduras Rosa", "rubros": ["hortaliza"], "referencia": "Segundo piso"}


def test_la_casera_entra_con_su_celular_y_su_puesto_aparece(cliente):
    r = cliente.post(f"{API}/admin/usuarios/caseras", headers=_admin(cliente), json=CASERA)
    assert r.status_code == 201, r.text
    datos = r.json()
    assert datos["celular"] == "71234567" and datos["numero"] == "B-12"

    # Entra con el celular, aunque lo escriba con el prefijo del país.
    r = cliente.post(f"{API}/auth/ingresar", json={"correo": "+591 71234567", "contrasena": datos["clave_temporal"]})
    assert r.status_code == 200, r.text
    assert r.json()["usuario"]["rol"] == "vendedor"

    puestos = cliente.get(f"{API}/mercados/lanza/puestos").json()["puestos"]
    assert any(p["puesto"]["numero"] == "B-12" and p["puesto"]["nombre"] == "Verduras Rosa" for p in puestos)


def test_un_puesto_con_duena_no_se_pisa_y_no_queda_cuenta_suelta(cliente):
    admin = _admin(cliente)
    assert cliente.post(f"{API}/admin/usuarios/caseras", headers=admin, json=CASERA).status_code == 201
    otra = {**CASERA, "nombre": "Doña Juana", "celular": "76543210"}
    r = cliente.post(f"{API}/admin/usuarios/caseras", headers=admin, json=otra)
    assert r.status_code in (400, 409), r.text
    # La segunda casera no quedó creada: con el puesto libre se la puede registrar después.
    r = cliente.post(f"{API}/admin/usuarios/caseras", headers=admin, json={**otra, "numero": "B-13"})
    assert r.status_code == 201, r.text


def test_solo_el_administrador_registra_caseras(cliente):
    r = cliente.post(f"{API}/admin/usuarios/caseras", json=CASERA)
    assert r.status_code == 401


@pytest.mark.parametrize("texto, esperado", [
    ("71234567", "71234567"), ("+591 712-34567", "71234567"), ("59161234567", "61234567"),
    ("51234567", None), ("7123456", None), ("rosa@correo.bo", None),
])
def test_reconoce_un_celular_de_bolivia(texto, esperado):
    assert celular_boliviano(texto) == esperado


def test_el_correo_sigue_funcionando_para_entrar():
    assert identificador_de_ingreso("rosa@correo.bo") == "rosa@correo.bo"
    assert identificador_de_ingreso("71234567") == "71234567@caseras.preciojusto.bo"


def test_la_clave_temporal_cumple_las_reglas_de_contrasena():
    for _ in range(50):
        validar_contrasena(clave_temporal())


def test_un_celular_invalido_se_rechaza():
    from src.dominio.modelo.usuario import correo_de_celular
    with pytest.raises(DatoInvalido):
        correo_de_celular("123")
