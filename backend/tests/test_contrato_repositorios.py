"""
Prueba de CONTRATO de los repositorios.

Este archivo es el que demuestra la arquitectura hexagonal mejor que
cualquier explicación: el mismo conjunto de casos se ejecuta contra los
dos adaptadores del puerto —el de memoria y el de SQLAlchemy— y ambos
tienen que comportarse igual.

Si mañana se agrega un tercer adaptador, se agrega a la lista de abajo y
queda verificado sin escribir una prueba más.

El adaptador de SQLAlchemy se prueba sobre SQLite en memoria: mismo código,
mismo esquema, sin levantar un servidor. Por eso corre en la integración
continua sin credenciales.
"""
from datetime import datetime, timezone

import pytest

from src.infraestructura.adaptadores.salida.memoria.repositorios import (
    MercadosEnMemoria, ObservacionesEnMemoria, ProductosEnMemoria,
)
from src.infraestructura.adaptadores.salida.persistencia.repositorios import (
    MercadosPostgres, ObservacionesPostgres, ProductosPostgres,
)
from src.infraestructura.adaptadores.salida.persistencia.sesion import (
    crear_esquema, crear_motor, fabrica_sesiones,
)
from src.dominio.modelo import (
    Categoria, Fuente, Mercado, NivelPrecio, Observacion, Producto, TipoPuntoVenta,
)
from src.dominio.valor import Dinero, Periodo, Unidad


def _sqlalchemy():
    motor = crear_motor("sqlite://")   # en memoria
    crear_esquema(motor)
    fabrica = fabrica_sesiones(motor)
    return ProductosPostgres(fabrica), MercadosPostgres(fabrica), ObservacionesPostgres(fabrica)


def _memoria():
    return ProductosEnMemoria(), MercadosEnMemoria(), ObservacionesEnMemoria()


@pytest.fixture(params=["memoria", "sqlalchemy"], ids=["memoria", "sqlalchemy"])
def repos(request):
    """Cada prueba de este archivo se ejecuta dos veces, una por adaptador."""
    return _memoria() if request.param == "memoria" else _sqlalchemy()


def _observacion(monto=10.0, unidad="KILO", fuente=Fuente.MEDIOS,
                 producto="tomate", mercado="rodriguez", dia=15, reputacion=1.0):
    return Observacion(
        fuente=fuente,
        nivel=NivelPrecio.MINORISTA,
        codigo_producto=producto,
        codigo_mercado=mercado,
        periodo=Periodo(2026, 8, dia),
        precio=Dinero(monto, Unidad(unidad)),
        capturada_en=datetime.now(timezone.utc),
        reputacion_informante=reputacion,
    )


# --- productos -----------------------------------------------------------

def test_guardar_y_recuperar_producto(repos):
    productos, _, _ = repos
    productos.guardar(Producto("tomate", "Tomate", Categoria.HORTALIZA, 5, "Valles"))

    recuperado = productos.obtener("tomate")

    assert recuperado is not None
    assert recuperado.nombre == "Tomate"
    assert recuperado.categoria is Categoria.HORTALIZA
    assert recuperado.es_perecedero is True


def test_producto_inexistente_devuelve_nada(repos):
    productos, _, _ = repos
    assert productos.obtener("no_existe") is None


def test_guardar_el_mismo_producto_dos_veces_lo_actualiza(repos):
    productos, _, _ = repos
    productos.guardar(Producto("papa", "Papa", Categoria.TUBERCULO))
    productos.guardar(Producto("papa", "Papa holandesa", Categoria.TUBERCULO))

    assert len(productos.listar()) == 1
    assert productos.obtener("papa").nombre == "Papa holandesa"


# --- mercados ------------------------------------------------------------

def test_guardar_y_filtrar_mercados_por_zona(repos):
    _, mercados, _ = repos
    mercados.guardar(Mercado("rodriguez", "Mercado Rodríguez", TipoPuntoVenta.MERCADO, "San Pedro"))
    mercados.guardar(Mercado("lanza", "Mercado Lanza", TipoPuntoVenta.MERCADO, "Centro"))

    assert len(mercados.listar()) == 2
    solo_centro = mercados.listar("Centro")
    assert len(solo_centro) == 1
    assert solo_centro[0].codigo == "lanza"


def test_el_tipo_de_punto_de_venta_sobrevive_al_guardado(repos):
    """
    Importa: de ese tipo depende si se publica un rango o un precio puntual.
    """
    _, mercados, _ = repos
    mercados.guardar(Mercado("mini", "Minimarket", TipoPuntoVenta.MINIMARKET, "Sopocachi"))

    recuperado = mercados.obtener("mini")
    assert recuperado.tipo is TipoPuntoVenta.MINIMARKET
    assert recuperado.publica_rango is False


