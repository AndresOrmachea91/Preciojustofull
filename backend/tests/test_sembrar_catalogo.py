"""
La siembra es idempotente y no destruye: se prueba contra el repositorio
en memoria (el caso de uso no distingue) y, para la clave foránea, contra
SQLAlchemy sobre SQLite.
"""
from pathlib import Path

import pytest
from sqlalchemy import event

from src.aplicacion.casos_uso.sembrar_catalogo import SembrarCatalogo
from src.dominio.excepciones import JerarquiaInvalida
from src.dominio.modelo import Categoria, Mercado, Producto, TipoPuntoVenta
from src.dominio.valor import UnidadCanonica
from src.infraestructura.adaptadores.salida.catalogo.lector_csv import leer_productos, leer_puntos_venta
from src.infraestructura.adaptadores.salida.memoria.repositorios import MercadosEnMemoria, ProductosEnMemoria
from src.infraestructura.adaptadores.salida.persistencia.repositorios import MercadosPostgres, ProductosPostgres
from src.infraestructura.adaptadores.salida.persistencia.sesion import (
    crear_esquema, crear_motor, fabrica_sesiones,
)

CATALOGO_REAL = Path(__file__).resolve().parents[1] / "datos" / "catalogo" / "puntos_venta.csv"
PRODUCTOS_REAL = Path(__file__).resolve().parents[1] / "datos" / "catalogo" / "productos.csv"


def _punto(codigo, nombre=None, tipo=TipoPuntoVenta.MERCADO, padre=None, macro="Centro"):
    return Mercado(codigo, nombre or codigo.title(), tipo, macro, -16.5, -68.1,
                   macrodistrito=macro, codigo_padre=padre)


CATALOGO = [
    _punto("rodriguez_cubierto", padre="rodriguez"),   # el hijo va primero a propósito
    _punto("rodriguez"),
    _punto("ketal", tipo=TipoPuntoVenta.SUPERMERCADO),
]


def test_sembrar_dos_veces_deja_el_mismo_estado_que_sembrar_una():
    repo = MercadosEnMemoria()
    caso = SembrarCatalogo(repo)

    primera = caso.ejecutar(CATALOGO)
    estado = sorted(repo.listar(), key=lambda m: m.codigo)
    segunda = caso.ejecutar(CATALOGO)

    assert len(primera.insertados) == 3
    assert segunda.insertados == segunda.actualizados == []
    assert len(segunda.sin_cambios) == 3
    assert sorted(repo.listar(), key=lambda m: m.codigo) == estado


def test_sembrar_sobre_datos_existentes_actualiza_sin_duplicar():
    repo = MercadosEnMemoria([_punto("rodriguez", nombre="Mercado Rodriguez (viejo)")])
    caso = SembrarCatalogo(repo)

    resumen = caso.ejecutar(CATALOGO)

    assert resumen.actualizados == ["rodriguez"]
    assert sorted(resumen.insertados) == ["ketal", "rodriguez_cubierto"]
    assert len(repo.listar()) == 3
    assert repo.obtener("rodriguez").nombre == "Rodriguez"


def test_resembrar_no_pisa_el_factor_aprendido_en_campo():
    """El catálogo describe el lugar; el factor se aprende y no se resetea."""
    aprendido = Mercado("rodriguez", "Rodriguez", TipoPuntoVenta.MERCADO, "Centro",
                        -16.5, -68.1, factor_mercado=1.07, macrodistrito="Centro")
    repo = MercadosEnMemoria([aprendido])

    resumen = SembrarCatalogo(repo).ejecutar(CATALOGO)

    assert "rodriguez" in resumen.sin_cambios
    assert repo.obtener("rodriguez").factor_mercado == 1.07


def test_los_padres_se_guardan_antes_que_los_hijos():
    orden = []

    class Espia(MercadosEnMemoria):
        def guardar(self, mercado):
            orden.append(mercado.codigo)
            super().guardar(mercado)

    SembrarCatalogo(Espia()).ejecutar(CATALOGO)

    assert orden.index("rodriguez") < orden.index("rodriguez_cubierto")


