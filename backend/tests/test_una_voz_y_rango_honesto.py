"""
C126 una voz por informante y C128 rango honesto.

Una persona que repite su precio no fabrica confianza: cinco reportes
suyos son UNA evidencia. Y un precio viejo o estimado se muestra con un
rango más ancho, sin mover su centro.
"""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

from src.dominio.modelo import Fuente, Mercado, NivelPrecio, Observacion, TipoPuntoVenta
from src.dominio.servicio.motor_fusion import MotorFusion
from src.dominio.servicio.rango_honesto import empatan, rango_honesto
from src.dominio.modelo.precio_consolidado import RangoPrecio
from src.dominio.valor import Dinero, NivelConfianza, Periodo, Unidad

AHORA = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)


def _obs(monto, informante=None, fuente=Fuente.CIUDADANO, dia=10, reputacion=0.5):
    return Observacion(
        fuente=fuente, nivel=NivelPrecio.MINORISTA, codigo_producto="papa",
        codigo_mercado="rodriguez", periodo=Periodo(2026, 10, dia),
        precio=Dinero(monto, Unidad("KILO")), capturada_en=AHORA + timedelta(days=dia - 10),
        fecha_observacion=date(2026, 10, dia), reputacion_informante=reputacion,
        informante=informante,
    )


def test_cinco_reportes_de_la_misma_persona_son_una_voz():
    obs = [_obs(8.0 + i * 0.01, informante="usuario:7") for i in range(5)]
    precio = MotorFusion().consolidar(obs)
    assert precio.voces == {"ciudadano": 1}
    # Una sola voz ciudadana: confianza BAJA, no ALTA por repetición.
    assert precio.confianza is NivelConfianza.BAJO


def test_dos_personas_distintas_si_son_dos_voces():
    precio = MotorFusion().consolidar([_obs(8.0, "usuario:7"), _obs(8.1, "usuario:9")])
    assert precio.voces == {"ciudadano": 2}
    assert precio.confianza is NivelConfianza.ALTO


def test_sin_informante_conocido_cada_observacion_cuenta_sola():
    precio = MotorFusion().consolidar([_obs(8.0), _obs(8.1)])
    assert precio.voces == {"ciudadano": 2}


def test_de_una_persona_vale_lo_ultimo_que_dijo():
    vendedor = [_obs(9.0, "usuario:3", Fuente.VENDEDOR, dia=2), _obs(7.0, "usuario:3", Fuente.VENDEDOR, dia=9)]
    precio = MotorFusion().consolidar(vendedor)
    assert precio.rango.centro == 7.0
    assert precio.observaciones_usadas == 2   # se conservan las dos; vota una


def test_una_persona_no_puede_expulsar_a_otra_como_atipica():
    # Tres reportes de A a 20 Bs contra uno de B a 8: si contaran tres veces,
    # B quedaría como atípico. Con una voz por informante son dos voces.
    obs = [_obs(20.0, "usuario:1"), _obs(20.0, "usuario:1"), _obs(20.0, "usuario:1"), _obs(8.0, "usuario:2")]
    precio = MotorFusion().consolidar(obs)
    assert precio.voces == {"ciudadano": 2}
    assert precio.rango.centro == 14.0


def test_estimado_lleva_el_factor_y_las_voces_de_la_ciudad():
    ipc = Observacion(
        fuente=Fuente.SIIP_IPC, nivel=NivelPrecio.MINORISTA, codigo_producto="papa",
        codigo_mercado=None, ciudad="la_paz", ambito=Fuente.SIIP_IPC.ambito,
        periodo=Periodo(2026, 9), precio=Dinero(10.0, Unidad("KILO")), capturada_en=AHORA,
    )
    lanza = Mercado("lanza", "Lanza", TipoPuntoVenta.MERCADO, "Centro", -16.5, -68.1, 1.06)
    precio = MotorFusion().estimar_desde_ciudad([ipc], lanza)
    assert precio.factor_mercado == 1.06
    assert precio.voces == {"siip_ipc": 1}


def test_rango_honesto_ensancha_por_antiguedad_sin_mover_el_centro():
    base = MotorFusion().consolidar([_obs(10.0, "usuario:1"), _obs(10.0, "usuario:2")])
    tres_semanas = rango_honesto(base, date(2026, 10, 31))
    assert tres_semanas.rango.centro == base.rango.centro
    assert tres_semanas.rango.amplitud > base.rango.amplitud
    assert tres_semanas.antiguedad_dias == 21
    assert tres_semanas.motivos_rango


def test_rango_honesto_tiene_tope_y_no_toca_un_dato_de_hoy():
    base = MotorFusion().consolidar([_obs(10.0, "usuario:1"), _obs(10.0, "usuario:2")])
    assert rango_honesto(base, date(2026, 10, 10)).rango == base.rango
    un_anio = rango_honesto(base, date(2027, 10, 10))
    mitad_extra = (un_anio.rango.amplitud - base.rango.amplitud) / 2
    assert abs(mitad_extra - 10.0 * 0.15) < 0.02


def test_un_estimado_siempre_suma_incertidumbre():
    base = replace(MotorFusion().consolidar([_obs(10.0, "usuario:1")]),
                   procedencia=MotorFusion().consolidar([_obs(10.0)]).procedencia.ESTIMADO)
    assert rango_honesto(base, date(2026, 10, 10)).rango.amplitud > base.rango.amplitud


def test_empate_cuando_la_diferencia_es_menor_que_el_error():
    assert empatan(RangoPrecio(9.0, 11.0), RangoPrecio(9.6, 10.6))
    assert not empatan(RangoPrecio(9.0, 10.0), RangoPrecio(12.0, 13.0))


def test_la_migracion_recupera_el_informante_de_la_evidencia(tmp_path):
    from sqlalchemy import text
    from src.infraestructura.adaptadores.salida.persistencia.sesion import crear_esquema, crear_motor

    motor = crear_motor(f"sqlite:///{tmp_path / 'voz.db'}")
    crear_esquema(motor)
    columnas = ("fuente, nivel, codigo_producto, codigo_mercado, anio, mes, dia, precio_monto, unidad_texto, "
                "cantidad, variedad, tipo_precio, reputacion_informante, ambito, capturada_en, creado_en, "
                "creado_por, eliminado, evidencia")
    with motor.begin() as c:
        c.execute(text(
            "INSERT INTO reporte_precio (id, codigo_producto, codigo_mercado, monto, unidad, id_autor, estado, "
            "creado_en, creado_por, eliminado) VALUES (4, 'papa', 'rodriguez', 8, 'KILO', 12, 'aprobado', "
            ":c, 'x', 0)"), {"c": AHORA})
        for fuente, evidencia in (("ciudadano", "reporte:4"), ("vendedor", "vendedor:31"), ("medios", None)):
            c.execute(text(
                f"INSERT INTO observacion_precio ({columnas}) VALUES (:f, 'minorista', 'papa', 'rodriguez', "
                "2026, 10, 1, 8, 'KILO', 1, 'desconocida', 'desconocido', 1, 'punto_venta', :c, :c, 'x', 0, :e)"
            ), {"f": fuente, "c": AHORA, "e": evidencia})

    crear_esquema(motor)

    with motor.connect() as c:
        filas = dict(c.execute(text("SELECT fuente, informante FROM observacion_precio")).all())
    assert filas == {"ciudadano": "usuario:12", "vendedor": "usuario:31", "medios": None}
