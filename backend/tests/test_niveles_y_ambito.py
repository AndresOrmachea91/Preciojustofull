"""
Las fuentes del SIIP no miden lo mismo que un levantamiento en un puesto.

El diario cotiza MAYORISTA (arroz por quintal, carne en gancho) y el IPC
cotiza CONSUMIDOR FINAL (el mismo arroz por libra). Además las dos publican
UN valor por ciudad, no por mercado. Estas pruebas verifican que el camino
fuente -> observación -> motor respete las dos cosas.
"""
from datetime import datetime, timezone

import pytest

from src.dominio.excepciones import NivelesNoComparables, ReferenciaNoEsMedicion, UnidadDesconocida
from src.dominio.modelo import Fuente, Mercado, NivelPrecio, Observacion, TipoPuntoVenta
from src.dominio.servicio.motor_fusion import MotorFusion
from src.dominio.valor import Ambito, Dinero, NivelConfianza, Periodo, Unidad, UnidadCanonica
from src.infraestructura.adaptadores.salida.fuentes.cliente_resiliente import ClienteResiliente
from src.infraestructura.adaptadores.salida.fuentes.siip_diario import FuenteSiipDiario
from src.infraestructura.adaptadores.salida.fuentes.siip_ipc import FuenteSiipIpc
from src.infraestructura.adaptadores.salida.memoria.repositorios import ObservacionesEnMemoria
from src.infraestructura.adaptadores.salida.persistencia.repositorios import ObservacionesPostgres
from src.infraestructura.adaptadores.salida.persistencia.sesion import (
    crear_esquema, crear_motor, fabrica_sesiones,
)

AHORA = datetime.now(timezone.utc)


def _obs(fuente, nivel=None, ambito=None, monto=10.0, unidad="KILO", mercado="la_paz"):
    return Observacion(
        fuente=fuente,
        nivel=nivel or fuente.nivel_fijo or NivelPrecio.MINORISTA,
        codigo_producto="arroz", codigo_mercado=mercado,
        periodo=Periodo(2026, 7, 15), precio=Dinero(monto, Unidad(unidad)),
        capturada_en=AHORA, ambito=ambito or fuente.ambito,
    )


# --- la fuente declara su nivel y su ámbito --------------------------------

def test_cada_fuente_del_siip_declara_su_nivel_y_su_ambito():
    assert Fuente.SIIP_DIARIO.nivel_fijo is NivelPrecio.MAYORISTA
    assert Fuente.SIIP_IPC.nivel_fijo is NivelPrecio.MINORISTA
    assert Fuente.SIIP_DIARIO.ambito is Fuente.SIIP_IPC.ambito is Ambito.CIUDAD
    # Campo y ciudadano miden donde están parados: sin nivel fijo, en un local.
    assert Fuente.CAMPO.nivel_fijo is None
    assert Fuente.CAMPO.ambito is Ambito.PUNTO_VENTA


def test_una_observacion_no_puede_contradecir_el_nivel_de_su_fuente():
    with pytest.raises(ValueError, match="solo cotiza mayorista"):
        _obs(Fuente.SIIP_DIARIO, nivel=NivelPrecio.MINORISTA)
    with pytest.raises(ValueError, match="solo cotiza minorista"):
        _obs(Fuente.SIIP_IPC, nivel=NivelPrecio.MAYORISTA)


def test_una_observacion_del_siip_no_puede_fingir_ser_medicion_local():
    with pytest.raises(ValueError, match="publica por ciudad"):
        _obs(Fuente.SIIP_IPC, ambito=Ambito.PUNTO_VENTA, mercado="rodriguez")


# --- los adaptadores producen lo que la fuente declara ----------------------

HTML_DIARIO = """
<table id="tabla_precios"><thead>
<tr><th rowspan=2>Ciudad</th><th rowspan=2>Unidad</th><th colspan="2">2026</th><th colspan="2">2026-JUL</th></tr>
<tr><td>MAY</td><td>JUN</td><th>1</th><th>2</th></tr>
</thead>
<tr><td>La Paz</td><td>qq.</td><td>575,00</td><td>571,67</td><td>567,50</td><td>565,00</td></tr>
<tr><td>Cochabamba</td><td>CAJA</td><td>12,00</td><td>12,00</td><td>12,00</td><td>12,00</td></tr>
<tr><td>Promedio</td><td>qq.</td><td>1,00</td><td>1,00</td><td>1,00</td><td>1,00</td></tr>
</table>
"""


def test_el_diario_produce_mayorista_de_ambito_ciudad_y_rechaza_lo_que_no_convierte():
    fuente = FuenteSiipDiario(cliente=ClienteResiliente())
    obs = fuente._parsear(HTML_DIARIO, "5")

    assert obs and all(o.nivel is NivelPrecio.MAYORISTA for o in obs)
    assert all(o.ambito is Ambito.CIUDAD for o in obs)
    assert {o.codigo_mercado for o in obs} == {"la_paz"}
    assert all(o.precio.unidad.texto == "qq." for o in obs)
    # "CAJA" sin peso no es un precio por kilo: se rechaza con motivo.
    assert len(fuente.rechazadas) == 1
    assert fuente.rechazadas[0][0] == "5/Cochabamba"
    assert "CAJA" in fuente.rechazadas[0][1]


