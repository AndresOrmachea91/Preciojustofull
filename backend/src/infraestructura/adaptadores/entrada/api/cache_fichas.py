"""
Memoria corta de las fichas de mercado y del directorio (C134).

Armar una ficha recorre los 45 productos: se guarda dos minutos. Todo lo
que cambia lo que muestra —un precio del casero, una oferta, una
confirmación, una planilla de campo— la olvida al instante, así quien
publica ve su cambio sin esperar.
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import TypeVar

VIGENCIA_SEGUNDOS = 120
_guardadas: dict[str, tuple[float, object]] = {}
_candado = threading.Lock()

T = TypeVar("T")


def recordar(clave: str, calcular: Callable[[], T]) -> T:
    with _candado:
        guardada = _guardadas.get(clave)
        if guardada is not None and time.monotonic() - guardada[0] < VIGENCIA_SEGUNDOS:
            return guardada[1]  # type: ignore[return-value]
    valor = calcular()
    with _candado:
        _guardadas[clave] = (time.monotonic(), valor)
    return valor


def olvidar() -> None:
    with _candado:
        _guardadas.clear()
