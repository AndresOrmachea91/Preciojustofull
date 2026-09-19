"""
El catálogo es un dato versionado a mano, y lo que se edita a mano se rompe.

Estas pruebas no verifican lógica de negocio: verifican que el archivo que
alimenta la siembra sea cargable. Un código repetido o un padre inexistente
no debe descubrirse cuando la siembra ya está a medio correr contra la base
de producción.
"""
import csv
from pathlib import Path

import pytest

CATALOGO = Path(__file__).resolve().parents[1] / "datos" / "catalogo"
PUNTOS_VENTA = CATALOGO / "puntos_venta.csv"

COLUMNAS = [
    "codigo", "nombre", "tipo", "macrodistrito",
    "latitud", "longitud", "codigo_padre", "osm_id", "revision", "notas",
]
TIPOS = {"mercado", "supermercado", "minimarket", "tienda", "mayorista"}
MACRODISTRITOS = {
    "Centro", "Cotahuma", "Max Paredes", "Periférica",
    "San Antonio", "Sur", "Mallasa",
}
# Caja generosa alrededor del municipio de La Paz. No pretende ser el límite
# municipal: pretende atrapar el punto y la coma invertidos y el signo perdido.
LATITUD = (-16.62, -16.40)
LONGITUD = (-68.25, -68.00)


@pytest.fixture(scope="module")
def filas():
    with PUNTOS_VENTA.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_el_archivo_tiene_las_columnas_esperadas(filas):
    assert list(filas[0].keys()) == COLUMNAS


def test_hay_puntos_de_venta_cargados(filas):
    assert len(filas) >= 50


def test_los_codigos_no_se_repiten(filas):
    codigos = [f["codigo"] for f in filas]
    repetidos = {c for c in codigos if codigos.count(c) > 1}
    assert not repetidos, f"códigos repetidos: {sorted(repetidos)}"


def test_no_se_repite_el_origen_en_openstreetmap(filas):
    """Dos filas con el mismo osm_id son el mismo lugar cargado dos veces."""
    ids = [f["osm_id"] for f in filas if f["osm_id"]]
    repetidos = {i for i in ids if ids.count(i) > 1}
    assert not repetidos, f"osm_id repetidos: {sorted(repetidos)}"


def test_ningun_campo_obligatorio_esta_vacio(filas):
    faltantes = [
        (f["codigo"], col)
        for f in filas
        for col in ("codigo", "nombre", "tipo", "macrodistrito", "latitud", "longitud")
        if not f[col].strip()
    ]
    assert not faltantes, f"campos vacíos: {faltantes}"


def test_los_tipos_son_conocidos(filas):
    desconocidos = {f["tipo"] for f in filas} - TIPOS
    assert not desconocidos, f"tipos fuera del dominio: {desconocidos}"


def test_los_macrodistritos_son_de_la_paz(filas):
    desconocidos = {f["macrodistrito"] for f in filas} - MACRODISTRITOS
    assert not desconocidos, f"macrodistritos desconocidos: {desconocidos}"


def test_las_coordenadas_caen_en_la_paz(filas):
    fuera = [
        f["codigo"] for f in filas
        if not (LATITUD[0] <= float(f["latitud"]) <= LATITUD[1]
                and LONGITUD[0] <= float(f["longitud"]) <= LONGITUD[1])
    ]
    assert not fuera, f"coordenadas fuera de La Paz: {fuera}"


def test_las_coordenadas_no_estan_pegadas_unas_a_otras(filas):
    """Dos puntos idénticos casi siempre son un copiar-pegar sin corregir."""
    pares = [(f["latitud"], f["longitud"]) for f in filas]
    repetidos = {p for p in pares if pares.count(p) > 1}
    assert not repetidos, f"coordenadas repetidas: {sorted(repetidos)}"


def test_todo_padre_declarado_existe(filas):
    codigos = {f["codigo"] for f in filas}
    colgados = [
        (f["codigo"], f["codigo_padre"]) for f in filas
        if f["codigo_padre"] and f["codigo_padre"] not in codigos
    ]
    assert not colgados, f"codigo_padre inexistente: {colgados}"


def test_la_jerarquia_no_tiene_ciclos(filas):
    padre_de = {f["codigo"]: f["codigo_padre"] for f in filas}
    for codigo in padre_de:
        visto, actual = {codigo}, padre_de[codigo]
        while actual:
            assert actual not in visto, f"ciclo en la jerarquía desde {codigo}"
            visto.add(actual)
            actual = padre_de.get(actual, "")


def test_la_jerarquia_no_pasa_de_dos_niveles(filas):
    """Un local pertenece a un mercado. Un local dentro de un local dentro
    de un mercado no es un modelo, es un error de carga."""
    padre_de = {f["codigo"]: f["codigo_padre"] for f in filas}
    nietos = [
        c for c, p in padre_de.items()
        if p and padre_de.get(p)
    ]
    assert not nietos, f"jerarquía de más de dos niveles: {nietos}"


def test_solo_los_mercados_son_padres(filas):
    tipo_de = {f["codigo"]: f["tipo"] for f in filas}
    malos = [
        (f["codigo"], f["codigo_padre"]) for f in filas
        if f["codigo_padre"] and tipo_de[f["codigo_padre"]] != "mercado"
    ]
    assert not malos, f"padres que no son mercados: {malos}"
