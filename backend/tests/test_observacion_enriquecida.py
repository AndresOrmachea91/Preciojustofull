"""
Una observación tiene que poder compararse con otra: variedad, cantidad,
fecha de observación (distinta de la de captura), tipo de precio y
evidencia. Y las 271 observaciones históricas, que no traen nada de eso,
tienen que cargar sin fallar y sin mentir.
"""
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import text

from src.dominio.excepciones import UnidadDesconocida
from src.dominio.modelo import Fuente, NivelPrecio, Observacion
from src.dominio.valor import VARIEDAD_DESCONOCIDA, Dinero, Periodo, TipoPrecio, Unidad, UnidadCanonica
from src.infraestructura.adaptadores.salida.persistencia.repositorios import ObservacionesPostgres
from src.infraestructura.adaptadores.salida.persistencia.sesion import (
    crear_esquema, crear_motor, fabrica_sesiones,
)

AHORA = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)


def _obs(monto=10.0, unidad="KILO", **extra):
    base = dict(
        fuente=Fuente.CAMPO, nivel=NivelPrecio.MINORISTA, codigo_producto="arroz",
        codigo_mercado="rodriguez", periodo=Periodo(2026, 9, 18),
        precio=Dinero(monto, Unidad(unidad)), capturada_en=AHORA,
    )
    return Observacion(**{**base, **extra})


# --- los campos nuevos ----------------------------------------------------

def test_los_marcadores_por_defecto_son_explicitos_no_none():
    o = _obs()
    assert o.variedad == VARIEDAD_DESCONOCIDA and not o.variedad_conocida
    assert o.tipo_precio is TipoPrecio.DESCONOCIDO
    assert o.fecha_observacion is None and not o.fecha_observacion_conocida
    assert o.cantidad == 1.0
    assert o.evidencia is None


def test_la_variedad_no_puede_ir_vacia():
    with pytest.raises(ValueError, match="desconocida"):
        _obs(variedad="  ")


def test_la_fecha_de_observacion_es_distinta_de_la_de_captura():
    o = _obs(fecha_observacion=date(2026, 9, 15))
    assert o.fecha_observacion == date(2026, 9, 15)
    assert o.capturada_en.date() == date(2026, 9, 19)
    assert o.fecha_observacion_conocida


def test_la_cantidad_entra_en_la_conversion_canonica():
    """Bs 75,87 por 760 gramos son Bs 99,83 el kilo."""
    o = _obs(75.87, "GRAMO(s)", cantidad=760)
    assert o.precio_canonico() == pytest.approx(75.87 / 760 / 0.001, rel=1e-6)
    assert o.unidad_canonica is UnidadCanonica.KILOGRAMO
    assert o.precio.monto == 75.87 and o.precio.unidad.texto == "GRAMO(s)"   # el par original sigue ahí


def test_la_cantidad_debe_ser_positiva():
    with pytest.raises(ValueError, match="cantidad"):
        _obs(cantidad=0)


def test_una_unidad_sin_peso_declarado_se_conserva_marcada_como_no_convertible():
    o = _obs(12.0, "BOLSA")
    assert not o.es_convertible
    assert o.unidad_canonica is None
    assert o.precio.unidad.texto == "BOLSA"     # no se pierde ni se adivina
    with pytest.raises(UnidadDesconocida):
        o.precio_canonico()


def test_el_atado_es_convertible_a_su_propia_unidad_no_a_kilo():
    o = _obs(5.0, "atado")
    assert o.es_convertible and o.unidad_canonica is UnidadCanonica.ATADO


# --- todo sobrevive al guardado --------------------------------------------

def _repo():
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    return motor, ObservacionesPostgres(fabrica_sesiones(motor))


def test_los_campos_nuevos_sobreviven_al_guardado():
    _, repo = _repo()
    repo.guardar_varias([_obs(
        75.87, "GRAMO(s)", cantidad=760, variedad="entera", fecha_observacion=date(2026, 9, 15),
        tipo_precio=TipoPrecio.PAGADO, evidencia="ticket 4471",
    )])

    (r,) = repo.buscar("arroz", "rodriguez")

    assert (r.cantidad, r.variedad, r.fecha_observacion) == (760, "entera", date(2026, 9, 15))
    assert r.tipo_precio is TipoPrecio.PAGADO and r.evidencia == "ticket 4471"
    assert r.precio_canonico() == pytest.approx(75.87 / 0.76)


