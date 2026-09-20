"""
La clave natural identifica al HECHO observado, no a la captura. Dos
capturas del mismo hecho son una fila; el mismo hecho con otro valor es
una revisión y se conserva aparte; la primera captura no se pisa.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from src.dominio.modelo import Fuente, NivelPrecio, Observacion
from src.dominio.valor import Dinero, Periodo, Unidad
from src.infraestructura.adaptadores.salida.memoria.repositorios import ObservacionesEnMemoria
from src.infraestructura.adaptadores.salida.persistencia.repositorios import ObservacionesPostgres
from src.infraestructura.adaptadores.salida.persistencia.sesion import (
    asegurar_indice_clave_natural, crear_esquema, crear_motor, fabrica_sesiones,
)

T0 = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)


def _obs(monto=6.82, unidad="LIBRA(s)", cantidad=1.0, capturada=T0, fuente=Fuente.SIIP_IPC,
         periodo=Periodo(2026, 8), producto="111030102", lugar="la_paz"):
    es_ciudad = fuente.ambito.value == "ciudad"
    return Observacion(
        fuente=fuente, nivel=fuente.nivel_fijo or NivelPrecio.MINORISTA,
        codigo_producto=producto, codigo_mercado=None if es_ciudad else lugar,
        ciudad=lugar if es_ciudad else None, periodo=periodo,
        precio=Dinero(monto, Unidad(unidad)), capturada_en=capturada, ambito=fuente.ambito,
        cantidad=cantidad,
    )


def test_la_clave_natural_es_del_hecho_y_no_de_la_captura():
    hoy, manana = _obs(capturada=T0), _obs(capturada=T0 + timedelta(days=1))
    assert hoy.clave_natural == manana.clave_natural
    # Otro valor NO cambia la clave: es el mismo hecho, revisado.
    assert _obs(monto=7.0).clave_natural == hoy.clave_natural
    # Otra presentación sí: el IPC publica kilo y unidad para el mismo mes.
    assert _obs(unidad="KILO(s)").clave_natural != hoy.clave_natural
    assert _obs(cantidad=25).clave_natural != hoy.clave_natural
    # Otro período, otro lugar, otra fuente: otros hechos.
    assert _obs(periodo=Periodo(2026, 7)).clave_natural != hoy.clave_natural
    assert _obs(lugar="potosi").clave_natural != hoy.clave_natural


def _sqlalchemy():
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    asegurar_indice_clave_natural(motor)
    return motor, ObservacionesPostgres(fabrica_sesiones(motor))


@pytest.fixture(params=["memoria", "sqlalchemy"])
def repo(request):
    return ObservacionesEnMemoria() if request.param == "memoria" else _sqlalchemy()[1]


def test_insertar_el_mismo_hecho_n_veces_deja_una_fila(repo):
    hecho = _obs()
    nuevas = [repo.guardar_varias([_obs(capturada=T0 + timedelta(hours=8 * i))]) for i in range(57)]
    assert nuevas[0] == 1 and sum(nuevas[1:]) == 0
    assert len(repo.buscar(hecho.codigo_producto)) == 1


def test_el_mismo_hecho_repetido_dentro_de_un_lote_entra_una_vez(repo):
    assert repo.guardar_varias([_obs(), _obs(), _obs()]) == 1


def test_el_mismo_hecho_con_otro_valor_es_una_revision_y_deja_dos_filas(repo):
    repo.guardar_varias([_obs(monto=6.82)])
    nuevas = repo.guardar_varias([_obs(monto=6.90, capturada=T0 + timedelta(days=1))])

    assert nuevas == 1
    assert sorted(o.precio.monto for o in repo.buscar("111030102")) == [6.82, 6.90]


def test_la_revision_queda_marcada_y_la_primera_captura_no_se_pisa():
    motor, repo = _sqlalchemy()
    repo.guardar_varias([_obs(monto=6.82, capturada=T0)])
    repo.guardar_varias([_obs(monto=6.82, capturada=T0 + timedelta(days=1))])   # visto de nuevo
    repo.guardar_varias([_obs(monto=6.90, capturada=T0 + timedelta(days=2))])   # revisado

    with motor.connect() as c:
        filas = c.execute(text(
            "SELECT id, precio_monto, capturada_en, ultima_captura_en, revisa_a "
            "FROM observacion_precio ORDER BY id"
        )).all()

    assert len(filas) == 2
    original, revision = filas
    assert original.precio_monto == 6.82 and original.revisa_a is None
    assert original.capturada_en.startswith("2026-09-01")            # la PRIMERA captura
    assert original.ultima_captura_en > original.capturada_en          # y que se volvió a ver, aparte
    assert revision.precio_monto == 6.90 and revision.revisa_a == original.id


def test_dos_presentaciones_del_mismo_mes_no_se_pisan(repo):
    """El IPC publica kilo y unidad para plátano en el mismo mes: son dos hechos."""
    nuevas = repo.guardar_varias([_obs(5.5, "KILO(s)"), _obs(13.21, "UNIDAD(es)", cantidad=25)])
    assert nuevas == 2


def test_las_mensuales_sin_dia_tambien_se_deduplican():
    """La falla de origen: en PostgreSQL dos NULL de mes/dia nunca eran iguales."""
    motor, repo = _sqlalchemy()
    repo.guardar_varias([_obs(periodo=Periodo(2026, 8))])
    repo.guardar_varias([_obs(periodo=Periodo(2026, 8))])
    with motor.connect() as c:
        assert c.execute(text("SELECT count(*) FROM observacion_precio")).scalar() == 1


def test_el_indice_unico_rechaza_lo_que_el_upsert_no_vio():
    """Última línea de defensa: aunque alguien inserte a mano, el hecho no se duplica."""
    from sqlalchemy.exc import IntegrityError
    motor, repo = _sqlalchemy()
    repo.guardar_varias([_obs()])
    with pytest.raises(IntegrityError), motor.begin() as c:
        c.execute(text(
            "INSERT INTO observacion_precio (fuente, nivel, codigo_producto, ciudad, anio, mes, dia, "
            "precio_monto, unidad_texto, cantidad, ambito, capturada_en) VALUES "
            "('siip_ipc','minorista','111030102','la_paz',2026,8,NULL,6.82,'LIBRA(s)',1.0,'ciudad','2026-09-02')"
        ))
