"""
El catálogo de productos es dato curado a mano, así que se rompe a mano.
Estas pruebas verifican que el archivo sea cargable y que el mapeo a las
fuentes del SIIP no tenga errores de dedo.
"""
import csv
from pathlib import Path

import pytest

from src.dominio.modelo import Categoria
from src.infraestructura.adaptadores.salida.catalogo.lector_csv import UNIDADES_BASE, BOOLEANOS

PRODUCTOS = Path(__file__).resolve().parents[1] / "datos" / "catalogo" / "productos.csv"

COLUMNAS = [
    "codigo", "nombre", "categoria", "unidad_base", "es_perecedero",
    "siip_diario", "siip_ipc", "revision", "notas",
]


@pytest.fixture(scope="module")
def filas():
    with PRODUCTOS.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_el_archivo_tiene_las_columnas_esperadas(filas):
    assert list(filas[0].keys()) == COLUMNAS


def test_hay_45_productos(filas):
    assert len(filas) == 45


def test_los_codigos_no_se_repiten(filas):
    codigos = [f["codigo"] for f in filas]
    repetidos = {c for c in codigos if codigos.count(c) > 1}
    assert not repetidos, f"códigos repetidos: {sorted(repetidos)}"


def test_las_categorias_son_del_dominio(filas):
    desconocidas = {f["categoria"] for f in filas} - {c.value for c in Categoria}
    assert not desconocidas, f"categorías fuera del dominio: {desconocidas}"


def test_las_unidades_base_son_del_dominio(filas):
    desconocidas = {f["unidad_base"] for f in filas} - set(UNIDADES_BASE)
    assert not desconocidas, f"unidades fuera del dominio: {desconocidas}"


def test_es_perecedero_es_booleano(filas):
    malos = [(f["codigo"], f["es_perecedero"]) for f in filas if f["es_perecedero"] not in BOOLEANOS]
    assert not malos, f"es_perecedero no booleano: {malos}"


def test_ningun_campo_obligatorio_esta_vacio(filas):
    faltantes = [
        (f["codigo"], col) for f in filas
        for col in ("codigo", "nombre", "categoria", "unidad_base", "es_perecedero", "revision")
        if not f[col].strip()
    ]
    assert not faltantes, f"campos vacíos: {faltantes}"


@pytest.mark.parametrize("columna", ["siip_diario", "siip_ipc"])
def test_ningun_codigo_de_fuente_apunta_a_dos_productos(filas, columna):
    """Un mismo código de fuente en dos productos duplicaría la serie."""
    codigos = [f[columna] for f in filas if f[columna]]
    repetidos = {c for c in codigos if codigos.count(c) > 1}
    assert not repetidos, f"{columna} repetidos: {sorted(repetidos)}"


def test_la_colision_platano_banana_se_resolvio_dejando_a_banana_sin_ipc(filas):
    por_codigo = {f["codigo"]: f for f in filas}
    assert por_codigo["platano"]["siip_ipc"] == "116016901"
    assert por_codigo["banana"]["siip_ipc"] == ""
    assert sum(1 for f in filas if f["siip_ipc"] == "116016901") == 1


def test_todo_producto_tiene_al_menos_una_fuente(filas):
    sin_fuente = [f["codigo"] for f in filas if not (f["siip_diario"] or f["siip_ipc"])]
    assert not sin_fuente, f"productos sin fuente: {sin_fuente}"


def test_los_codigos_de_fuente_son_numericos(filas):
    malos = [
        (f["codigo"], col, f[col]) for f in filas for col in ("siip_diario", "siip_ipc")
        if f[col] and not f[col].isdigit()
    ]
    assert not malos, f"códigos de fuente no numéricos: {malos}"
