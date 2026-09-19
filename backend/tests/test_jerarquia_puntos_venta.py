"""
Invariantes de la jerarquía de puntos de venta, en el DOMINIO.

`test_catalogo_csv.py` verifica las mismas reglas sobre el archivo. Acá se
verifica que el dominio las haga cumplir venga de donde venga el dato.
"""
from datetime import datetime, timezone

import pytest

from src.dominio.excepciones import JerarquiaInvalida, NivelesNoComparables
from src.dominio.modelo import Fuente, Mercado, NivelPrecio, Observacion, TipoPuntoVenta
from src.dominio.servicio.jerarquia import ordenar_padres_primero, validar_jerarquia
from src.dominio.servicio.motor_fusion import MotorFusion
from src.dominio.valor import Dinero, Periodo, Unidad


def _punto(codigo, tipo=TipoPuntoVenta.MERCADO, padre=None):
    return Mercado(codigo, codigo.title(), tipo, "Centro", codigo_padre=padre)


# --- las tres invariantes -------------------------------------------------

def test_un_punto_de_venta_no_puede_ser_su_propio_padre():
    with pytest.raises(ValueError, match="su propio padre"):
        _punto("rodriguez", padre="rodriguez")


def test_solo_un_mercado_puede_ser_padre():
    tienda = _punto("tienda_x", TipoPuntoVenta.TIENDA)
    hijo = _punto("puesto", TipoPuntoVenta.TIENDA, padre="tienda_x")

    with pytest.raises(JerarquiaInvalida) as e:
        validar_jerarquia([tienda, hijo])
    assert "no mercado" in str(e.value)


def test_la_jerarquia_no_pasa_de_dos_niveles():
    abuelo = _punto("rodriguez")
    padre = _punto("rodriguez_cubierto", padre="rodriguez")
    nieto = _punto("puesto_7", TipoPuntoVenta.TIENDA, padre="rodriguez_cubierto")

    with pytest.raises(JerarquiaInvalida) as e:
        validar_jerarquia([abuelo, padre, nieto])
    assert "dos niveles" in str(e.value)


def test_un_padre_que_no_existe_es_una_infraccion():
    with pytest.raises(JerarquiaInvalida, match="inexistente"):
        validar_jerarquia([_punto("hijo", padre="fantasma")])


def test_una_jerarquia_de_dos_niveles_es_valida():
    validar_jerarquia([
        _punto("rodriguez"),
        _punto("rodriguez_cubierto", padre="rodriguez"),
        _punto("tienda_x", TipoPuntoVenta.TIENDA),
    ])


def test_se_reportan_todas_las_infracciones_juntas():
    """Corregir una a la vez y volver a correr sería una tortura."""
    puntos = [
        _punto("a", TipoPuntoVenta.TIENDA),
        _punto("b", padre="a"),
        _punto("c", padre="nadie"),
    ]
    with pytest.raises(JerarquiaInvalida) as e:
        validar_jerarquia(puntos)
    assert len(e.value.infracciones) == 2


def test_ordenar_pone_a_los_padres_antes_que_a_los_hijos():
    hijo = _punto("sector", padre="rodriguez")
    padre = _punto("rodriguez")
    otro = _punto("lanza")

    ordenados = ordenar_padres_primero([hijo, otro, padre])

    assert [p.codigo for p in ordenados] == ["lanza", "rodriguez", "sector"]


# --- mayorista ------------------------------------------------------------

def test_el_tipo_mayorista_vende_a_otro_nivel():
    makro = _punto("makro", TipoPuntoVenta.MAYORISTA)
    ketal = _punto("ketal", TipoPuntoVenta.SUPERMERCADO)

    assert makro.nivel_precio is NivelPrecio.MAYORISTA
    assert ketal.nivel_precio is NivelPrecio.MINORISTA
    assert not makro.es_comparable_con(ketal)
    assert ketal.es_comparable_con(_punto("rodriguez"))
    # Tiene precio puesto: no publica rango, y no puede contener locales.
    assert makro.publica_rango is False
    assert makro.tipo.puede_ser_padre is False


def _observacion(nivel, monto=10.0):
    return Observacion(
        fuente=Fuente.CAMPO, nivel=nivel, codigo_producto="arroz", codigo_mercado="x",
        periodo=Periodo(2026, 9, 1), precio=Dinero(monto, Unidad("KILO")),
        capturada_en=datetime.now(timezone.utc),
    )


def test_el_motor_no_mezcla_precios_mayoristas_con_minoristas():
    """Promediar un precio por quintal con uno por libra da un número que no existe."""
    mezcla = [_observacion(NivelPrecio.MAYORISTA, 4.0), _observacion(NivelPrecio.MINORISTA, 9.0)]

    with pytest.raises(NivelesNoComparables):
        MotorFusion().consolidar(mezcla)


def test_el_motor_si_consolida_un_solo_nivel():
    solo_mayorista = [_observacion(NivelPrecio.MAYORISTA, 4.0), _observacion(NivelPrecio.MAYORISTA, 4.2)]
    assert MotorFusion().consolidar(solo_mayorista).observaciones_usadas == 2
