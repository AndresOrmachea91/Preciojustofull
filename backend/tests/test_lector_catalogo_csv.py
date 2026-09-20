"""El lector de CSV traduce filas a entidades y, si no puede, dice por qué."""
from pathlib import Path

import pytest

from src.dominio.modelo import Categoria, TipoPuntoVenta
from src.dominio.valor import UnidadCanonica
from src.infraestructura.adaptadores.salida.catalogo.lector_csv import (
    CatalogoCorrupto, filas_a_productos, filas_a_puntos_venta, leer_productos, leer_puntos_venta,
)

CATALOGO = Path(__file__).resolve().parents[1] / "datos" / "catalogo"
CATALOGO_REAL = CATALOGO / "puntos_venta.csv"
PRODUCTOS_REAL = CATALOGO / "productos.csv"

FILA_BUENA = {
    "codigo": "rodriguez", "nombre": "Mercado Rodríguez", "tipo": "mercado",
    "macrodistrito": "Cotahuma", "latitud": "-16.500192", "longitud": "-68.138992",
    "codigo_padre": "", "osm_id": "w733480376", "revision": "ok", "notas": "",
}


def test_traduce_una_fila_completa():
    (m,) = filas_a_puntos_venta([FILA_BUENA])

    assert m.codigo == "rodriguez"
    assert m.tipo is TipoPuntoVenta.MERCADO
    assert m.macrodistrito == "Cotahuma"
    assert m.zona == "Cotahuma"
    assert (m.latitud, m.longitud) == (-16.500192, -68.138992)
    assert m.codigo_padre is None


def test_un_padre_vacio_es_ninguno_y_uno_lleno_se_conserva():
    con_padre = {**FILA_BUENA, "codigo": "rodriguez_cubierto", "codigo_padre": "rodriguez"}
    (m,) = filas_a_puntos_venta([con_padre])
    assert m.codigo_padre == "rodriguez"


@pytest.mark.parametrize("fila, motivo", [
    ({**FILA_BUENA, "tipo": "kiosco"}, "tipo desconocido 'kiosco'"),
    ({**FILA_BUENA, "latitud": "16,50"}, "coordenadas ilegibles"),
    ({**FILA_BUENA, "nombre": "  "}, "la columna 'nombre' está vacía"),
    ({**FILA_BUENA, "codigo_padre": "rodriguez"}, "su propio padre"),
])
def test_una_fila_corrupta_falla_con_fila_y_motivo(fila, motivo):
    with pytest.raises(CatalogoCorrupto) as e:
        filas_a_puntos_venta([FILA_BUENA, fila])
    assert e.value.numero_fila == 3
    assert motivo in str(e.value)


def test_un_archivo_sin_las_columnas_esperadas_falla_antes_de_leer_filas(tmp_path):
    archivo = tmp_path / "malo.csv"
    archivo.write_text("codigo,nombre\nx,y\n", encoding="utf-8")

    with pytest.raises(CatalogoCorrupto, match="faltan las columnas"):
        leer_puntos_venta(archivo)


def test_el_catalogo_real_se_lee_entero():
    puntos = leer_puntos_venta(CATALOGO_REAL)

    assert len(puntos) >= 50
    por_codigo = {p.codigo: p for p in puntos}
    assert por_codigo["rodriguez_cubierto"].codigo_padre == "rodriguez"
    assert por_codigo["makro_centro"].tipo is TipoPuntoVenta.MAYORISTA


# --- productos ------------------------------------------------------------

PRODUCTO_BUENO = {
    "codigo": "huevo", "nombre": "Huevo grande", "categoria": "carne", "unidad_base": "unidad",
    "es_perecedero": "si", "siip_diario": "29", "siip_ipc": "114040101",
    "revision": "verificar_unidad", "notas": "",
}


def test_traduce_un_producto_completo():
    (p,) = filas_a_productos([PRODUCTO_BUENO])

    assert p.codigo == "huevo"
    assert p.categoria is Categoria.CARNE
    assert p.unidad_base is UnidadCanonica.UNIDAD
    assert p.es_perecedero is True
    assert filas_a_productos([{**PRODUCTO_BUENO, "es_perecedero": "no"}])[0].es_perecedero is False


@pytest.mark.parametrize("fila, motivo", [
    ({**PRODUCTO_BUENO, "categoria": "bebida"}, "categoría desconocida 'bebida'"),
    ({**PRODUCTO_BUENO, "unidad_base": "caja"}, "unidad_base desconocida 'caja'"),
    ({**PRODUCTO_BUENO, "es_perecedero": "quizás"}, "es_perecedero debe ser si o no"),
    ({**PRODUCTO_BUENO, "nombre": ""}, "la columna 'nombre' está vacía"),
])
def test_un_producto_corrupto_falla_con_fila_y_motivo(fila, motivo):
    with pytest.raises(CatalogoCorrupto) as e:
        filas_a_productos([PRODUCTO_BUENO, fila])
    assert e.value.numero_fila == 3
    assert motivo in str(e.value)


def test_el_catalogo_real_de_productos_se_lee_entero():
    productos = leer_productos(PRODUCTOS_REAL)

    assert len(productos) == 45
    por_codigo = {p.codigo: p for p in productos}
    assert por_codigo["cebolla_verde"].unidad_base is UnidadCanonica.ATADO
    assert por_codigo["trucha"].categoria is Categoria.PESCADO
    assert por_codigo["leche_polvo"].categoria is Categoria.LACTEO
    assert por_codigo["arroz_primera"].es_perecedero is False


def test_el_mapeo_a_las_fuentes_sale_del_catalogo():
    from src.infraestructura.adaptadores.salida.catalogo.lector_csv import leer_mapeo_fuentes

    mapeo = leer_mapeo_fuentes(PRODUCTOS_REAL)

    assert mapeo["siip_diario"]["arroz_primera"] == "5"
    assert mapeo["siip_ipc"]["arroz_primera"] == "111030102"
    assert "banana" not in mapeo["siip_ipc"] and mapeo["siip_diario"]["banana"] == "60"
    assert len(mapeo["siip_diario"]) == 45 and len(mapeo["siip_ipc"]) == 41