def test_el_ipc_produce_minorista_de_ambito_ciudad():
    datos = {
        "eje_x": ["JUN-2026", "JUL-2026"],
        "data": [
            {"cantidad": "1.00", "unidad": "LIBRA(s)", "ciudad": "LA PAZ", "valor": [6.96, 6.82]},
            {"cantidad": "1.00", "unidad": "CUARTILLA", "ciudad": "POTOSI", "valor": [41.0, 41.47]},
            {"cantidad": "1.00", "unidad": "MANOJO", "ciudad": "BENI", "valor": [1.0, 1.0]},
        ],
    }
    fuente = FuenteSiipIpc(cliente=ClienteResiliente())
    obs = fuente._parsear(datos, "111030102")

    assert len(obs) == 4
    assert all(o.nivel is NivelPrecio.MINORISTA and o.ambito is Ambito.CIUDAD for o in obs)
    assert {o.codigo_mercado for o in obs} == {"la_paz", "potosi"}
    assert fuente.rechazadas == [("111030102/BENI", str(UnidadDesconocida("MANOJO")))]


# --- el motor no mezcla niveles ni confunde referencia con medición ---------

def test_el_motor_no_presenta_una_referencia_de_ciudad_como_precio_de_mercado():
    with pytest.raises(ReferenciaNoEsMedicion):
        MotorFusion().consolidar([_obs(Fuente.SIIP_IPC, monto=6.82, unidad="LIBRA")])


def test_diario_e_ipc_no_se_fusionan_entre_si():
    """Son la misma ciudad y el mismo producto, pero niveles distintos."""
    rodriguez = Mercado("rodriguez", "Rodríguez", TipoPuntoVenta.MERCADO, "Cotahuma")
    diario = _obs(Fuente.SIIP_DIARIO, monto=565.0, unidad="qq.")
    ipc = _obs(Fuente.SIIP_IPC, monto=6.82, unidad="LIBRA")

    with pytest.raises(NivelesNoComparables):
        MotorFusion().estimar_desde_ciudad([diario, ipc], rodriguez)


def test_la_referencia_mayorista_no_estima_un_puesto_minorista_ni_al_reves():
    motor = MotorFusion()
    puesto = Mercado("rodriguez", "Rodríguez", TipoPuntoVenta.MERCADO, "Cotahuma")
    makro = Mercado("makro", "Makro", TipoPuntoVenta.MAYORISTA, "Centro")

    with pytest.raises(NivelesNoComparables):
        motor.estimar_desde_ciudad([_obs(Fuente.SIIP_DIARIO, unidad="qq.")], puesto)
    with pytest.raises(NivelesNoComparables):
        motor.estimar_desde_ciudad([_obs(Fuente.SIIP_IPC, unidad="LIBRA")], makro)


def test_la_referencia_de_ciudad_estima_un_local_via_factor_mercado():
    """Bs 6,90 la libra en La Paz, en un minimarket que va 1,20 sobre la ciudad."""
    mini = Mercado("mini", "Mini", TipoPuntoVenta.MINIMARKET, "Sopocachi", factor_mercado=1.20)
    referencia = [_obs(Fuente.SIIP_IPC, monto=6.90, unidad="LIBRA")]

    estimado = MotorFusion().estimar_desde_ciudad(referencia, mini)

    assert estimado.codigo_mercado == "mini"
    assert estimado.unidad is UnidadCanonica.KILOGRAMO
    assert abs(estimado.rango.centro - (6.90 / 0.46) * 1.20) < 0.5
    assert estimado.confianza.peso <= NivelConfianza.MEDIO.peso
    assert any("Estimado desde la referencia de ciudad la_paz" in c for c in estimado.conflictos)


def test_una_medicion_local_si_se_consolida_como_siempre():
    local = [_obs(Fuente.CAMPO, mercado="rodriguez"), _obs(Fuente.CIUDADANO, mercado="rodriguez", monto=11.0)]
    assert MotorFusion().consolidar(local).observaciones_usadas == 2


# --- el ámbito sobrevive al guardado -----------------------------------------

@pytest.fixture(params=["memoria", "sqlalchemy"])
def observaciones(request):
    if request.param == "memoria":
        return ObservacionesEnMemoria()
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    return ObservacionesPostgres(fabrica_sesiones(motor))


def test_el_ambito_ciudad_sobrevive_al_guardado(observaciones):
    observaciones.guardar_varias([_obs(Fuente.SIIP_IPC, unidad="LIBRA")])

    (recuperada,) = observaciones.buscar("arroz", "la_paz")

    assert recuperada.ambito is Ambito.CIUDAD
    assert recuperada.nivel is NivelPrecio.MINORISTA
