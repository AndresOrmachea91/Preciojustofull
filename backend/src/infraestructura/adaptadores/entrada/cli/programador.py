#!/usr/bin/env python3
"""
Adaptador de entrada: el programador del recolector, UNA corrida por día.

    python -m src.infraestructura.adaptadores.entrada.cli.programador

Es el proceso que vive en el contenedor "recolector". Duerme hasta la hora
configurada (hora de Bolivia), corre el recolector de siempre y vuelve a
dormir hasta el día siguiente. No reemplaza al recolector: lo invoca, igual
que antes lo invocaba GitHub Actions.

Una corrida por día, pero con reintentos DENTRO del mismo día: si el SIIP
no responde (salida 1 o 2) o responde sin ningún hecho nuevo (salida 3), se
vuelve a intentar más tarde. El bloque diario del SIIP es una ventana
móvil: un día que no se recolecta no se recupera después. Como la
recolección es idempotente, reintentar nunca duplica datos.

Configuración (variables de entorno):
    RECOLECCION_HORA        "HH:MM" en hora de Bolivia (por defecto 11:00)
    RECOLECCION_REINTENTOS  intentos extra el mismo día (por defecto 3)
    RECOLECCION_ESPERA_MIN  minutos entre intentos (por defecto 60)
    RECOLECTAR_AL_INICIAR   "1" para correr una vez apenas arranca
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from datetime import datetime, time as hora, timedelta, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("programador")

# Bolivia no tiene horario de verano: UTC-4 todo el año. Un desfase fijo
# evita depender de la base de zonas horarias de la imagen.
BOLIVIA = timezone(timedelta(hours=-4), "BOT")

RECOLECTOR = [sys.executable, "-m", "src.infraestructura.adaptadores.entrada.cli.recolectar"]
DISPONIBILIDAD = RECOLECTOR + ["--disponibilidad"]
TRAMO_SEGUNDOS = 300

SIGNIFICADO = {
    0: "entraron hechos nuevos",
    1: "fallaron todos los productos",
    2: "configuración o fuente indisponible",
    3: "la fuente respondió pero no trajo ningún hecho nuevo",
}


def leer_hora(texto: str) -> hora:
    horas, minutos = texto.strip().split(":")
    return hora(int(horas), int(minutos))


def proxima_corrida(ahora: datetime, a_las: hora) -> datetime:
    """La próxima vez que el reloj de Bolivia marque `a_las`, estrictamente después de `ahora`."""
    local = ahora.astimezone(BOLIVIA)
    candidata = local.replace(hour=a_las.hour, minute=a_las.minute, second=0, microsecond=0)
    if candidata <= local:
        candidata += timedelta(days=1)
    return candidata


def correr_el_dia(reintentos: int, espera: timedelta, ejecutar=subprocess.call, dormir=time.sleep) -> int:
    """Una corrida con sus reintentos. Devuelve el código de la última."""
    codigo = 2
    for intento in range(1, reintentos + 2):
        log.info("Recolección: intento %s de %s", intento, reintentos + 1)
        codigo = ejecutar(RECOLECTOR)
        log.info("Salida %s: %s", codigo, SIGNIFICADO.get(codigo, "desconocida"))
        if codigo == 0:
            break
        if intento <= reintentos:
            log.info("Se reintenta en %s minutos", int(espera.total_seconds() // 60))
            dormir(espera.total_seconds())
    ejecutar(DISPONIBILIDAD)
    return codigo


def main() -> int:
    a_las = leer_hora(os.environ.get("RECOLECCION_HORA", "11:00"))
    reintentos = int(os.environ.get("RECOLECCION_REINTENTOS", "3"))
    espera = timedelta(minutes=int(os.environ.get("RECOLECCION_ESPERA_MIN", "60")))

    if not os.environ.get("BASE_DATOS_URL"):
        log.error("Falta BASE_DATOS_URL: sin base no hay dónde guardar la serie.")
        return 2

    log.info("Programador listo: una recolección diaria a las %s (hora de Bolivia)", a_las.strftime("%H:%M"))
    if os.environ.get("RECOLECTAR_AL_INICIAR") == "1":
        correr_el_dia(reintentos, espera)

    while True:
        siguiente = proxima_corrida(datetime.now(timezone.utc), a_las)
        log.info("Próxima recolección: %s", siguiente.strftime("%Y-%m-%d %H:%M %Z"))
        # Se duerme en tramos cortos y se vuelve a mirar el reloj: si el equipo
        # estuvo suspendido a la hora de la corrida, se recolecta apenas
        # despierta (a lo sumo TRAMO_SEGUNDOS después), no al día siguiente.
        while (falta := (siguiente - datetime.now(timezone.utc)).total_seconds()) > 0:
            time.sleep(min(falta, TRAMO_SEGUNDOS))
        correr_el_dia(reintentos, espera)


if __name__ == "__main__":
    sys.exit(main())
