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


def _por_unidad(producto: str, monto: float, mes: int) -> Observacion:
    return Observacion(
        fuente=Fuente.SIIP_IPC, nivel=NivelPrecio.MINORISTA, codigo_producto=producto,
        codigo_mercado=None, ciudad="la_paz", ambito=Ambito.CIUDAD, periodo=Periodo(2026, mes),
        precio=Dinero(monto, Unidad("UNIDAD(es)")), capturada_en=AHORA,
    )


def test_con_dos_series_se_usa_la_de_la_unidad_del_producto():
    """
    El SIIP publica la papaya por kilo y por unidad. Si la serie por unidad
    es más nueva, igual no sirve para un producto que se vende por kilo:
    18 Bs la papaya por 2 kilos no son 36 Bs.
    """
    from src.aplicacion.casos_uso.precios.comparar_mercados import CompararMercadosCasoUso
    from src.dominio.modelo import Categoria
    from src.infraestructura.adaptadores.salida.memoria.repositorios import ProductosEnMemoria

    productos = ProductosEnMemoria([Producto("papaya", "Papaya", categoria=Categoria.FRUTA)])
    mercados = MercadosEnMemoria([Mercado("lanza", "Mercado Lanza", TipoPuntoVenta.MERCADO, "Centro")])
    observaciones = ObservacionesEnMemoria([_referencia("papaya", 13.0), _por_unidad("papaya", 18.0, mes=9)])

    canasta = CalcularCanastaCasoUso(mercados, observaciones, MotorFusion(), productos=productos)
    [lanza] = canasta.ejecutar([ItemCanasta("papaya", 2)])
    assert lanza.costo_total == 26.0

    comparador = CompararMercadosCasoUso(productos, mercados, observaciones, MotorFusion())
    [precio] = comparador.ejecutar("papaya")
    assert precio.precio.unidad.value == "kg" and precio.precio.rango.centro == 13.0


def test_el_historial_resume_cada_mes_por_nivel_con_la_mediana():
    from src.aplicacion.casos_uso.precios.historial_precio import HistorialPrecio
    from src.dominio.modelo import Categoria
    from src.infraestructura.adaptadores.salida.memoria.repositorios import ProductosEnMemoria

    def diario(monto, mes, dia):
        return Observacion(
            fuente=Fuente.SIIP_DIARIO, nivel=NivelPrecio.MAYORISTA, codigo_producto="papa",
            codigo_mercado=None, ciudad="la_paz", ambito=Ambito.CIUDAD, periodo=Periodo(2026, mes, dia),
            precio=Dinero(monto, Unidad("KILO")), capturada_en=AHORA,
        )

    productos = ProductosEnMemoria([Producto("papa", "Papa", categoria=Categoria.TUBERCULO)])
    observaciones = ObservacionesEnMemoria([
        _referencia("papa", 6.0),                                   # IPC agosto
        diario(4.0, 8, 1), diario(4.2, 8, 2), diario(9.9, 8, 3),    # un día raro no mueve la mediana
        diario(4.5, 9, 1),
        _por_unidad("papa", 0.5, mes=9),                            # serie en otra unidad: fuera
    ])
    unidad, puntos = HistorialPrecio(productos, observaciones).ejecutar("papa")

    assert unidad == "kg"
    assert [(p.mes, p.nivel, p.precio, p.observaciones) for p in puntos] == [
        (8, "mayorista", 4.2, 3), (8, "minorista", 6.0, 1), (9, "mayorista", 4.5, 1),
    ]
    # Con meses=1 queda solo el más reciente.
    assert {p.mes for p in HistorialPrecio(productos, observaciones).ejecutar("papa", meses=1)[1]} == {9}
