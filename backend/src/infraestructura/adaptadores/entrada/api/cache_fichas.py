"""
Memoria corta de las fichas de mercado, el directorio, las ofertas y los
precios referenciales (C134, C147).

Armar una ficha recorre los 45 productos: se guarda dos minutos. Todo lo
que cambia lo que muestra —un precio del casero, una oferta, una
confirmación, una planilla de campo— la olvida al instante, así quien
publica ve su cambio sin esperar.

Pasados los dos minutos nadie espera el recálculo: se entrega lo guardado
y se renueva por detrás, una sola vez aunque lleguen muchas visitas juntas.
Solo la primera visita después de arrancar (o de un cambio) paga la cuenta.
"""
from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import TypeVar

log = logging.getLogger(__name__)

VIGENCIA_SEGUNDOS = 120
# Más viejo que esto ya no se entrega ni mientras se renueva: se calcula de nuevo.
MAXIMO_SEGUNDOS = 1800
_guardadas: dict[str, tuple[float, object]] = {}
_renovando: set[str] = set()
_candado = threading.Lock()
# Cambia con cada olvido: una renovación que empezó antes no pisa lo nuevo con lo viejo.
_generacion = 0

T = TypeVar("T")


def recordar(clave: str, calcular: Callable[[], T]) -> T:
    with _candado:
        guardada = _guardadas.get(clave)
        if guardada is not None:
            edad = time.monotonic() - guardada[0]
            if edad < VIGENCIA_SEGUNDOS:
                return guardada[1]  # type: ignore[return-value]
            if edad < MAXIMO_SEGUNDOS:
                if clave not in _renovando:
                    _renovando.add(clave)
                    threading.Thread(target=_renovar, args=(clave, calcular, _generacion), daemon=True).start()
                return guardada[1]  # type: ignore[return-value]
        generacion = _generacion
    valor = calcular()
    with _candado:
        if generacion == _generacion:
            _guardadas[clave] = (time.monotonic(), valor)
    return valor


def _renovar(clave: str, calcular: Callable[[], object], generacion: int) -> None:
    try:
        valor = calcular()
        with _candado:
            if generacion == _generacion:
                _guardadas[clave] = (time.monotonic(), valor)
    except Exception:  # noqa: BLE001 — si falla, queda lo guardado y se reintenta en la próxima visita
        log.exception("No se pudo renovar %s", clave)
    finally:
        with _candado:
            _renovando.discard(clave)


def olvidar() -> None:
    global _generacion
    with _candado:
        _guardadas.clear()
        _generacion += 1