def test_dry_run_reporta_pero_no_escribe():
    repo = MercadosEnMemoria([_punto("rodriguez", nombre="Viejo")])

    resumen = SembrarCatalogo(repo).ejecutar(CATALOGO, simular=True)

    assert resumen.simulado is True
    assert resumen.actualizados == ["rodriguez"]
    assert sorted(resumen.insertados) == ["ketal", "rodriguez_cubierto"]
    assert len(repo.listar()) == 1
    assert repo.obtener("rodriguez").nombre == "Viejo"


def test_una_jerarquia_invalida_no_siembra_nada():
    repo = MercadosEnMemoria()
    roto = [_punto("tienda", tipo=TipoPuntoVenta.TIENDA), _punto("hijo", padre="tienda")]

    with pytest.raises(JerarquiaInvalida):
        SembrarCatalogo(repo).ejecutar(roto)
    assert repo.listar() == []


def test_el_catalogo_real_se_siembra_en_sqlalchemy_con_clave_foranea():
    """Contra SQLite con claves foráneas activas: el orden de inserción importa de verdad."""
    motor = crear_motor("sqlite://")
    event.listen(motor, "connect", lambda con, _: con.execute("PRAGMA foreign_keys=ON"))
    crear_esquema(motor)
    repo = MercadosPostgres(fabrica_sesiones(motor))
    puntos = leer_puntos_venta(CATALOGO_REAL)

    primera = SembrarCatalogo(repo).ejecutar(puntos)
    segunda = SembrarCatalogo(repo).ejecutar(puntos)

    assert len(primera.insertados) == len(puntos)
    assert len(segunda.sin_cambios) == len(puntos)
    hijo = repo.obtener("rodriguez_cubierto")
    assert hijo.codigo_padre == "rodriguez"
    assert hijo.macrodistrito == "Cotahuma"


# --- productos ------------------------------------------------------------

PRODUCTOS = [
    Producto("arroz_primera", "Arroz de primera", Categoria.ABARROTE, 30),
    Producto("huevo", "Huevo grande", Categoria.CARNE, 5, unidad_base=UnidadCanonica.UNIDAD),
]


def test_sembrar_productos_dos_veces_deja_el_mismo_estado():
    repo = ProductosEnMemoria()
    caso = SembrarCatalogo(MercadosEnMemoria(), repo)

    primera = caso.sembrar_productos(PRODUCTOS)
    segunda = caso.sembrar_productos(PRODUCTOS)

    assert len(primera.insertados) == 2
    assert segunda.insertados == segunda.actualizados == []
    assert len(segunda.sin_cambios) == 2
    assert len(repo.listar()) == 2


def test_sembrar_productos_sobre_existentes_actualiza_sin_duplicar():
    repo = ProductosEnMemoria([Producto("huevo", "Huevo", Categoria.OTRO)])

    resumen = SembrarCatalogo(MercadosEnMemoria(), repo).sembrar_productos(PRODUCTOS)

    assert resumen.actualizados == ["huevo"]
    assert resumen.insertados == ["arroz_primera"]
    assert len(repo.listar()) == 2
    assert repo.obtener("huevo").unidad_base is UnidadCanonica.UNIDAD


def test_dry_run_de_productos_no_escribe():
    repo = ProductosEnMemoria()

    resumen = SembrarCatalogo(MercadosEnMemoria(), repo).sembrar_productos(PRODUCTOS, simular=True)

    assert len(resumen.insertados) == 2
    assert repo.listar() == []


def test_sin_repositorio_de_productos_no_se_puede_sembrar_productos():
    with pytest.raises(ValueError, match="repositorio de productos"):
        SembrarCatalogo(MercadosEnMemoria()).sembrar_productos(PRODUCTOS)


def test_el_catalogo_real_de_productos_se_siembra_en_sqlalchemy():
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    fabrica = fabrica_sesiones(motor)
    caso = SembrarCatalogo(MercadosPostgres(fabrica), ProductosPostgres(fabrica))
    productos = leer_productos(PRODUCTOS_REAL)

    primera = caso.sembrar_productos(productos)
    segunda = caso.sembrar_productos(productos)

    assert len(primera.insertados) == 45
    assert len(segunda.sin_cambios) == 45
    assert ProductosPostgres(fabrica).obtener("cebolla_verde").unidad_base is UnidadCanonica.ATADO
