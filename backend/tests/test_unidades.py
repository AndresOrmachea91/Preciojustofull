"""
Unidades tal como las escribe el SIIP de verdad, tomadas del volcado del
18 de septiembre de 2026. Si una conversión está mal, todos los precios
del sistema quedan mal.
"""
import pytest

from src.dominio.excepciones import UnidadDesconocida
from src.dominio.valor import Dinero, Unidad, UnidadCanonica

KG, L, U, ATADO = (UnidadCanonica.KILOGRAMO, UnidadCanonica.LITRO,
                   UnidadCanonica.UNIDAD, UnidadCanonica.ATADO)


@pytest.mark.parametrize("texto, canonica, factor", [
    # Un cuarto de arroba: Potosí y Cochabamba cotizan el arroz así.
    ("CUARTILLA", KG, 2.875),
    # Diario mayorista, La Paz.
    ("qq.", KG, 46.0),
    ("SACO qq.", KG, 46.0),
    ("@", KG, 11.5),
    ("BOLSA  @", KG, 11.5),
    ("Kg.", KG, 1.0),
    ("Kg,", KG, 1.0),                 # el tomate viene con coma
    ("46 Kg.", KG, 46.0),
    ("SACO 46 Kg.", KG, 46.0),
    ("CAJA 17 Kg.", KG, 17.0),
    ("LATA 17 Kg.", KG, 17.0),
    ("LATA 2500 grs.", KG, 2.5),
    ("Lt.", L, 1.0),
    ("BIDON 946 ml.", L, 0.946),
    ("BIDON 900 cc.", L, 0.9),
    ("unid.", U, 1.0),                # huevo: por unidad, no por ciento
    ("100 unid.", U, 100.0),          # frutas, choclo, manzana
    ("Ciento", U, 100.0),
    ("caja de 21 kgr,", KG, 21.0),    # lo que dice el NOMBRE de la manzana
    # IPC consumidor final.
    ("KILO(s)", KG, 1.0),
    ("LIBRA(s)", KG, 0.46),
    ("UNIDAD(es)", U, 1.0),
    ("GRAMO(s)", KG, 0.001),
    ("MILILITRO(s)", L, 0.001),
    ("atado", ATADO, 1.0),
])
def test_convierte_las_unidades_reales_del_siip(texto, canonica, factor):
    assert Unidad(texto).equivalencia() == (canonica, pytest.approx(factor))


@pytest.mark.parametrize("texto", ["CAJA", "saco", "LATA", "manojo", "", "caja grande"])
def test_un_bulto_sin_peso_declarado_no_convierte(texto):
    """Nunca se adivina un peso para colar un precio por bulto como Bs/kg."""
    assert not Unidad(texto).es_conocida()
    with pytest.raises(UnidadDesconocida):
        Unidad(texto).equivalencia()


def test_el_arroz_por_cuartilla_queda_en_bs_por_kilo():
    """Bs 41,47 la cuartilla en Potosí son Bs 14,42 el kilo."""
    valor, canonica = Dinero(41.47, Unidad("CUARTILLA")).por_unidad_canonica()
    assert canonica is KG
    assert valor == pytest.approx(41.47 / 2.875, abs=0.01)


def test_el_huevo_por_unidad_y_por_ciento_dan_lo_mismo_por_unidad():
    por_unidad, _ = Dinero(1.67, Unidad("unid.")).por_unidad_canonica()
    por_ciento, _ = Dinero(167.0, Unidad("100 unid.")).por_unidad_canonica()
    assert por_unidad == pytest.approx(por_ciento)


def test_la_manzana_por_ciento_no_se_confunde_con_la_caja_del_nombre():
    """
    El nombre del producto dice "caja de 21 kgr" pero la tabla cotiza por
    "100 unid.". Manda la columna de unidad: Bs 325 el ciento son Bs 3,25
    la unidad, y no se convierte a kilo porque no se sabe cuánto pesa una.
    """
    valor, canonica = Dinero(325.0, Unidad("100 unid.")).por_unidad_canonica()
    assert canonica is U
    assert valor == pytest.approx(3.25)


def test_un_atado_no_convierte_a_kilo():
    _, canonica = Dinero(5.0, Unidad("atado")).por_unidad_canonica()
    assert canonica is ATADO
