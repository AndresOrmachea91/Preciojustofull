"""
Los precios referenciales de La Paz (C144): todos los productos con el
precio de la ciudad, sin el ajuste de ningún lugar, y sin pedir sesión.
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from src.aplicacion.casos_uso.precios.precios_referenciales import PreciosReferenciales
from src.dominio.modelo import Categoria, Fuente, Mercado, NivelPrecio, Observacion, Producto, TipoPuntoVenta
from src.dominio.servicio.motor_fusion import MotorFusion
from src.dominio.valor import Ambito, Dinero, Periodo, Unidad
from src.infraestructura.adaptadores.salida.memoria.repositorios import (
    MercadosEnMemoria, ObservacionesEnMemoria, ProductosEnMemoria,
)

from src.infraestructura.adaptadores.entrada.api import dependencias
from src.infraestructura.adaptadores.entrada.api.main import app

API = "/api/v1"


@pytest.fixture
def cliente():
    dependencias._repositorios.cache_clear()
    with TestClient(app) as c:
        yield c
    dependencias._repositorios.cache_clear()


def test_la_api_lista_todos_los_productos_sin_pedir_sesion(cliente):
    r = cliente.get(f"{API}/precios/referencia")
    assert r.status_code == 200, r.text
    productos = cliente.get(f"{API}/productos").json()
    assert {f["producto"]["codigo"] for f in r.json()} == {p["codigo"] for p in productos}


def _referencia(producto: str, monto: float, nivel: NivelPrecio) -> Observacion:
    return Observacion(
        fuente=Fuente.SIIP_IPC, nivel=nivel, codigo_producto=producto, codigo_mercado=None, ciudad="la_paz",
        ambito=Ambito.CIUDAD, periodo=Periodo(2026, 10), precio=Dinero(monto, Unidad("KILO")),
        capturada_en=datetime(2026, 11, 1, tzinfo=timezone.utc),
    )


def test_es_la_ciudad_sin_el_ajuste_de_ningun_lugar():
    productos = ProductosEnMemoria([Producto("papa", "Papa", categoria=Categoria.TUBERCULO),
                                    Producto("arroz", "Arroz", categoria=Categoria.ABARROTE)])
    # El único mercado está 20 % arriba: la referencia no se entera.
    mercados = MercadosEnMemoria([Mercado("lanza", "Mercado Lanza", TipoPuntoVenta.MERCADO, "Centro",
                                          factor_mercado=1.2)])
    observaciones = ObservacionesEnMemoria([_referencia("papa", 6.0, NivelPrecio.MINORISTA)])

    filas = {r.producto.codigo: r for r in PreciosReferenciales(productos, mercados, observaciones,
                                                                  MotorFusion()).ejecutar()}

    assert filas["papa"].consumidor.rango.centro == pytest.approx(6.0)
    assert filas["papa"].mayorista is None, "no hay un lugar mayorista: no se inventa ese nivel"
    assert filas["arroz"].consumidor is None, "sin referencia de la ciudad, el renglón queda sin precio"


def test_viene_ordenada_por_categoria_y_nombre(cliente):
    filas = cliente.get(f"{API}/precios/referencia").json()
    claves = [(f["producto"]["categoria"], f["producto"]["nombre"]) for f in filas]
    assert claves == sorted(claves)
