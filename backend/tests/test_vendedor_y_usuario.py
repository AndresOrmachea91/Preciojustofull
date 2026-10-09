"""
Lo que hacen el vendedor (publicar los precios de su puesto) y el usuario
(seguir sus reportes y armar listas de compras para cotizarlas).
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from src.aplicacion.casos_uso.precios.calcular_canasta import CalcularCanastaCasoUso
from src.aplicacion.casos_uso.usuario.listas_compras import GestionarListas, RenglonPedido
from src.aplicacion.casos_uso.usuario.mis_reportes import MisReportes
from src.aplicacion.casos_uso.usuario.reportar_precio import RegistrarReporteCiudadano
from src.aplicacion.casos_uso.vendedor.publicar_precio import MisPrecios, PublicarPrecioPropio
from src.dominio.excepciones import (
    DatoInvalido, ListaNoEncontrada, PermisoDenegado, PresentacionInvalida, SinPuntoVenta,
)
from src.dominio.modelo import Fuente, ItemLista, ListaCompras, Presentacion, Rol, Usuario
from src.dominio.servicio.motor_fusion import MotorFusion
from src.infraestructura.adaptadores.entrada.api import dependencias
from src.infraestructura.adaptadores.entrada.api.main import app
from src.infraestructura.adaptadores.salida.memoria.cuentas import ReportesEnMemoria
from src.infraestructura.adaptadores.salida.memoria.listas import ListasEnMemoria
from src.infraestructura.adaptadores.salida.persistencia.listas import ListasPostgres
from src.infraestructura.adaptadores.salida.persistencia.sesion import (
    crear_esquema, crear_motor, fabrica_sesiones,
)

AHORA = datetime(2026, 10, 9, tzinfo=timezone.utc)
VENDEDORA = Usuario("rosa@pj.bo", "Rosa", Rol.VENDEDOR, "h", AHORA, codigo_punto_venta="rodriguez", id=7)
SIN_PUESTO = Usuario("juan@pj.bo", "Juan", Rol.VENDEDOR, "h", AHORA, id=8)
ANA = Usuario("ana@pj.bo", "Ana", Rol.USUARIO, "h", AHORA, id=2)
LUIS = Usuario("luis@pj.bo", "Luis", Rol.USUARIO, "h", AHORA, id=3)


# --- vendedor ------------------------------------------------------------------

def test_el_vendedor_publica_en_su_puesto_marcado_como_declarado(repositorios):
    productos, mercados, observaciones = repositorios
    PublicarPrecioPropio(productos, mercados, observaciones).ejecutar(
        VENDEDORA, "papa", 80.0, Presentacion.ARROBA,
    )
    propias = [o for o in observaciones.buscar("papa", "rodriguez") if o.fuente is Fuente.VENDEDOR]
    assert len(propias) == 1
    assert propias[0].evidencia == "vendedor:7"
    assert propias[0].precio_canonico() == pytest.approx(80.0 / 11.5)   # por kilo


def test_mis_precios_muestra_lo_ultimo_de_cada_producto(repositorios):
    productos, mercados, observaciones = repositorios
    publicar = PublicarPrecioPropio(productos, mercados, observaciones)
    publicar.ejecutar(VENDEDORA, "papa", 80.0, Presentacion.ARROBA)
    publicar.ejecutar(VENDEDORA, "papa", 3.5, Presentacion.LIBRA)
    publicar.ejecutar(VENDEDORA, "tomate", 7.0, Presentacion.KILO)

    precios = MisPrecios(productos, mercados, observaciones).ejecutar(VENDEDORA)
    assert [(p.producto.codigo, p.presentacion, p.monto) for p in precios] == [
        ("papa", "libra", 3.5), ("tomate", "kilo", 7.0),
    ]


def test_sin_puesto_no_hay_donde_publicar(repositorios):
    productos, mercados, observaciones = repositorios
    with pytest.raises(SinPuntoVenta):
        PublicarPrecioPropio(productos, mercados, observaciones).ejecutar(
            SIN_PUESTO, "papa", 80.0, Presentacion.ARROBA,
        )


def test_el_vendedor_solo_publica_en_presentaciones_del_producto(repositorios):
    productos, mercados, observaciones = repositorios
    with pytest.raises(PresentacionInvalida):
        PublicarPrecioPropio(productos, mercados, observaciones).ejecutar(
            VENDEDORA, "papa", 10.0, Presentacion.DOCENA,
        )


def test_un_usuario_comun_no_publica_como_vendedor(repositorios):
    productos, mercados, observaciones = repositorios
    with pytest.raises(PermisoDenegado):
        PublicarPrecioPropio(productos, mercados, observaciones).ejecutar(ANA, "papa", 80.0, Presentacion.ARROBA)


# --- mis reportes ---------------------------------------------------------------

def test_mis_reportes_solo_trae_los_propios_del_mas_nuevo_al_mas_viejo(repositorios):
    productos, mercados, _ = repositorios
    reportes = ReportesEnMemoria()
    reportar = RegistrarReporteCiudadano(productos, mercados, reportes)
    reportar.ejecutar(ANA, "tomate", "rodriguez", 9.0, "KILO")
    reportar.ejecutar(LUIS, "papa", "lanza", 5.0, "KILO")
    reportar.ejecutar(ANA, "papa", "rodriguez", 6.0, "KILO")

    mios = MisReportes(reportes).ejecutar(ANA)
    assert [r.codigo_producto for r in mios] == ["papa", "tomate"]


# --- listas de compras ----------------------------------------------------------

@pytest.fixture
def listas(repositorios):
    productos, mercados, observaciones = repositorios
    canasta = CalcularCanastaCasoUso(mercados, observaciones, MotorFusion())
    return GestionarListas(ListasEnMemoria(), productos, canasta)


def test_una_lista_guarda_cantidades_en_la_presentacion_de_la_persona(listas):
    lista = listas.crear(ANA, "Compra del mes", [
        RenglonPedido("papa", 2, Presentacion.ARROBA),
        RenglonPedido("arroz", 5, Presentacion.KILO),
    ])
    assert lista.items[0].en_unidad_base() == pytest.approx(23.0)
    assert [l.nombre for l in listas.listar(ANA)] == ["Compra del mes"]
    assert listas.listar(LUIS) == []


def test_la_lista_de_otro_no_se_ve_ni_se_toca(listas):
    lista = listas.crear(ANA, "Mía", [RenglonPedido("papa", 1, Presentacion.KILO)])
    with pytest.raises(ListaNoEncontrada):
        listas.actualizar(LUIS, lista.id, "Robada", [])
    with pytest.raises(ListaNoEncontrada):
        listas.cotizar(LUIS, lista.id)
    with pytest.raises(ListaNoEncontrada):
        listas.eliminar(LUIS, lista.id)


@pytest.mark.parametrize("renglones,error", [
    ([RenglonPedido("papa", 1, Presentacion.DOCENA)], PresentacionInvalida),
    ([RenglonPedido("papa", 0, Presentacion.KILO)], DatoInvalido),
    ([RenglonPedido("papa", 1, Presentacion.KILO), RenglonPedido("papa", 2, Presentacion.KILO)], DatoInvalido),
])
def test_una_lista_valida_sus_renglones(listas, renglones, error):
    with pytest.raises(error):
        listas.crear(ANA, "Mal", renglones)


def test_cotizar_usa_la_cantidad_en_unidad_base(listas):
    por_kilo = listas.crear(ANA, "Kilo", [RenglonPedido("papa", 1, Presentacion.KILO)])
    por_arroba = listas.crear(ANA, "Arroba", [RenglonPedido("papa", 1, Presentacion.ARROBA)])
    kilo = {c.codigo_mercado: c.costo_total for c in listas.cotizar(ANA, por_kilo.id)}
    arroba = {c.codigo_mercado: c.costo_total for c in listas.cotizar(ANA, por_arroba.id)}
    assert kilo, "la papa tiene precio en algún mercado"
    for mercado, total in kilo.items():
        assert arroba[mercado] == pytest.approx(total * 11.5, abs=0.06)   # la canasta redondea a centavos


def test_un_vendedor_tambien_arma_listas(listas):
    assert listas.crear(VENDEDORA, "Para el puesto", []).nombre == "Para el puesto"


# --- contrato de listas: memoria y SQLAlchemy ------------------------------------

@pytest.fixture(params=["memoria", "sqlalchemy"])
def repo_listas(request):
    if request.param == "memoria":
        return ListasEnMemoria()
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    return ListasPostgres(fabrica_sesiones(motor))


def test_contrato_listas(repo_listas):
    lista = repo_listas.guardar(ListaCompras(2, "Compra", (
        ItemLista("papa", 2, Presentacion.ARROBA), ItemLista("arroz", 1, Presentacion.QUINTAL),
    )))
    assert lista.id is not None and lista.creado_en is not None

    editada = repo_listas.guardar(lista.con("Compra grande", (
        ItemLista("arroz", 2, Presentacion.QUINTAL), ItemLista("tomate", 3, Presentacion.KILO),
    )))
    leida = repo_listas.obtener(lista.id)
    assert leida == editada
    assert leida.nombre == "Compra grande"
    assert [(i.codigo_producto, i.cantidad) for i in leida.items] == [("arroz", 2), ("tomate", 3)]

    assert [l.id for l in repo_listas.listar_de(2)] == [lista.id]
    assert repo_listas.listar_de(99) == []
    repo_listas.eliminar(lista.id)
    assert repo_listas.obtener(lista.id) is None and repo_listas.listar_de(2) == []


# --- HTTP -------------------------------------------------------------------------

@pytest.fixture
def cliente():
    for cache in (dependencias._cuentas, dependencias._repositorios, dependencias._listas):
        cache.cache_clear()
    alta = dependencias.caso_registrar_usuario()
    alta.crear_como_sistema("ana@pj.bo", "Ana", "clave1234", Rol.USUARIO)
    vendedora = alta.crear_como_sistema("rosa@pj.bo", "Rosa", "clave1234", Rol.VENDEDOR)
    usuarios = dependencias._cuentas()[0]
    usuarios.guardar(vendedora.con_punto_venta("rodriguez"))
    with TestClient(app) as c:
        yield c
    for cache in (dependencias._cuentas, dependencias._repositorios, dependencias._listas):
        cache.cache_clear()


def _token(cliente, correo):
    r = cliente.post("/api/v1/auth/ingresar", json={"correo": correo, "contrasena": "clave1234"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_api_vendedor(cliente):
    rosa = _token(cliente, "rosa@pj.bo")
    r = cliente.post("/api/v1/vendedor/precios", headers=rosa,
                     json={"codigo_producto": "papa", "monto": 80, "presentacion": "arroba"})
    assert r.status_code == 201
    precios = cliente.get("/api/v1/vendedor/precios", headers=rosa).json()
    assert precios[0]["presentacion"] == "arroba"
    assert precios[0]["precio_por_unidad_base"] == pytest.approx(80 / 11.5, rel=1e-3)
    assert cliente.get("/api/v1/vendedor/precios", headers=_token(cliente, "ana@pj.bo")).status_code == 403


def test_api_mis_reportes_y_listas(cliente):
    ana = _token(cliente, "ana@pj.bo")
    cliente.post("/api/v1/reportes", headers=ana,
                 json={"codigo_producto": "tomate", "codigo_mercado": "rodriguez", "monto": 9, "unidad": "KILO"})
    mios = cliente.get("/api/v1/reportes/mios", headers=ana).json()
    assert [(r["codigo_producto"], r["estado"]) for r in mios] == [("tomate", "pendiente")]

    r = cliente.post("/api/v1/listas", headers=ana, json={
        "nombre": "Compra del mes",
        "items": [{"codigo_producto": "papa", "cantidad": 2, "presentacion": "arroba"}],
    })
    assert r.status_code == 201
    id_lista = r.json()["id"]
    cotizacion = cliente.get(f"/api/v1/listas/{id_lista}/cotizar", headers=ana).json()
    assert cotizacion and cotizacion[0]["costo_total"] > 0

    # La vendedora no ve la lista de Ana.
    assert cliente.get(f"/api/v1/listas/{id_lista}/cotizar", headers=_token(cliente, "rosa@pj.bo")).status_code == 404
    assert cliente.delete(f"/api/v1/listas/{id_lista}", headers=ana).status_code == 204
    assert cliente.get("/api/v1/listas", headers=ana).json() == []
