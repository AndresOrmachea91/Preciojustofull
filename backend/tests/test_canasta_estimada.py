"""
La canasta (y las listas de compras) usan la MISMA regla que el comparador:
lo medido en el puesto si lo hay; si no, estimado desde la referencia de la
ciudad. Y dicen cuántos productos fueron estimados.

Antes la canasta solo miraba lo medido en cada puesto: con datos reales,
donde casi todo es referencia de ciudad, cotizaba en un solo lugar.
"""
from datetime import datetime, timezone

import pytest

from src.aplicacion.casos_uso.precios.calcular_canasta import CalcularCanastaCasoUso
from src.aplicacion.puertos.entrada import ItemCanasta
from src.dominio.modelo import Fuente, Mercado, NivelPrecio, Observacion, Producto, TipoPuntoVenta
from src.dominio.servicio.motor_fusion import MotorFusion
from src.dominio.valor import Ambito, Dinero, Periodo, Unidad
from src.infraestructura.adaptadores.salida.memoria.repositorios import (
    MercadosEnMemoria, ObservacionesEnMemoria,
)

AHORA = datetime(2026, 10, 9, tzinfo=timezone.utc)


def _referencia(producto: str, monto: float) -> Observacion:
    return Observacion(
        fuente=Fuente.SIIP_IPC, nivel=NivelPrecio.MINORISTA, codigo_producto=producto,
        codigo_mercado=None, ciudad="la_paz", ambito=Ambito.CIUDAD, periodo=Periodo(2026, 8),
        precio=Dinero(monto, Unidad("KILO")), capturada_en=AHORA,
    )


def _medida(producto: str, mercado: str, monto: float) -> Observacion:
    return Observacion(
        fuente=Fuente.CAMPO, nivel=NivelPrecio.MINORISTA, codigo_producto=producto,
        codigo_mercado=mercado, periodo=Periodo(2026, 10, 9),
        precio=Dinero(monto, Unidad("KILO")), capturada_en=AHORA,
    )


@pytest.fixture
def canasta():
    mercados = MercadosEnMemoria([
        Mercado("lanza", "Mercado Lanza", TipoPuntoVenta.MERCADO, "Centro", factor_mercado=1.0),
        Mercado("tienda", "Tienda", TipoPuntoVenta.TIENDA, "Sopocachi", factor_mercado=1.2),
    ])
    observaciones = ObservacionesEnMemoria([
        _referencia("papa", 6.0), _referencia("arroz", 10.0),
        _medida("papa", "lanza", 5.0),   # en el Lanza alguien midió la papa
    ])
    return CalcularCanastaCasoUso(mercados, observaciones, MotorFusion())


def test_sin_medicion_en_el_puesto_se_cotiza_desde_la_ciudad(canasta):
    resultado = canasta.ejecutar([ItemCanasta("papa", 2), ItemCanasta("arroz", 1)])
    por_lugar = {c.codigo_mercado: c for c in resultado}

    assert set(por_lugar) == {"lanza", "tienda"}, "los dos lugares cotizan, aunque nadie midió en la tienda"
    assert all(c.cobertura == 1 for c in resultado)


def test_la_cotizacion_dice_cuantos_productos_son_estimados(canasta):
    por_lugar = {c.codigo_mercado: c for c in canasta.ejecutar([ItemCanasta("papa", 2), ItemCanasta("arroz", 1)])}
    assert por_lugar["lanza"].productos_estimados == 1     # la papa se midió; el arroz se estimó
    assert por_lugar["tienda"].productos_estimados == 2    # nada medido: todo estimado
    assert por_lugar["lanza"].nivel_precio == "minorista"


def test_lo_medido_en_el_puesto_gana_sobre_la_estimacion(canasta):
    lanza = next(c for c in canasta.ejecutar([ItemCanasta("papa", 1)]) if c.codigo_mercado == "lanza")
    assert lanza.costo_total == pytest.approx(5.0, abs=0.5)   # lo medido, no la referencia de 6
