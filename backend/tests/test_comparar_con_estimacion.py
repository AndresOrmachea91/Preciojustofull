"""
Hoy nadie midió en los mercados concretos: todo lo que hay es la referencia
de ciudad del SIIP. La comparación tiene que mostrar precios igual, pero
diciendo que son ESTIMADOS, y sin poner un mayorista a competir con un
puesto.
"""
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from src.aplicacion.casos_uso.comparar_mercados import CompararMercadosCasoUso
from src.aplicacion.casos_uso.consultar_precio import ConsultarPrecioProducto
from src.dominio.modelo import Fuente, Mercado, NivelPrecio, Observacion, TipoPuntoVenta
from src.dominio.valor import Dinero, Periodo, Procedencia, Unidad
from src.infraestructura.adaptadores.entrada.api.main import app
from src.infraestructura.adaptadores.salida.memoria.repositorios import datos_de_ejemplo

AHORA = datetime.now(timezone.utc)


def _referencia(fuente, monto, unidad, producto="papa", periodo=Periodo(2026, 8)):
    return Observacion(
        fuente=fuente, nivel=fuente.nivel_fijo, codigo_producto=producto, codigo_mercado=None,
        ciudad="la_paz", periodo=periodo, precio=Dinero(monto, Unidad(unidad)),
        capturada_en=AHORA, ambito=fuente.ambito,
    )


def _repos_con_referencia():
    productos, mercados, observaciones = datos_de_ejemplo()
    mercados.guardar(Mercado("makro", "Makro", TipoPuntoVenta.MAYORISTA, "Centro", -16.49, -68.14))
    observaciones.guardar_varias([
        _referencia(Fuente.SIIP_IPC, 3.20, "LIBRA(s)"),        # consumidor final, La Paz
        _referencia(Fuente.SIIP_DIARIO, 56.67, "@"),           # mayorista, La Paz
    ])
    return productos, mercados, observaciones


def test_un_mercado_sin_mediciones_recibe_un_precio_estimado_desde_la_ciudad():
    productos, mercados, observaciones = _repos_con_referencia()
    resultado = CompararMercadosCasoUso(productos, mercados, observaciones).ejecutar("papa")
    por_codigo = {r.codigo_mercado: r for r in resultado}

    # rodriguez tiene mediciones propias: observado. El minimarket no: estimado.
    assert por_codigo["rodriguez"].precio.procedencia is Procedencia.OBSERVADO
    mini = por_codigo["minimarket_sopocachi"]
    assert mini.precio.procedencia is Procedencia.ESTIMADO
    assert mini.precio.rango.centro > 0
    assert any("no es una medición en minimarket_sopocachi" in c for c in mini.precio.conflictos)


def test_el_mayorista_se_estima_desde_la_referencia_mayorista_y_no_compite():
    productos, mercados, observaciones = _repos_con_referencia()
    resultado = CompararMercadosCasoUso(productos, mercados, observaciones).ejecutar("papa")

    makro = next(r for r in resultado if r.codigo_mercado == "makro")
    assert makro.nivel_precio == NivelPrecio.MAYORISTA.value
    assert makro.precio.procedencia is Procedencia.ESTIMADO
    assert makro.precio.rango.centro < 56.67 / 11.5 * 1.1   # viene de Bs/@ mayorista, no de la libra minorista
    # Los minoristas van primero, ordenados entre sí; el mayorista al final.
    niveles = [r.nivel_precio for r in resultado]
    assert niveles == sorted(niveles, key=lambda n: n == "mayorista")


def test_sin_medicion_ni_referencia_el_mercado_se_omite():
    productos, mercados, observaciones = datos_de_ejemplo()   # sin referencia de ciudad
    resultado = CompararMercadosCasoUso(productos, mercados, observaciones).ejecutar("tomate")
    assert all(r.precio.procedencia is Procedencia.OBSERVADO for r in resultado)
    assert "minimarket_sopocachi" in {r.codigo_mercado for r in resultado}   # tiene medición propia


def test_consultar_un_mercado_sin_mediciones_devuelve_estimado():
    productos, mercados, observaciones = _repos_con_referencia()
    caso = ConsultarPrecioProducto(productos, observaciones, mercados=mercados)
    precio = caso.ejecutar("papa", "minimarket_sopocachi")
    assert precio.procedencia is Procedencia.ESTIMADO and precio.codigo_mercado == "minimarket_sopocachi"


def test_la_api_expone_lo_que_el_mapa_necesita():
    cliente = TestClient(app)
    mercados = cliente.get("/api/v1/mercados").json()
    assert mercados
    for m in mercados:
        assert {"macrodistrito", "codigo_padre", "nivel_precio", "latitud", "longitud"} <= set(m)
    comparar = cliente.get("/api/v1/precios/tomate/comparar").json()
    assert all(fila["nivel_precio"] in ("mayorista", "minorista") for fila in comparar)
    assert all(fila["precio"]["procedencia"] in ("observado", "estimado") for fila in comparar)
