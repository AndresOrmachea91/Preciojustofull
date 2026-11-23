"""
C148: la casera lleva cuánto le queda de cada producto, el estado sale solo,
ajusta en un toque («vendí 2») y recibe un reporte con sugerencias de precio
comparadas con su mismo mercado, sin contar sus propios precios.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from src.aplicacion.casos_uso.vendedor.inventario import InventarioDelPuesto
from src.aplicacion.casos_uso.vendedor.mi_puesto import MiPuestoCasoUso
from src.aplicacion.casos_uso.vendedor.publicar_precio import PublicarPrecioPropio
from src.aplicacion.casos_uso.vendedor.reporte_inventario import (
    ReporteDelInventario, redondear_a_cincuenta, sugerir,
)
from src.dominio.excepciones import DatoInvalido, ProductoNoEncontrado
from src.dominio.modelo import ArticuloInventario, Disponibilidad, Presentacion, Rol, Usuario
from src.dominio.servicio.motor_fusion import MotorFusion
from src.infraestructura.adaptadores.salida.fotos.almacen_local import AlmacenFotosLocal
from src.infraestructura.adaptadores.salida.memoria.cuentas import UsuariosEnMemoria
from src.infraestructura.adaptadores.salida.memoria.puestos_y_ofertas import InventarioEnMemoria, PuestosEnMemoria
from src.infraestructura.adaptadores.salida.persistencia.puestos_y_ofertas import InventarioPostgres
from src.infraestructura.adaptadores.salida.persistencia.sesion import crear_esquema, crear_motor, fabrica_sesiones

AHORA = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)


@pytest.fixture
def mundo(repositorios, tmp_path):
    productos, mercados, observaciones = repositorios
    usuarios = UsuariosEnMemoria()
    rosa = usuarios.guardar(Usuario("rosa@pj.bo", "Rosa", Rol.VENDEDOR, "h", AHORA))
    puestos, inventario = PuestosEnMemoria(), InventarioEnMemoria()
    MiPuestoCasoUso(mercados, puestos, usuarios, AlmacenFotosLocal(tmp_path)).guardar(
        rosa, "14", "Verduras Rosa", ["hortaliza"], codigo_mercado="rodriguez")
    rosa = usuarios.obtener(rosa.id)
    publicar = PublicarPrecioPropio(productos, mercados, observaciones, puestos)
    reloj = {"ahora": AHORA}
    return {
        "rosa": rosa, "inventario": inventario,
        "caso": InventarioDelPuesto(productos, puestos, inventario, publicar, ahora=lambda: reloj["ahora"]),
        "reporte": ReporteDelInventario(productos, mercados, observaciones, MotorFusion(), puestos, inventario,
                                        ahora=lambda: reloj["ahora"]),
        "reloj": reloj,
    }


def test_con_la_cantidad_el_estado_sale_solo(mundo):
    caso, rosa = mundo["caso"], mundo["rosa"]
    a = caso.guardar(rosa, "tomate", 10, Presentacion.KILO, cantidad=30, minimo=5)
    assert (a.cantidad, a.minimo, a.disponibilidad) == (30, 5, Disponibilidad.HAY)
    assert caso.guardar(rosa, "tomate", 10, Presentacion.KILO, cantidad=4, minimo=5).disponibilidad is Disponibilidad.POCO
    # Aunque diga «hay», con 0 en la mano no se puede comprar.
    assert caso.guardar(rosa, "tomate", 10, Presentacion.KILO, Disponibilidad.HAY, cantidad=0).disponibilidad \
        is Disponibilidad.AGOTADO


def test_sin_cantidad_sigue_funcionando_como_antes(mundo):
    a = mundo["caso"].guardar(mundo["rosa"], "papa", 7, Presentacion.KILO, Disponibilidad.POCO)
    assert (a.cantidad, a.disponibilidad) == (None, Disponibilidad.POCO)


def test_vendi_y_llegaron_en_un_toque(mundo):
    caso, rosa = mundo["caso"], mundo["rosa"]
    caso.guardar(rosa, "tomate", 10, Presentacion.KILO, cantidad=6, minimo=2)
    assert caso.ajustar(rosa, "tomate", -3).cantidad == 3
    poco = caso.ajustar(rosa, "tomate", -1)
    assert (poco.cantidad, poco.disponibilidad) == (2, Disponibilidad.POCO)
    # Nunca baja de cero, y queda agotado.
    agotado = caso.ajustar(rosa, "tomate", -10)
    assert (agotado.cantidad, agotado.disponibilidad) == (0, Disponibilidad.AGOTADO)
    repuesto = caso.ajustar(rosa, "tomate", 20)
    assert (repuesto.cantidad, repuesto.disponibilidad, repuesto.monto) == (20, Disponibilidad.HAY, 10)


def test_ajustar_un_producto_que_no_vende_avisa(mundo):
    with pytest.raises(ProductoNoEncontrado):
        mundo["caso"].ajustar(mundo["rosa"], "trucha", -1)


def test_cantidades_imposibles_se_rechazan():
    with pytest.raises(DatoInvalido):
        ArticuloInventario(1, "tomate", 10, Presentacion.KILO, cantidad=-1)
    with pytest.raises(DatoInvalido):
        ArticuloInventario(1, "tomate", 10, Presentacion.KILO, cantidad=5, minimo=-2)


def test_la_sugerencia_compara_con_el_mercado_y_redondea_como_se_cobra():
    assert redondear_a_cincuenta(7.37) == 7.5 and redondear_a_cincuenta(7.2) == 7.0
    caro = sugerir(13, 1.0, 10.0, "Kilo")
    assert caro.tipo == "bajar" and caro.precio_sugerido == 10.0 and "30 % más caro" in caro.texto
    assert "Bs 10,00 por kilo" in caro.texto
    barato = sugerir(7, 1.0, 10.0, "Kilo")
    assert barato.tipo == "subir" and barato.precio_sugerido == 10.0
    assert sugerir(10.3, 1.0, 10.0, "Kilo").tipo == "en_linea"
    # Por arroba: el precio del mercado se lleva a la presentación en que ella vende.
    arroba = sugerir(150, 11.5, 10.0, "Arroba")
    assert arroba.precio_mercado == 115.0 and arroba.tipo == "bajar"
    assert sugerir(10, 1.0, None, "Kilo").tipo == "sin_referencia"


def test_el_reporte_junta_alertas_valor_y_consejos(mundo):
    caso, rosa, reloj = mundo["caso"], mundo["rosa"], mundo["reloj"]
    caso.guardar(rosa, "tomate", 10, Presentacion.KILO, cantidad=20, minimo=5)
    caso.guardar(rosa, "papa", 7, Presentacion.KILO, cantidad=2, minimo=5)
    reloj["ahora"] = AHORA - timedelta(days=10)
    caso.guardar(rosa, "arroz", 6, Presentacion.KILO, cantidad=0)
    reloj["ahora"] = AHORA
    r = mundo["reporte"].ejecutar(rosa)
    assert (r.productos, r.con_cantidad, r.agotados, r.queda_poco, r.sin_actualizar) == (3, 3, 1, 1, 1)
    assert r.valor_total == 20 * 10 + 2 * 7
    por_codigo = {x.articulo.codigo_producto: x for x in r.renglones}
    assert any("Queda poco" in a for a in por_codigo["papa"].alertas)
    assert any("hace 10 días" in a for a in por_codigo["arroz"].alertas)
    assert r.consejos and len(r.consejos) <= 3


def test_el_reporte_no_se_compara_con_sus_propios_precios(mundo):
    """Si ella pone un precio altísimo, la referencia del mercado no sube con ella."""
    caso, rosa = mundo["caso"], mundo["rosa"]
    caso.guardar(rosa, "tomate", 40, Presentacion.KILO, cantidad=10)
    renglon = mundo["reporte"].ejecutar(rosa).renglones[0]
    assert renglon.sugerencia.tipo == "bajar"
    assert renglon.sugerencia.precio_mercado < 40


def test_la_cantidad_se_guarda_en_la_base_y_se_agrega_a_una_base_vieja():
    motor = crear_motor("sqlite://")
    with motor.begin() as c:
        c.execute(text("CREATE TABLE inventario_puesto (id INTEGER PRIMARY KEY, id_puesto INTEGER, "
                       "codigo_producto VARCHAR(64), monto FLOAT, presentacion VARCHAR(16), disponibilidad VARCHAR(12), "
                       "actualizado_en TIMESTAMP, eliminado BOOLEAN NOT NULL DEFAULT 0)"))
    crear_esquema(motor)
    with motor.begin() as c:
        columnas = {fila[1] for fila in c.execute(text("PRAGMA table_info(inventario_puesto)"))}
    assert {"cantidad", "minimo"} <= columnas


def test_postgres_guarda_y_lee_la_cantidad():
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    with motor.begin() as c:
        c.execute(text("INSERT INTO producto (codigo, nombre, categoria, unidad_base, dias_conservacion, creado_en, "
                       "creado_por, eliminado) VALUES ('tomate', 'Tomate', 'hortaliza', 'kg', 7, CURRENT_TIMESTAMP, 'x', 0)"))
    repo = InventarioPostgres(fabrica_sesiones(motor))
    repo.guardar(ArticuloInventario(1, "tomate", 10, Presentacion.KILO, Disponibilidad.POCO, AHORA, cantidad=3, minimo=5))
    leido = repo.del_puesto(1)[0]
    assert (leido.cantidad, leido.minimo, leido.disponibilidad) == (3, 5, Disponibilidad.POCO)
