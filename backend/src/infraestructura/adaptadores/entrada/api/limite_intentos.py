"""
Límite de intentos (C131): frena a quien prueba contraseñas, crea cuentas
en masa o llena de correos a alguien con "recuperar contraseña".

Vive en el borde HTTP porque es una defensa del canal, no una regla del
negocio. Cuenta en memoria del proceso, con ventana deslizante: si se
reinicia la app, la cuenta vuelve a cero, lo que para un solo servidor
alcanza. Cada regla mira la IP y, cuando la hay, la cuenta (correo): así
ni una IP prueba mil correos ni mil IPs prueban un correo.

Detrás de Caddy la IP real llega en X-Forwarded-For; uvicorn la toma con
--proxy-headers (ver Dockerfile).
"""
from __future__ import annotations

import math
import threading
import time
from collections import deque
from dataclasses import dataclass

from fastapi import HTTPException, Request, status

from src.configuracion import config


@dataclass(frozen=True, slots=True)
class Regla:
    maximo: int
    ventana_segundos: int


# Ingresar: 10 intentos por IP y 5 por correo cada 15 minutos.
# Registro: 5 cuentas por IP por hora. Recuperar: 5 por IP y 3 por correo por hora.
REGLAS = {
    "ingresar:ip": Regla(10, 15 * 60),
    "ingresar:correo": Regla(5, 15 * 60),
    "registro:ip": Regla(5, 60 * 60),
    "recuperar:ip": Regla(5, 60 * 60),
    "recuperar:correo": Regla(3, 60 * 60),
}


class LimitadorIntentos:
    def __init__(self, reglas: dict[str, Regla] | None = None, reloj=time.monotonic):
        self._reglas = reglas or REGLAS
        self._reloj = reloj
        self._intentos: dict[str, deque[float]] = {}
        self._candado = threading.Lock()

    def registrar(self, regla: str, clave: str) -> None:
        """Cuenta un intento; si se pasó del límite, responde 429 con cuánto esperar."""
        r = self._reglas[regla]
        ahora = self._reloj()
        llave = f"{regla}|{clave.lower()}"
        with self._candado:
            cola = self._intentos.setdefault(llave, deque())
            while cola and ahora - cola[0] >= r.ventana_segundos:
                cola.popleft()
            if len(cola) >= r.maximo:
                espera = math.ceil(r.ventana_segundos - (ahora - cola[0]))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Demasiados intentos. Vuelva a probar en {max(1, math.ceil(espera / 60))} minuto(s).",
                    headers={"Retry-After": str(espera)},
                )
            cola.append(ahora)
            if len(self._intentos) > 50_000:   # que la memoria no crezca sin fin
                self._olvidar_vencidos(ahora)

    def olvidar(self, regla: str, clave: str) -> None:
        """Tras un ingreso correcto, los fallos anteriores de esa cuenta ya no cuentan."""
        with self._candado:
            self._intentos.pop(f"{regla}|{clave.lower()}", None)

    def _olvidar_vencidos(self, ahora: float) -> None:
        for llave in list(self._intentos):
            regla = self._reglas[llave.split("|", 1)[0]]
            cola = self._intentos[llave]
            if not cola or ahora - cola[-1] >= regla.ventana_segundos:
                del self._intentos[llave]


limitador = LimitadorIntentos()


def ip_de(peticion: Request) -> str:
    return peticion.client.host if peticion.client else "desconocida"


def contar(regla: str, clave: str) -> None:
    if config.limite_intentos_activo:
        limitador.registrar(regla, clave)
