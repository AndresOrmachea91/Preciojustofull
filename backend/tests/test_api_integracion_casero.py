"""
Prueba de integración de la API (A4240): el recorrido completo del casero y
del comprador por HTTP, con los mismos adaptadores que en producción salvo
la base (en memoria).

La casera se registra sola, elige su mercado y su puesto, sube la foto,
carga su inventario; el comprador abre la ventana del mercado en el mapa y
ve el puesto con su foto y sus precios; la foto se sirve.
"""
import base64

import pytest
from fastapi.testclient import TestClient

from src.infraestructura.adaptadores.entrada.api import dependencias
from src.infraestructura.adaptadores.entrada.api.cache_fichas import olvidar
from src.infraestructura.adaptadores.entrada.api.main import app

API = "/api/v1"
JPG = b"\xff\xd8\xff\xe0" + b"0" * 500


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    # Estado nuevo en cada prueba, y las fotos en una carpeta temporal.
    for f in (dependencias._cuentas, dependencias._repositorios, dependencias._puestos_y_ofertas,
              dependencias._inventario):
        f.cache_clear()
    olvidar()
    monkeypatch.setattr(dependencias.config, "fotos_dir", str(tmp_path / "fotos"))
    with TestClient(app) as c:
        yield c
    for f in (dependencias._cuentas, dependencias._repositorios, dependencias._puestos_y_ofertas,
              dependencias._inventario):
        f.cache_clear()
    olvidar()


def _casera(cliente) -> dict:
    r = cliente.post(f"{API}/auth/registro", json={
        "correo": "rosa@correo.bo", "nombre": "Rosa", "contrasena": "puesto1234", "quiere_vender": True})
    assert r.status_code == 201, r.text
    r = cliente.post(f"{API}/auth/ingresar", json={"correo": "rosa@correo.bo", "contrasena": "puesto1234"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_el_recorrido_completo_del_casero_y_del_comprador(cliente):
    sesion = _casera(cliente)

    # Sin puesto todavía: el inventario lo pide.
    assert cliente.get(f"{API}/vendedor/inventario", headers=sesion).status_code == 400

    r = cliente.put(f"{API}/vendedor/puesto", headers=sesion, json={
        "numero": "14", "nombre": "Verduras Rosa", "rubros": ["hortaliza"], "codigo_mercado": "lanza"})
    assert r.status_code == 200, r.text
    assert r.json()["codigo_mercado"] == "lanza" and r.json()["foto"] is None

    imagen = "data:image/jpeg;base64," + base64.b64encode(JPG).decode()
    r = cliente.put(f"{API}/vendedor/puesto/foto", headers=sesion, json={"imagen": imagen})
    assert r.status_code == 200, r.text
    foto = r.json()["foto"]
    assert foto.startswith("/api/v1/fotos/") and foto.endswith(".jpg")

    for producto, monto, presentacion, disponibilidad in (
        ("tomate", 12, "kilo", "hay"), ("papa", 80, "arroba", "poco"), ("arroz", 8.5, "kilo", "agotado"),
    ):
        r = cliente.put(f"{API}/vendedor/inventario", headers=sesion, json={
            "codigo_producto": producto, "monto": monto, "presentacion": presentacion,
            "disponibilidad": disponibilidad})
        assert r.status_code == 200, r.text
    inventario = cliente.get(f"{API}/vendedor/inventario", headers=sesion).json()
    assert {a["codigo_producto"]: a["disponibilidad"] for a in inventario} == {
        "tomate": "hay", "papa": "poco", "arroz": "agotado"}

    # El comprador, sin sesión, toca el Lanza en el mapa buscando papa.
    r = cliente.get(f"{API}/mercados/lanza/puestos", params={"producto": "papa", "articulos": 2})
    assert r.status_code == 200, r.text
    puesto = r.json()["puestos"][0]
    assert puesto["puesto"]["numero"] == "14" and puesto["puesto"]["foto"] == foto
    assert [a["codigo_producto"] for a in puesto["articulos"]] == ["papa", "tomate"]
    assert puesto["total"] == 3

    # La foto se sirve, con caché larga (el nombre cambia si cambia la foto).
    r = cliente.get(foto)
    assert r.status_code == 200 and r.content == JPG
    assert "immutable" in r.headers["cache-control"]

    # El precio del inventario se publicó como declarado por el vendedor.
    publicados = cliente.get(f"{API}/vendedor/precios", headers=sesion).json()
    assert {p["codigo_producto"] for p in publicados} >= {"tomate", "papa"}
    assert "arroz" not in {p["codigo_producto"] for p in publicados}   # agotado: no es un precio nuevo

    assert cliente.delete(f"{API}/vendedor/inventario/arroz", headers=sesion).status_code == 204
    assert len(cliente.get(f"{API}/vendedor/inventario", headers=sesion).json()) == 2


def test_una_distribuidora_aparece_como_punto_propio(cliente):
    sesion = _casera(cliente)
    r = cliente.put(f"{API}/vendedor/distribuidora", headers=sesion, json={
        "nombre": "Distribuidora El Sol", "zona": "Villa Fátima", "latitud": -16.48, "longitud": -68.12,
        "rubros": ["abarrote"]})
    assert r.status_code == 200, r.text
    assert r.json()["es_local"] is True
    mercados = {m["codigo"]: m for m in cliente.get(f"{API}/mercados").json()}
    punto = mercados[r.json()["codigo_mercado"]]
    assert punto["tipo"] == "distribuidor" and punto["nivel_precio"] == "mayorista"


def test_la_foto_que_no_es_imagen_se_rechaza_y_las_rutas_piden_sesion(cliente):
    sesion = _casera(cliente)
    cliente.put(f"{API}/vendedor/puesto", headers=sesion, json={"numero": "3", "codigo_mercado": "lanza"})
    falsa = "data:image/jpeg;base64," + base64.b64encode(b"<html>no soy foto</html>").decode()
    r = cliente.put(f"{API}/vendedor/puesto/foto", headers=sesion, json={"imagen": falsa})
    assert r.status_code == 400 and "JPG, PNG o WEBP" in r.text
    assert cliente.get(f"{API}/vendedor/inventario").status_code == 401
    for ruta in ("/vendedor/distribuidora", "/vendedor/puesto/foto", "/vendedor/inventario"):
        assert cliente.put(f"{API}{ruta}", json={}).status_code == 401
