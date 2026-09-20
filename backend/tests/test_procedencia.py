"""
Todo precio publicado dice de dónde sale: observado o estimado, cuántas
observaciones lo respaldan y la fecha de la más reciente. Ningún camino
de la API puede devolver un precio sin eso.
"""
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.dominio.modelo import Fuente, Mercado, NivelPrecio, Observacion, PrecioConsolidado, TipoPuntoVenta
from src.dominio.modelo.precio_consolidado import RangoPrecio
from src.dominio.servicio.motor_fusion import MotorFusion
from src.dominio.valor import Dinero, NivelConfianza, Periodo, Procedencia, Unidad, UnidadCanonica
from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.main import app

AHORA = datetime.now(timezone.utc)


def _obs(fuente=Fuente.CAMPO, monto=10.0, unidad="KILO", mercado="rodriguez", fecha=None):
    return Observacion(
        fuente=fuente, nivel=fuente.nivel_fijo or NivelPrecio.MINORISTA,
        codigo_producto="arroz", codigo_mercado=mercado, periodo=Periodo(2026, 9, 15),
        precio=Dinero(monto, Unidad(unidad)), capturada_en=AHORA, ambito=fuente.ambito,
        fecha_observacion=fecha,
    )


# --- dominio --------------------------------------------------------------

def test_lo_medido_en_el_local_es_observado_y_trae_la_fecha_mas_reciente():
    precio = MotorFusion().consolidar([
        _obs(fecha=date(2026, 9, 10)), _obs(monto=10.5, fecha=date(2026, 9, 14)), _obs(monto=10.2),
    ])
    assert precio.procedencia is Procedencia.OBSERVADO
    assert not precio.es_estimado
    assert precio.observaciones_usadas == 3
    assert precio.fecha_observacion_mas_reciente == date(2026, 9, 14)


def test_sin_fechas_de_observacion_la_mas_reciente_es_nula_no_la_de_captura():
    precio = MotorFusion().consolidar([_obs(), _obs(monto=10.4)])
    assert precio.fecha_observacion_mas_reciente is None


def test_lo_que_sale_de_la_ciudad_es_estimado_siempre():
    """El IPC es una medición, pero de otra cosa: de la ciudad, no del local."""
    mini = Mercado("mini", "Mini", TipoPuntoVenta.MINIMARKET, "Sopocachi", factor_mercado=1.1)
    referencia = [_obs(Fuente.SIIP_IPC, 6.9, "LIBRA", mercado="la_paz", fecha=date(2026, 8, 31))]

    estimado = MotorFusion().estimar_desde_ciudad(referencia, mini)

    assert estimado.procedencia is Procedencia.ESTIMADO
    assert estimado.es_estimado
    assert estimado.observaciones_usadas == 1
    assert estimado.fecha_observacion_mas_reciente == date(2026, 8, 31)


def test_un_precio_consolidado_no_se_construye_sin_procedencia():
    with pytest.raises(TypeError):
        PrecioConsolidado(
            codigo_producto="arroz", codigo_mercado="rodriguez", periodo=Periodo(2026, 9),
            rango=RangoPrecio(10, 11), unidad=UnidadCanonica.KILOGRAMO,
            confianza=NivelConfianza.MEDIO, observaciones_usadas=1,
            fecha_observacion_mas_reciente=None, calculado_en=AHORA,
        )


def test_un_precio_consolidado_necesita_al_menos_una_observacion():
    with pytest.raises(ValueError, match="al menos una"):
        PrecioConsolidado(
            codigo_producto="arroz", codigo_mercado="rodriguez", periodo=Periodo(2026, 9),
            rango=RangoPrecio(10, 11), unidad=UnidadCanonica.KILOGRAMO,
            confianza=NivelConfianza.MEDIO, observaciones_usadas=0,
            procedencia=Procedencia.OBSERVADO, fecha_observacion_mas_reciente=None, calculado_en=AHORA,
        )


# --- API ------------------------------------------------------------------

CAMPOS_OBLIGATORIOS = ("procedencia", "observaciones_usadas", "fecha_observacion_mas_reciente")


def test_el_esquema_de_salida_exige_los_tres_campos():
    for campo in CAMPOS_OBLIGATORIOS:
        assert e.PrecioSalida.model_fields[campo].is_required(), campo
    with pytest.raises(ValidationError):
        e.PrecioSalida(
            codigo_producto="arroz", codigo_mercado="rodriguez", periodo="2026-09",
            rango=e.RangoSalida(minimo=10, maximo=11, centro=10.5), unidad="kg",
            confianza="medio", observaciones_usadas=2, fecha_observacion_mas_reciente=None,
        )   # falta procedencia
    with pytest.raises(ValidationError):
        e.PrecioSalida(
            codigo_producto="arroz", codigo_mercado="rodriguez", periodo="2026-09",
            rango=e.RangoSalida(minimo=10, maximo=11, centro=10.5), unidad="kg",
            confianza="medio", procedencia="inventado", observaciones_usadas=2,
            fecha_observacion_mas_reciente=None,
        )   # procedencia fuera del dominio


@pytest.fixture(scope="module")
def cliente():
    return TestClient(app)


def _precios_que_devuelve(cliente):
    """Todos los precios de todos los caminos de la API que publican precios."""
    r = cliente.get("/api/v1/precios/tomate/comparar")
    assert r.status_code == 200 and r.json()
    yield from (fila["precio"] for fila in r.json())
    r = cliente.get("/api/v1/precios/tomate/mercado/rodriguez")
    assert r.status_code == 200
    yield r.json()


def test_ningun_camino_de_la_api_devuelve_un_precio_sin_procedencia(cliente):
    precios = list(_precios_que_devuelve(cliente))
    assert precios
    for p in precios:
        for campo in CAMPOS_OBLIGATORIOS:
            assert campo in p, f"falta {campo} en {p}"
        assert p["procedencia"] in ("observado", "estimado")
        assert p["observaciones_usadas"] >= 1
