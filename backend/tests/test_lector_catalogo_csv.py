"""El lector de CSV traduce filas a entidades y, si no puede, dice por qué."""
from pathlib import Path

import pytest

from src.dominio.modelo import TipoPuntoVenta
from src.infraestructura.adaptadores.salida.catalogo.lector_csv import (
    CatalogoCorrupto, filas_a_puntos_venta, leer_puntos_venta,
)

CATALOGO_REAL = Path(__file__).resolve().parents[1] / "datos" / "catalogo" / "puntos_venta.csv"

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