def test_una_no_convertible_se_guarda_con_canonico_nulo():
    motor, repo = _repo()
    repo.guardar_varias([_obs(12.0, "BOLSA")])

    with motor.connect() as c:
        fila = c.execute(text("SELECT unidad_texto, precio_canonico, unidad_canonica FROM observacion_precio")).one()
    assert fila == ("BOLSA", None, None)
    assert not repo.buscar("arroz")[0].es_convertible


# --- migración de lo histórico ---------------------------------------------

ESQUEMA_VIEJO = """
CREATE TABLE observacion_precio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fuente VARCHAR(32) NOT NULL, nivel VARCHAR(16) NOT NULL,
    codigo_producto VARCHAR(64) NOT NULL, codigo_mercado VARCHAR(64) NOT NULL,
    anio INTEGER NOT NULL, mes INTEGER, dia INTEGER,
    precio_monto FLOAT NOT NULL, unidad_texto VARCHAR(64) NOT NULL,
    precio_canonico FLOAT, unidad_canonica VARCHAR(8),
    reputacion_informante FLOAT NOT NULL DEFAULT 1.0,
    capturada_en DATETIME NOT NULL,
    CONSTRAINT uq_observacion_unica UNIQUE (fuente, codigo_producto, codigo_mercado, anio, mes, dia)
)
"""


def _base_vieja_con_271_observaciones():
    """Como quedó la base en producción antes de este cambio: sin ámbito ni campos nuevos."""
    motor = crear_motor("sqlite://")
    with motor.begin() as c:
        c.execute(text(ESQUEMA_VIEJO))
        filas = []
        # 200 diarias del SIIP (con día), 50 mensuales del IPC (sin día), 21 de campo
        for i in range(200):
            filas.append(("siip_diario", "mayorista", "5", "la_paz", 2026, 1 + i // 28, 1 + i % 28, 565.0, "qq."))
        for i in range(50):
            filas.append(("siip_ipc", "minorista", "111030102", "la_paz", 2022 + i // 12, 1 + i % 12, None, 6.8, "LIBRA(s)"))
        for i in range(21):
            filas.append(("campo", "minorista", "tomate", "rodriguez", 2026, 9, 1 + i, 6.5, "LIBRA"))
        c.execute(text(
            "INSERT INTO observacion_precio (fuente, nivel, codigo_producto, codigo_mercado, anio, mes, dia, "
            "precio_monto, unidad_texto, capturada_en) VALUES (:f, :n, :p, :m, :a, :me, :d, :mo, :u, :c)"
        ), [dict(f=f, n=n, p=p, m=m, a=a, me=me, d=d, mo=mo, u=u, c=AHORA.isoformat()) for f, n, p, m, a, me, d, mo, u in filas])
    return motor


def test_las_271_observaciones_historicas_cargan_sin_fallar_ni_mentir():
    motor = _base_vieja_con_271_observaciones()

    crear_esquema(motor)   # la migración mínima: agrega columnas, rellena lo honesto
    repo = ObservacionesPostgres(fabrica_sesiones(motor))
    diario = repo.buscar("5")
    ipc = repo.buscar("111030102")
    campo = repo.buscar("tomate")

    assert len(diario) + len(ipc) + len(campo) == 271
    todas = diario + ipc + campo
    # Marcadores explícitos, no valores plausibles.
    assert all(o.variedad == VARIEDAD_DESCONOCIDA for o in todas)
    assert all(o.tipo_precio is TipoPrecio.DESCONOCIDO for o in todas)
    assert all(o.cantidad == 1.0 and o.evidencia is None for o in todas)
    # La fecha se recuperó del dato donde el dato la trae (hay día)...
    assert all(o.fecha_observacion == date(o.periodo.anio, o.periodo.mes, o.periodo.dia) for o in diario + campo)
    # ...y quedó nula donde no, sin rellenar con la captura.
    assert all(o.fecha_observacion is None for o in ipc)
    assert not any(o.fecha_observacion == o.capturada_en.date() for o in ipc)
    # Y el ámbito se dedujo de la fuente: el SIIP publica por ciudad.
    assert all(o.es_referencia_de_ciudad for o in diario + ipc)
    assert not any(o.es_referencia_de_ciudad for o in campo)


def test_la_migracion_es_idempotente():
    motor = _base_vieja_con_271_observaciones()
    crear_esquema(motor)
    crear_esquema(motor)
    with motor.connect() as c:
        assert c.execute(text("SELECT count(*) FROM observacion_precio")).scalar() == 271
