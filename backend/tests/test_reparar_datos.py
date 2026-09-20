"""
El script de reparación sobre una base como la que dejó el recolector
viejo: esquema sin las columnas nuevas, hechos repetidos con el mismo
valor, '46 Kg.' sin unidad canónica, 'la_paz' como si fuera un mercado y
el SIIP con ámbito punto_venta.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from src.dominio.valor import Ambito, TipoPrecio
from src.infraestructura.adaptadores.entrada.cli.reparar_datos import GrupoConValoresDistintos, reparar
from src.infraestructura.adaptadores.salida.persistencia.repositorios import ObservacionesPostgres
from src.infraestructura.adaptadores.salida.persistencia.sesion import crear_motor, fabrica_sesiones

T0 = datetime(2026, 8, 29, 7, 0, tzinfo=timezone.utc)

ESQUEMA_VIEJO = """
CREATE TABLE observacion_precio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fuente VARCHAR(32) NOT NULL, nivel VARCHAR(16) NOT NULL,
    codigo_producto VARCHAR(64) NOT NULL, codigo_mercado VARCHAR(64),
    anio INTEGER NOT NULL, mes INTEGER, dia INTEGER,
    precio_monto FLOAT NOT NULL, unidad_texto VARCHAR(64) NOT NULL,
    precio_canonico FLOAT, unidad_canonica VARCHAR(8),
    reputacion_informante FLOAT NOT NULL DEFAULT 1.0,
    ambito VARCHAR(16) NOT NULL DEFAULT 'punto_venta',
    capturada_en DATETIME NOT NULL
)
"""

# Los hechos: (producto, mes, dia, monto, unidad, canonica_vieja)
HECHOS = [
    ("5", 6, None, 575.0, "qq.", "kg"),
    ("5", 7, 1, 567.5, "qq.", "kg"),
    ("5", 7, 2, 565.0, "qq.", "kg"),
    ("12", 6, None, 335.0, "46 Kg.", None),     # el parser viejo no la resolvía
    ("12", 7, 1, 335.0, "46 Kg.", None),
    ("30", 6, None, 39.5, "Kg.", "kg"),
]


def _base_como_neon(repeticiones=3, con_revision=False):
    motor = crear_motor("sqlite://")
    with motor.begin() as c:
        c.execute(text(ESQUEMA_VIEJO))
        filas = []
        for corrida in range(repeticiones):
            for producto, mes, dia, monto, unidad, canonica in HECHOS:
                if dia is not None and corrida > 0:
                    continue   # las diarias sí las frenaba la restricción vieja
                filas.append(dict(
                    p=producto, me=mes, d=dia, mo=monto, u=unidad,
                    pc=(monto / 46) if canonica else None, uc=canonica,
                    c=(T0 + timedelta(hours=8 * corrida)).isoformat(),
                ))
        if con_revision:
            filas.append(dict(p="30", me=6, d=None, mo=41.0, u="Kg.", pc=41.0, uc="kg",
                              c=(T0 + timedelta(days=5)).isoformat()))
        c.execute(text(
            "INSERT INTO observacion_precio (fuente, nivel, codigo_producto, codigo_mercado, anio, mes, dia, "
            "precio_monto, unidad_texto, precio_canonico, unidad_canonica, ambito, capturada_en) VALUES "
            "('siip_diario', 'mayorista', :p, 'la_paz', 2026, :me, :d, :mo, :u, :pc, :uc, 'punto_venta', :c)"
        ), filas)
    return motor


def test_la_simulacion_no_escribe_nada():
    motor = _base_como_neon()
    antes = motor.connect().execute(text("SELECT count(*) FROM observacion_precio")).scalar()

    informe = reparar(motor, simular=True)

    despues = motor.connect().execute(text("SELECT count(*) FROM observacion_precio")).scalar()
    assert antes == despues == 12
    assert informe["4_dedup"] == {"filas": 12, "hechos": 6, "borradas": 6}
    assert informe["3_parseo"]["corregidas"] == 12          # tipo_precio y fecha cambian en todas
    assert informe["1_catalogo"]["puntos_insertados"] == 88
    assert motor.connect().execute(text("SELECT count(*) FROM mercado")).scalar() == 0


def test_la_reparacion_deja_un_hecho_por_fila_con_la_primera_captura():
    motor = _base_como_neon()

    informe = reparar(motor, simular=False)

    v = informe["verificacion"]
    assert v["total"] == 6
    assert v["por_ambito"] == {"ciudad": 6}
    assert v["sin_unidad_canonica"] == 0
    assert v["productos_que_fallan_al_cargar"] == 0 and v["cargadas_como_entidad"] == 6
    assert (v["mercados_en_catalogo"], v["productos_en_catalogo"]) == (88, 45)

    with motor.connect() as c:
        harina = c.execute(text(
            "SELECT unidad_canonica, precio_canonico, unidad_texto, precio_monto, ciudad, codigo_mercado, "
            "capturada_en, ultima_captura_en, tipo_precio, fecha_observacion "
            "FROM observacion_precio WHERE codigo_producto = 'harina_blanca' AND dia IS NULL"
        )).one()
    assert (harina.unidad_canonica, harina.precio_canonico) == ("kg", pytest.approx(335.0 / 46))
    assert (harina.unidad_texto, harina.precio_monto) == ("46 Kg.", 335.0)     # el original no se toca
    assert (harina.ciudad, harina.codigo_mercado) == ("la_paz", None)
    assert harina.capturada_en.startswith("2026-08-29T07")                       # la PRIMERA captura
    assert harina.ultima_captura_en > harina.capturada_en
    assert harina.tipo_precio == TipoPrecio.COTIZADO.value and harina.fecha_observacion is None

    repo = ObservacionesPostgres(fabrica_sesiones(motor))
    (diaria,) = [o for o in repo.buscar("arroz_primera", ciudad="la_paz") if o.periodo.dia == 2]
    assert informe["2b_producto"]["remapeados"] == [("5", "arroz_primera"), ("12", "harina_blanca"), ("30", "pacu")]
    assert informe["2b_producto"]["sin_mapeo"] == []
    assert diaria.ambito is Ambito.CIUDAD and diaria.fecha_observacion.isoformat() == "2026-07-02"


def test_la_reparacion_es_idempotente():
    motor = _base_como_neon()
    reparar(motor, simular=False)
    segunda = reparar(motor, simular=False)
    assert segunda["4_dedup"]["borradas"] == 0 and segunda["3_parseo"]["corregidas"] == 0
    assert segunda["verificacion"]["total"] == 6


def test_si_un_hecho_tiene_dos_valores_para_y_no_borra_nada():
    motor = _base_como_neon(con_revision=True)
    with pytest.raises(GrupoConValoresDistintos):
        reparar(motor, simular=False)
    assert motor.connect().execute(text("SELECT count(*) FROM observacion_precio")).scalar() == 13


def test_despues_de_reparar_el_indice_rechaza_duplicados():
    from sqlalchemy.exc import IntegrityError
    motor = _base_como_neon()
    reparar(motor, simular=False)
    with pytest.raises(IntegrityError), motor.begin() as c:
        c.execute(text(
            "INSERT INTO observacion_precio (fuente, nivel, codigo_producto, ciudad, anio, mes, dia, precio_monto, "
            "unidad_texto, cantidad, ambito, capturada_en) VALUES "
            "('siip_diario','mayorista','pacu', 'la_paz', 2026, 6, NULL, 39.5, 'Kg.', 1.0, 'ciudad', '2026-09-20')"
        ))
