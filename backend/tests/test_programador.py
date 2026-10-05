"""El programador del recolector: una corrida por día, a la hora de Bolivia, con reintentos."""
from datetime import datetime, time, timedelta, timezone

from src.infraestructura.adaptadores.entrada.cli.programador import (
    DISPONIBILIDAD, RECOLECTOR, correr_el_dia, leer_hora, proxima_corrida,
)

ONCE = time(11, 0)


def test_la_hora_es_la_de_bolivia_no_la_del_servidor():
    # 13:00 UTC son las 09:00 en La Paz: todavía no llegaron las 11:00.
    siguiente = proxima_corrida(datetime(2026, 10, 5, 13, 0, tzinfo=timezone.utc), ONCE)
    assert siguiente.astimezone(timezone.utc) == datetime(2026, 10, 5, 15, 0, tzinfo=timezone.utc)


def test_si_ya_paso_la_hora_es_manana():
    siguiente = proxima_corrida(datetime(2026, 10, 5, 16, 0, tzinfo=timezone.utc), ONCE)
    assert siguiente.astimezone(timezone.utc) == datetime(2026, 10, 6, 15, 0, tzinfo=timezone.utc)


def test_justo_a_la_hora_no_se_repite_la_corrida():
    siguiente = proxima_corrida(datetime(2026, 10, 5, 15, 0, tzinfo=timezone.utc), ONCE)
    assert siguiente.date().isoformat() == "2026-10-06"


def test_leer_hora():
    assert leer_hora(" 07:30 ") == time(7, 30)


def _simular(codigos):
    llamadas, esperas = [], []

    def ejecutar(comando):
        llamadas.append(comando)
        return codigos.pop(0) if comando == RECOLECTOR else 0

    return llamadas, esperas, ejecutar


def test_si_sale_bien_no_reintenta():
    llamadas, esperas, ejecutar = _simular([0])
    assert correr_el_dia(3, timedelta(minutes=60), ejecutar, esperas.append) == 0
    assert llamadas == [RECOLECTOR, DISPONIBILIDAD]
    assert esperas == []


def test_reintenta_el_mismo_dia_hasta_que_entra_algo():
    llamadas, esperas, ejecutar = _simular([2, 3, 0])
    assert correr_el_dia(3, timedelta(minutes=60), ejecutar, esperas.append) == 0
    assert llamadas.count(RECOLECTOR) == 3
    assert esperas == [3600, 3600]


def test_agotados_los_reintentos_devuelve_el_ultimo_codigo():
    llamadas, esperas, ejecutar = _simular([1, 1, 3])
    assert correr_el_dia(2, timedelta(minutes=30), ejecutar, esperas.append) == 3
    assert llamadas.count(RECOLECTOR) == 3
    assert esperas == [1800, 1800]
