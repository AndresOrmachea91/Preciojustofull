import os

# Las pruebas NUNCA usan la base de backend/.env: esa es la de producción.
# Las variables de entorno mandan sobre el archivo, así que esto fuerza los
# repositorios en memoria igual que en la integración continua. Va antes de
# cualquier import de src, porque la configuración se lee al importarla.
os.environ["BASE_DATOS_URL"] = ""
os.environ["JWT_SECRETO"] = "secreto-de-pruebas-que-no-sirve-en-produccion-0123456789"
os.environ["ADMIN_INICIAL_CORREO"] = ""
os.environ["ADMIN_INICIAL_CONTRASENA"] = ""
# Las pruebas ingresan muchas veces seguidas desde la misma "IP": el límite
# de intentos se prueba aparte (test_limite_intentos.py), encendiéndolo.
os.environ["LIMITE_INTENTOS_ACTIVO"] = "false"

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

