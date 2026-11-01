"""
El administrador gestiona el catálogo: mercados, tiendas y productos con
sus presentaciones de venta (kilo, libra, arroba, quintal...).
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from src.aplicacion.casos_uso.administracion.gestionar_catalogo import (
    GestionarProductos, GestionarPuntosVenta, codigo_desde_nombre,
)
from src.dominio.excepciones import (
    CodigoYaExiste, DatoInvalido, JerarquiaInvalida, MercadoNoEncontrado, PermisoDenegado,
    PresentacionInvalida, PuntoVentaConDependientes,
)
from src.dominio.modelo import Categoria, Presentacion, Producto, Rol, TipoPuntoVenta, Usuario
from src.dominio.modelo.presentacion import compatibles, precio_en
from src.dominio.valor import UnidadCanonica
from src.infraestructura.adaptadores.entrada.api import dependencias
from src.infraestructura.adaptadores.entrada.api.main import app
from src.infraestructura.adaptadores.salida.memoria.cuentas import UsuariosEnMemoria
from src.infraestructura.adaptadores.salida.memoria.repositorios import (
    MercadosEnMemoria, ProductosEnMemoria,
)
from src.infraestructura.adaptadores.salida.persistencia.repositorios import (
    MercadosPostgres, ProductosPostgres,
)
from src.infraestructura.adaptadores.salida.persistencia.sesion import (
    crear_esquema, crear_motor, fabrica_sesiones,
)

AHORA = datetime(2026, 10, 9, tzinfo=timezone.utc)
ADMIN = Usuario("admin@pj.bo", "Admin", Rol.ADMINISTRADOR, "h", AHORA, id=1)
VECINO = Usuario("ana@pj.bo", "Ana", Rol.USUARIO, "h", AHORA, id=2)
EN_LA_PAZ = dict(latitud=-16.4998, longitud=-68.1385)


# --- presentaciones (dominio) -----------------------------------------------

def test_un_producto_por_kilo_se_vende_en_libra_kilo_arroba_y_quintal():
    assert compatibles(UnidadCanonica.KILOGRAMO) == (
        Presentacion.LIBRA, Presentacion.KILO, Presentacion.ARROBA, Presentacion.QUINTAL,
    )
    assert Producto("arroz", "Arroz").presentaciones == compatibles(UnidadCanonica.KILOGRAMO)


def test_las_presentaciones_por_defecto_siguen_como_se_compra_cada_categoria():
    from src.dominio.modelo.producto import Categoria

    def de(categoria, unidad=UnidadCanonica.KILOGRAMO):
        return Producto("x", "X", categoria=categoria, unidad_base=unidad).presentaciones

    P = Presentacion
    # Nadie compra carne por arroba: 60 Bs/kg x 11,5 = 690 Bs, una cifra que confunde.
    assert de(Categoria.CARNE) == (P.LIBRA, P.KILO)
    assert de(Categoria.PESCADO) == (P.LIBRA, P.KILO)
    assert de(Categoria.FRUTA) == (P.LIBRA, P.KILO, P.ARROBA)
    assert de(Categoria.TUBERCULO) == (P.LIBRA, P.KILO, P.ARROBA, P.QUINTAL)
    # Por unidad: el maple (30) es del huevo; un limón se vende por unidad o docena.
    assert de(Categoria.CARNE, UnidadCanonica.UNIDAD) == (P.UNIDAD, P.DOCENA, P.MAPLE)
    assert de(Categoria.FRUTA, UnidadCanonica.UNIDAD) == (P.UNIDAD, P.DOCENA)
    # Lo que elige el administrador manda sobre la regla.
    assert Producto("x", "X", categoria=Categoria.CARNE, presentaciones=(P.KILO, P.ARROBA)).presentaciones == (
        P.KILO, P.ARROBA,
    )


def test_el_precio_por_kilo_se_lleva_a_cada_presentacion():
    assert precio_en(10.0, Presentacion.QUINTAL) == pytest.approx(460.0)
    assert precio_en(10.0, Presentacion.ARROBA) == pytest.approx(115.0)
    assert precio_en(10.0, Presentacion.LIBRA) == pytest.approx(4.6)
    assert precio_en(1.2, Presentacion.MAPLE) == pytest.approx(36.0)


@pytest.mark.parametrize("unidad,presentaciones,mensaje", [
    (UnidadCanonica.KILOGRAMO, (Presentacion.DOCENA, Presentacion.KILO), "docena"),
    (UnidadCanonica.KILOGRAMO, (Presentacion.QUINTAL,), "unidad base"),
    (UnidadCanonica.UNIDAD, (Presentacion.KILO,), "kilo"),
])
def test_no_se_mezclan_presentaciones_de_otra_magnitud(unidad, presentaciones, mensaje):
    with pytest.raises(PresentacionInvalida, match=mensaje):
        Producto("x", "X", unidad_base=unidad, presentaciones=presentaciones)


def test_codigo_desde_nombre():
    assert codigo_desde_nombre("Mercado Rodríguez — sector Ñ") == "mercado_rodriguez_sector_n"


# --- casos de uso ------------------------------------------------------------

@pytest.fixture
def catalogo():
    mercados, productos, usuarios = MercadosEnMemoria(), ProductosEnMemoria(), UsuariosEnMemoria()
    return GestionarPuntosVenta(mercados, usuarios), GestionarProductos(productos), mercados, usuarios


def test_crear_un_mercado_arma_su_codigo_y_no_lo_repite(catalogo):
    puntos, *_ = catalogo
    a = puntos.crear(ADMIN, nombre="Mercado Lanza", tipo=TipoPuntoVenta.MERCADO, **EN_LA_PAZ)
    b = puntos.crear(ADMIN, nombre="Mercado Lanza", tipo=TipoPuntoVenta.MERCADO, **EN_LA_PAZ)
    assert (a.codigo, b.codigo) == ("mercado_lanza", "mercado_lanza_2")
    with pytest.raises(CodigoYaExiste):
        puntos.crear(ADMIN, nombre="Otro", tipo=TipoPuntoVenta.DISTRIBUIDOR, codigo="mercado_lanza")


def test_solo_el_administrador_toca_el_catalogo(catalogo):
    puntos, productos, *_ = catalogo
    with pytest.raises(PermisoDenegado):
        puntos.crear(VECINO, nombre="X", tipo=TipoPuntoVenta.DISTRIBUIDOR)
    with pytest.raises(PermisoDenegado):
        productos.crear(VECINO, nombre="X", categoria=Categoria.OTRO, unidad_base=UnidadCanonica.KILOGRAMO)


@pytest.mark.parametrize("latitud,longitud", [
    (-16.5, None),            # falta una
    (16.5, -68.13),           # signo de la latitud
    (-68.13, -16.5),          # invertidas
    (-17.39, -66.16),         # Cochabamba: fuera del área
])
def test_la_ubicacion_tiene_que_estar_en_la_paz_o_el_alto(catalogo, latitud, longitud):
    puntos, *_ = catalogo
    with pytest.raises(DatoInvalido, match="ubicación"):
        puntos.crear(ADMIN, nombre="X", tipo=TipoPuntoVenta.DISTRIBUIDOR, latitud=latitud, longitud=longitud)


def test_un_sector_solo_cuelga_de_un_mercado_que_existe(catalogo):
    puntos, *_ = catalogo
    puntos.crear(ADMIN, nombre="Mercado Lanza", tipo=TipoPuntoVenta.MERCADO)
    tienda = puntos.crear(ADMIN, nombre="Distribuidora Doña Rosa", tipo=TipoPuntoVenta.DISTRIBUIDOR)
    sector = puntos.crear(ADMIN, nombre="Lanza carnes", tipo=TipoPuntoVenta.MERCADO, codigo_padre="mercado_lanza")
    assert sector.codigo_padre == "mercado_lanza"
    with pytest.raises(MercadoNoEncontrado):
        puntos.crear(ADMIN, nombre="X", tipo=TipoPuntoVenta.DISTRIBUIDOR, codigo_padre="no_existe")
    with pytest.raises(JerarquiaInvalida):
        puntos.crear(ADMIN, nombre="X", tipo=TipoPuntoVenta.DISTRIBUIDOR, codigo_padre=tienda.codigo)


def test_actualizar_conserva_codigo_y_factor(catalogo):
    puntos, _, mercados, _ = catalogo
    m = puntos.crear(ADMIN, nombre="Mercado Lanza", tipo=TipoPuntoVenta.MERCADO)
    mercados.guardar(type(m)(**{**{f: getattr(m, f) for f in m.__slots__}, "factor_mercado": 1.07}))
    nuevo = puntos.actualizar(ADMIN, m.codigo, nombre="Mercado Lanza (nuevo)",
                              tipo=TipoPuntoVenta.MERCADO, zona="Centro", **EN_LA_PAZ)
    assert (nuevo.codigo, nuevo.nombre, nuevo.factor_mercado) == ("mercado_lanza", "Mercado Lanza (nuevo)", 1.07)


def test_no_se_elimina_un_mercado_con_sectores_o_vendedores(catalogo):
    puntos, _, mercados, usuarios = catalogo
    puntos.crear(ADMIN, nombre="Mercado Lanza", tipo=TipoPuntoVenta.MERCADO)
    puntos.crear(ADMIN, nombre="Lanza carnes", tipo=TipoPuntoVenta.MERCADO, codigo_padre="mercado_lanza")
    with pytest.raises(PuntoVentaConDependientes, match="sectores"):
        puntos.eliminar(ADMIN, "mercado_lanza")

    usuarios.guardar(Usuario("v@pj.bo", "V", Rol.VENDEDOR, "h", AHORA, codigo_punto_venta="lanza_carnes"))
    with pytest.raises(PuntoVentaConDependientes, match="vendedores"):
        puntos.eliminar(ADMIN, "lanza_carnes")


def test_eliminar_un_producto_lo_saca_del_catalogo(catalogo):
    _, productos, *_ = catalogo
    p = productos.crear(ADMIN, nombre="Huevo", categoria=Categoria.OTRO, unidad_base=UnidadCanonica.UNIDAD,
                        presentaciones=(Presentacion.UNIDAD, Presentacion.MAPLE))
    assert p.presentaciones == (Presentacion.UNIDAD, Presentacion.MAPLE)
    productos.eliminar(ADMIN, "huevo")
    from src.dominio.excepciones import ProductoNoEncontrado
    with pytest.raises(ProductoNoEncontrado):
        productos.eliminar(ADMIN, "huevo")


# --- contrato: memoria y SQLAlchemy se comportan igual ---------------------

@pytest.fixture(params=["memoria", "sqlalchemy"])
def repos(request):
    if request.param == "memoria":
        return ProductosEnMemoria(), MercadosEnMemoria()
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    fabrica = fabrica_sesiones(motor)
    return ProductosPostgres(fabrica), MercadosPostgres(fabrica)


def test_contrato_presentaciones_y_eliminar(repos):
    productos, mercados = repos
    productos.guardar(Producto("huevo", "Huevo", unidad_base=UnidadCanonica.UNIDAD,
                               presentaciones=(Presentacion.UNIDAD, Presentacion.MAPLE)))
    assert productos.obtener("huevo").presentaciones == (Presentacion.UNIDAD, Presentacion.MAPLE)

    productos.eliminar("huevo")
    assert productos.obtener("huevo") is None and productos.listar() == []

    from src.dominio.modelo import Mercado
    mercados.guardar(Mercado("lanza", "Lanza", TipoPuntoVenta.MERCADO, "Centro"))
    mercados.eliminar("lanza")
    assert mercados.obtener("lanza") is None and mercados.listar() == []


# --- HTTP ----------------------------------------------------------------------

@pytest.fixture
def cliente():
    dependencias._cuentas.cache_clear()
    dependencias._repositorios.cache_clear()
    dependencias.caso_registrar_usuario().crear_como_sistema("admin@pj.bo", "Admin", "clave1234", Rol.ADMINISTRADOR)
    dependencias.caso_registrar_usuario().crear_como_sistema("ana@pj.bo", "Ana", "clave1234", Rol.USUARIO)
    with TestClient(app) as c:
        yield c
    dependencias._cuentas.cache_clear()
    dependencias._repositorios.cache_clear()


def _token(cliente, correo):
    r = cliente.post("/api/v1/auth/ingresar", json={"correo": correo, "contrasena": "clave1234"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_api_catalogo_del_administrador(cliente):
    admin = _token(cliente, "admin@pj.bo")
    r = cliente.post("/api/v1/admin/mercados", headers=admin, json={
        "nombre": "Distribuidora Doña Rosa", "tipo": "distribuidor", "zona": "Sopocachi", **EN_LA_PAZ})
    assert r.status_code == 201 and r.json()["codigo"] == "distribuidora_dona_rosa"
    assert "distribuidora_dona_rosa" in [m["codigo"] for m in cliente.get("/api/v1/mercados").json()]

    r = cliente.put("/api/v1/admin/mercados/distribuidora_dona_rosa", headers=admin, json={
        "nombre": "Distribuidora Doña Rosa", "tipo": "distribuidor", "latitud": 16.5, "longitud": -68.1})
    assert r.status_code == 400

    r = cliente.post("/api/v1/admin/productos", headers=admin, json={
        "nombre": "Huevo de granja", "categoria": "otro", "unidad_base": "u", "presentaciones": ["unidad", "maple"]})
    assert r.status_code == 201
    assert [p["codigo"] for p in r.json()["presentaciones"]] == ["unidad", "maple"]
    assert r.json()["presentaciones"][1]["factor"] == 30

    assert cliente.delete("/api/v1/admin/mercados/distribuidora_dona_rosa", headers=admin).status_code == 204
    assert "distribuidora_dona_rosa" not in [m["codigo"] for m in cliente.get("/api/v1/mercados").json()]


def test_api_catalogo_publico_trae_presentaciones(cliente):
    tomate = next(p for p in cliente.get("/api/v1/productos").json() if p["codigo"] == "tomate")
    assert tomate["unidad_base"] == "kg"
    # Hortaliza: hasta arroba. El quintal queda para tubérculos y abarrotes.
    assert {p["codigo"] for p in tomate["presentaciones"]} == {"libra", "kilo", "arroba"}


def test_api_un_usuario_no_toca_el_catalogo(cliente):
    ana = _token(cliente, "ana@pj.bo")
    r = cliente.post("/api/v1/admin/productos", headers=ana, json={"nombre": "X"})
    assert r.status_code == 403
    assert cliente.delete("/api/v1/admin/mercados/rodriguez", headers=ana).status_code == 403