# --- observaciones -------------------------------------------------------

def test_guardar_y_buscar_observaciones(repos):
    _, _, observaciones = repos
    observaciones.guardar_varias([_observacion(10.0), _observacion(12.0, dia=16)])

    encontradas = observaciones.buscar("tomate", "rodriguez")

    assert len(encontradas) == 2
    assert {o.precio.monto for o in encontradas} == {10.0, 12.0}


def test_la_unidad_original_se_conserva(repos):
    """
    No se guarda solo el valor normalizado: sin la unidad original no se
    podría auditar ni corregir un factor de conversión mal cargado.
    """
    _, _, observaciones = repos
    observaciones.guardar_varias([_observacion(80.0, unidad="ARROBA")])

    recuperada = observaciones.buscar("tomate")[0]

    assert recuperada.precio.unidad.texto == "ARROBA"
    assert recuperada.precio.monto == 80.0
    assert abs(recuperada.precio_canonico() - 80.0 / 11.5) < 0.01


def test_buscar_filtra_por_mercado(repos):
    _, _, observaciones = repos
    observaciones.guardar_varias([
        _observacion(10.0, mercado="rodriguez"),
        _observacion(11.0, mercado="lanza"),
    ])

    assert len(observaciones.buscar("tomate", "lanza")) == 1
    assert len(observaciones.buscar("tomate")) == 2


def test_buscar_filtra_por_periodo(repos):
    _, _, observaciones = repos
    observaciones.guardar_varias([_observacion(10.0, dia=15), _observacion(11.0, dia=16)])

    encontradas = observaciones.buscar("tomate", periodo=Periodo(2026, 8, 16))

    assert len(encontradas) == 1
    assert encontradas[0].precio.monto == 11.0


def test_guardar_lista_vacia_no_rompe(repos):
    _, _, observaciones = repos
    assert observaciones.guardar_varias([]) == 0


def test_producto_sin_observaciones_devuelve_lista_vacia(repos):
    _, _, observaciones = repos
    assert observaciones.buscar("no_existe") == []


# --- idempotencia (solo aplica al adaptador persistente) -----------------

def test_reejecutar_el_recolector_no_duplica_la_serie():
    """
    El recolector corre tres veces al día. Si cada corrida duplicara los
    datos, la serie quedaría inservible en una semana.

    Esta garantía la da la restricción de unicidad de la base, así que se
    prueba solo contra el adaptador persistente.
    """
    _, _, observaciones = _sqlalchemy()
    lote = [_observacion(10.0), _observacion(12.0, dia=16)]

    primera = observaciones.guardar_varias(lote)
    segunda = observaciones.guardar_varias(lote)

    assert primera == 2
    assert segunda == 0
    assert len(observaciones.buscar("tomate")) == 2


def test_se_registra_cada_intento_para_medir_disponibilidad():
    _, _, observaciones = _sqlalchemy()

    observaciones.registrar_intento("SIIP_DIARIO", "http://x", True, 240, "24 KB")
    observaciones.registrar_intento("SIIP_DIARIO", "http://x", False, 25000, "Timeout")
    observaciones.registrar_intento("SIIP_DIARIO", "http://x", True, 300, "24 KB")

    resumen = observaciones.disponibilidad()

    assert len(resumen) == 1
    assert resumen[0]["intentos"] == 3
    assert resumen[0]["exitosos"] == 2
    assert resumen[0]["porcentaje"] == 66.7


def test_el_avance_del_dato_distingue_corridas_con_y_sin_hechos_nuevos():
    """
    22 días de corridas "exitosas" sin un hecho nuevo pasaron desapercibidos
    porque solo se medía la respuesta HTTP. Esta métrica mide si el dato
    avanza: una corrida con 208 vistos y 0 nuevos es una corrida fallida.
    """
    _, _, observaciones = _sqlalchemy()

    observaciones.registrar_corrida("SIIP diario mayorista", "5", vistos=103, nuevos=103)
    observaciones.registrar_corrida("SIIP diario mayorista", "5", vistos=103, nuevos=0)
    observaciones.registrar_corrida("SIIP diario mayorista", "5", vistos=103, nuevos=0)

    (avance,) = observaciones.avance_del_dato()

    assert avance["corridas"] == 3
    assert avance["con_dato_nuevo"] == 1
    assert avance["porcentaje"] == 33.3
    assert avance["vistos"] == 309 and avance["nuevos"] == 103
    assert avance["ultimo_nuevo"] is not None
