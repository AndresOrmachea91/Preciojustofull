"""
C137 y decisión 26: el casero elige su mercado y su puesto (o registra su
distribuidora), le pone foto y maneja su inventario; el mapa muestra los
puestos de cada mercado con lo que tienen. Las cadenas salen del sistema.
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from src.aplicacion.casos_uso.precios.puestos_del_mercado import PuestosDelMercado
from src.aplicacion.casos_uso.vendedor.inventario import InventarioDelPuesto
from src.aplicacion.casos_uso.vendedor.mi_puesto import MiPuestoCasoUso
from src.aplicacion.casos_uso.vendedor.publicar_precio import PublicarPrecioPropio
from src.dominio.excepciones import CodigoYaExiste, DatoInvalido
from src.dominio.modelo import (
    ArticuloInventario, Disponibilidad, Fuente, Mercado, Presentacion, Puesto, Rol, TipoPuntoVenta, Usuario,
)
from src.dominio.modelo.foto import extension_de_imagen
from src.infraestructura.adaptadores.entrada.api.main import app
from src.infraestructura.adaptadores.salida.fotos.almacen_local import AlmacenFotosLocal
from src.infraestructura.adaptadores.salida.memoria.cuentas import UsuariosEnMemoria
from src.infraestructura.adaptadores.salida.memoria.puestos_y_ofertas import InventarioEnMemoria, PuestosEnMemoria
from src.infraestructura.adaptadores.salida.persistencia.puestos_y_ofertas import InventarioPostgres, PuestosPostgres
from src.infraestructura.adaptadores.salida.persistencia.sesion import crear_esquema, crear_motor, fabrica_sesiones

AHORA = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
JPG = b"\xff\xd8\xff\xe0" + b"0" * 200
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 200


@pytest.fixture
def mundo(repositorios, tmp_path):
    productos, mercados, observaciones = repositorios
    usuarios = UsuariosEnMemoria()
    rosa = usuarios.guardar(Usuario("rosa@pj.bo", "Rosa", Rol.VENDEDOR, "h", AHORA))
    puestos, inventario = PuestosEnMemoria(), InventarioEnMemoria()
    publicar = PublicarPrecioPropio(productos, mercados, observaciones, puestos)
    return {
        "usuarios": usuarios, "rosa": rosa, "mercados": mercados, "puestos": puestos, "inventario": inventario,
        "observaciones": observaciones, "fotos": AlmacenFotosLocal(tmp_path / "fotos"),
        "negocio": MiPuestoCasoUso(mercados, puestos, usuarios, AlmacenFotosLocal(tmp_path / "fotos")),
        "inventario_caso": InventarioDelPuesto(productos, puestos, inventario, publicar, ahora=lambda: AHORA),
        "mapa": PuestosDelMercado(mercados, productos, puestos, inventario),
    }


def _actual(mundo) -> Usuario:
    """El vendedor como lo lee la siguiente petición (el rol y el punto salen de la base)."""
    return mundo["usuarios"].obtener(mundo["rosa"].id)


# --- alcance: solo mercados, distribuidores y mayoristas -----------------------------

def test_las_cadenas_quedan_fuera_de_alcance():
    assert TipoPuntoVenta.MERCADO.en_alcance and TipoPuntoVenta.DISTRIBUIDOR.en_alcance
    assert not any(t.en_alcance for t in (TipoPuntoVenta.SUPERMERCADO, TipoPuntoVenta.MINIMARKET, TipoPuntoVenta.TIENDA))
    # Un distribuidor vende por caja o bulto: no compite con el precio de las familias.
    assert TipoPuntoVenta.DISTRIBUIDOR.nivel_precio.value == "mayorista"


def test_al_arrancar_las_cadenas_se_dan_de_baja_logica():
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    with motor.begin() as c:
        c.execute(text("INSERT INTO mercado (codigo, nombre, tipo, zona, macrodistrito, factor_mercado, creado_en, "
                       "creado_por, eliminado) VALUES ('ketal', 'Ketal', 'supermercado', '', '', 1, "
                       "CURRENT_TIMESTAMP, 'x', 0), ('lanza', 'Lanza', 'mercado', '', '', 1, CURRENT_TIMESTAMP, 'x', 0)"))
    crear_esquema(motor)
    with motor.begin() as c:
        filas = dict(c.execute(text("SELECT codigo, eliminado FROM mercado")).all())
    assert filas == {"ketal": 1, "lanza": 0}


# --- el puesto lo elige el casero ------------------------------------------------------

def test_el_casero_elige_su_mercado_y_queda_asignado(mundo):
    puesto = mundo["negocio"].guardar(mundo["rosa"], "14", "Verduras Rosa", ["hortaliza"], codigo_mercado="lanza")
    assert (puesto.codigo_mercado, puesto.numero) == ("lanza", "14")
    # Donde está su puesto es donde publica sus precios.
    assert _actual(mundo).codigo_punto_venta == "lanza"


def test_cambiarse_de_mercado_deja_el_puesto_viejo_sin_dueno(mundo):
    mundo["negocio"].guardar(mundo["rosa"], "14", "Rosa", [], codigo_mercado="lanza")
    mundo["negocio"].guardar(_actual(mundo), "3", "Rosa", [], codigo_mercado="rodriguez")
    assert mundo["puestos"].obtener_por_numero("lanza", "14").id_vendedor is None
    assert _actual(mundo).codigo_punto_venta == "rodriguez"


def test_un_puesto_no_va_en_una_distribuidora_ni_sin_mercado(mundo):
    mundo["mercados"].guardar(Mercado("dist", "Dist", TipoPuntoVenta.DISTRIBUIDOR, "Centro"))
    with pytest.raises(DatoInvalido, match="no un mercado"):
        mundo["negocio"].guardar(mundo["rosa"], "1", "X", [], codigo_mercado="dist")
    with pytest.raises(DatoInvalido, match="Elija en qué mercado"):
        mundo["negocio"].guardar(mundo["rosa"], "1", "X", [])
    with pytest.raises(DatoInvalido, match="reservado"):
        mundo["negocio"].guardar(mundo["rosa"], "local", "X", [], codigo_mercado="lanza")


def test_el_numero_ajeno_no_se_pisa(mundo):
    mundo["puestos"].guardar(Puesto("lanza", "14", "Otra", id_vendedor=99))
    with pytest.raises(CodigoYaExiste):
        mundo["negocio"].guardar(mundo["rosa"], "14", "Rosa", [], codigo_mercado="lanza")


# --- distribuidora -----------------------------------------------------------------------

def test_una_distribuidora_es_su_propio_punto_con_el_local_como_puesto(mundo):
    local = mundo["negocio"].registrar_distribuidora(
        mundo["rosa"], nombre="Distribuidora El Sol", zona="Villa Fátima", latitud=-16.48, longitud=-68.12,
        rubros=["abarrote"],
    )
    punto = mundo["mercados"].obtener(local.codigo_mercado)
    assert punto.tipo is TipoPuntoVenta.DISTRIBUIDOR and punto.nombre == "Distribuidora El Sol"
    assert local.es_local and local.titulo == "Distribuidora El Sol"
    assert _actual(mundo).codigo_punto_venta == punto.codigo
    # Editarla no crea otro punto.
    otra = mundo["negocio"].registrar_distribuidora(
        _actual(mundo), nombre="Distribuidora El Sol SRL", zona="Villa Fátima", latitud=-16.48, longitud=-68.12,
        rubros=[],
    )
    assert otra.codigo_mercado == punto.codigo and otra.id == local.id


def test_la_distribuidora_necesita_ubicacion_en_la_paz(mundo):
    with pytest.raises(DatoInvalido, match="Marque en el mapa"):
        mundo["negocio"].registrar_distribuidora(mundo["rosa"], nombre="X", zona="", latitud=None, longitud=None,
                                                 rubros=[])
    with pytest.raises(DatoInvalido, match="Marque en el mapa"):
        mundo["negocio"].registrar_distribuidora(mundo["rosa"], nombre="X", zona="", latitud=16.5, longitud=-68.1,
                                                 rubros=[])


# --- foto ----------------------------------------------------------------------------------

def test_solo_se_acepta_lo_que_de_verdad_es_una_imagen():
    assert extension_de_imagen(JPG) == "jpg"
    assert extension_de_imagen(PNG) == "png"
    assert extension_de_imagen(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "webp"
    with pytest.raises(DatoInvalido, match="JPG, PNG o WEBP"):
        extension_de_imagen(b"<script>alert(1)</script>")
    with pytest.raises(DatoInvalido, match="pesa más"):
        extension_de_imagen(b"\xff\xd8\xff" + b"0" * 3_000_000)


def test_la_foto_se_guarda_con_nombre_aleatorio_y_no_se_sirve_cualquier_ruta(mundo):
    with pytest.raises(DatoInvalido, match="Primero registre su puesto"):
        mundo["negocio"].poner_foto(mundo["rosa"], JPG)
    mundo["negocio"].guardar(mundo["rosa"], "14", "Rosa", [], codigo_mercado="lanza")
    puesto = mundo["negocio"].poner_foto(_actual(mundo), JPG)
    assert puesto.foto and puesto.foto.endswith(".jpg") and "14" not in puesto.foto
    assert mundo["fotos"].ruta(puesto.foto) is not None
    assert mundo["fotos"].ruta("../../.env") is None
    # Volver a guardar los datos del puesto no le quita la foto.
    assert mundo["negocio"].guardar(_actual(mundo), "14", "Rosa 2", [], codigo_mercado="lanza").foto == puesto.foto


# --- inventario ----------------------------------------------------------------------------

def _vendedora_con_puesto(mundo) -> Usuario:
    mundo["negocio"].guardar(mundo["rosa"], "14", "Rosa", ["hortaliza"], codigo_mercado="lanza")
    return _actual(mundo)


def _declarados(mundo, producto: str):
    return [o for o in mundo["observaciones"].buscar(producto) if o.fuente is Fuente.VENDEDOR]


def test_el_precio_nuevo_del_inventario_se_publica_como_declarado(mundo):
    rosa = _vendedora_con_puesto(mundo)
    caso = mundo["inventario_caso"]
    caso.guardar(rosa, "tomate", 12, Presentacion.KILO)
    declarados = _declarados(mundo, "tomate")
    assert len(declarados) == 1 and declarados[0].codigo_mercado == "lanza" and declarados[0].puesto == "14"
    # Solo cambia la disponibilidad: no es un precio nuevo.
    caso.guardar(rosa, "tomate", 12, Presentacion.KILO, Disponibilidad.POCO)
    assert len(_declarados(mundo, "tomate")) == 1
    assert [a.disponibilidad for a in caso.ver(rosa)] == [Disponibilidad.POCO]


def test_lo_agotado_no_publica_precio_y_quitar_lo_saca_del_inventario(mundo):
    rosa = _vendedora_con_puesto(mundo)
    caso = mundo["inventario_caso"]
    caso.guardar(rosa, "papa", 80, Presentacion.ARROBA, Disponibilidad.AGOTADO)
    assert _declarados(mundo, "papa") == []
    caso.quitar(rosa, "papa")
    assert caso.ver(rosa) == []


def test_el_inventario_pide_puesto_y_presentacion_valida(mundo):
    with pytest.raises(DatoInvalido, match="Primero registre su puesto"):
        mundo["inventario_caso"].ver(mundo["rosa"])
    rosa = _vendedora_con_puesto(mundo)
    with pytest.raises(DatoInvalido, match="error de tipeo"):
        mundo["inventario_caso"].guardar(rosa, "tomate", 120_000, Presentacion.KILO)


# --- la ventana del mapa -----------------------------------------------------------------

def test_en_el_mapa_primero_los_puestos_que_tienen_el_producto(mundo):
    p1 = mundo["puestos"].guardar(Puesto("lanza", "1", "Carnes", id_vendedor=50))
    p2 = mundo["puestos"].guardar(Puesto("lanza", "2", "Verduras", id_vendedor=51))
    inv = mundo["inventario"]
    inv.guardar(ArticuloInventario(p1.id, "papa", 80, Presentacion.ARROBA))
    inv.guardar(ArticuloInventario(p2.id, "papa", 78, Presentacion.ARROBA, Disponibilidad.AGOTADO))
    inv.guardar(ArticuloInventario(p2.id, "tomate", 12, Presentacion.KILO))

    r = mundo["mapa"].ejecutar("lanza", producto="tomate")
    assert [x.puesto.numero for x in r.puestos] == ["2", "1"]
    # De cada puesto, primero el producto buscado; lo agotado al final.
    assert [v.producto.codigo for v in r.puestos[0].articulos] == ["tomate", "papa"]

    recortado = mundo["mapa"].ejecutar("lanza", articulos_por_puesto=1)
    assert all(len(x.articulos) <= 1 for x in recortado.puestos)
    assert {x.puesto.numero: x.total for x in recortado.puestos} == {"1": 1, "2": 2}


# --- persistencia y API ----------------------------------------------------------------------

def test_inventario_y_foto_se_guardan_en_la_base():
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    fabrica = fabrica_sesiones(motor)
    puestos, inventario = PuestosPostgres(fabrica), InventarioPostgres(fabrica)
    p = puestos.guardar(Puesto("rodriguez", "10", "Carnes", id_vendedor=7, foto="a" * 32 + ".jpg"))
    assert puestos.del_vendedor(7).foto == "a" * 32 + ".jpg"
    a = inventario.guardar(ArticuloInventario(p.id, "carne", 45, Presentacion.KILO, actualizado_en=AHORA))
    b = inventario.guardar(ArticuloInventario(p.id, "carne", 47, Presentacion.KILO, Disponibilidad.POCO,
                                              actualizado_en=AHORA))
    assert a.id == b.id
    assert [(x.monto, x.disponibilidad) for x in inventario.del_puesto(p.id)] == [(47, Disponibilidad.POCO)]
    inventario.quitar(p.id, "carne")
    assert inventario.de_puestos([p.id]) == {}
    # Se puede volver a agregar después de quitarlo (único solo entre los vigentes).
    inventario.guardar(ArticuloInventario(p.id, "carne", 50, Presentacion.KILO, actualizado_en=AHORA))
    assert len(inventario.del_puesto(p.id)) == 1


def test_la_api_no_sirve_rutas_raras_como_foto():
    cliente = TestClient(app)
    assert cliente.get("/api/v1/fotos/..%2F..%2F.env").status_code == 404
    assert cliente.get("/api/v1/fotos/noexiste.jpg").status_code == 404


def test_el_casero_se_registra_solo_como_vendedor_pero_nunca_como_administrador():
    cliente = TestClient(app)
    r = cliente.post("/api/v1/auth/registro", json={
        "correo": "casera.nueva@correo.bo", "nombre": "Casera", "contrasena": "puesto1234", "quiere_vender": True})
    assert r.status_code == 201 and r.json()["rol"] == "vendedor"
    r = cliente.post("/api/v1/auth/registro", json={
        "correo": "vecina.nueva@correo.bo", "nombre": "Vecina", "contrasena": "vecina1234"})
    assert r.status_code == 201 and r.json()["rol"] == "usuario"
    # Un campo "rol" en el registro público no sirve para nada.
    r = cliente.post("/api/v1/auth/registro", json={
        "correo": "pillo@correo.bo", "nombre": "X", "contrasena": "pillo12345", "rol": "administrador"})
    assert r.status_code == 201 and r.json()["rol"] == "usuario"
