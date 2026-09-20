from datetime import datetime, timezone

import pytest

from src.infraestructura.adaptadores.salida.memoria.repositorios import datos_de_ejemplo
from src.dominio.modelo import Fuente, NivelPrecio, Observacion
from src.dominio.valor import Dinero, Periodo, Unidad


@pytest.fixture
def repositorios():
    return datos_de_ejemplo()


@pytest.fixture
def hacer_observacion():
    def _hacer(monto, unidad="KILO", fuente=Fuente.MEDIOS, reputacion=1.0,
               producto="tomate", mercado="rodriguez"):
        return Observacion(
            fuente=fuente,
            nivel=NivelPrecio.MINORISTA,
            codigo_producto=producto,
            codigo_mercado=mercado,
            periodo=Periodo(2026, 8, 15),
            precio=Dinero(monto, Unidad(unidad)),
            capturada_en=datetime.now(timezone.utc),
            reputacion_informante=reputacion,
        )
    return _hacer

