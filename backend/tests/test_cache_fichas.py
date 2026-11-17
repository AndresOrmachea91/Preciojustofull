"""
La memoria corta de la API (C147): entrega lo guardado sin hacer esperar a
nadie, lo renueva por detrás y lo olvida en cuanto algo cambia.
"""
import threading
import time

import pytest

from src.infraestructura.adaptadores.entrada.api import cache_fichas as cache


@pytest.fixture(autouse=True)
def _limpia():
    cache.olvidar()
    yield
    cache.olvidar()


def test_guarda_el_valor_y_no_recalcula_dentro_de_la_vigencia():
    veces = []
    for _ in range(3):
        assert cache.recordar("a", lambda: veces.append(1) or len(veces)) == 1
    assert len(veces) == 1


def test_olvidar_obliga_a_calcular_de_nuevo():
    assert cache.recordar("a", lambda: "viejo") == "viejo"
    cache.olvidar()
    assert cache.recordar("a", lambda: "nuevo") == "nuevo"


def test_vencido_entrega_lo_guardado_y_renueva_por_detras(monkeypatch):
    assert cache.recordar("a", lambda: "viejo") == "viejo"
    monkeypatch.setattr(cache, "VIGENCIA_SEGUNDOS", 0)
    listo = threading.Event()

    def nuevo():
        listo.set()
        return "nuevo"

    # Quien llega con el dato vencido no espera: recibe el guardado.
    assert cache.recordar("a", nuevo) == "viejo"
    assert listo.wait(2)
    monkeypatch.setattr(cache, "VIGENCIA_SEGUNDOS", 120)
    for _ in range(100):
        if cache.recordar("a", lambda: "otro") == "nuevo":
            break
        time.sleep(0.01)
    assert cache.recordar("a", lambda: "otro") == "nuevo"


def test_una_renovacion_que_empezo_antes_de_un_cambio_no_pisa_lo_nuevo(monkeypatch):
    assert cache.recordar("a", lambda: "viejo") == "viejo"
    monkeypatch.setattr(cache, "VIGENCIA_SEGUNDOS", 0)
    empezo, seguir = threading.Event(), threading.Event()

    def lento():
        empezo.set()
        seguir.wait(2)
        return "calculado antes del cambio"

    cache.recordar("a", lento)
    assert empezo.wait(2)
    monkeypatch.setattr(cache, "VIGENCIA_SEGUNDOS", 120)
    cache.olvidar()                      # alguien publicó una oferta
    assert cache.recordar("a", lambda: "con el cambio") == "con el cambio"
    seguir.set()
    time.sleep(0.05)
    assert cache.recordar("a", lambda: "otro") == "con el cambio"


def test_demasiado_viejo_se_calcula_de_nuevo(monkeypatch):
    assert cache.recordar("a", lambda: "viejo") == "viejo"
    monkeypatch.setattr(cache, "VIGENCIA_SEGUNDOS", 0)
    monkeypatch.setattr(cache, "MAXIMO_SEGUNDOS", 0)
    assert cache.recordar("a", lambda: "nuevo") == "nuevo"
