#!/usr/bin/env python3
"""
Adaptador de entrada por línea de comandos: el recolector.

Es otro adaptador sobre los mismos puertos que usa la API. Lo ejecuta
GitHub Actions tres veces al día.

    python -m src.infraestructura.adaptadores.entrada.cli.recolectar --fuente diario --producto 5
    python -m src.infraestructura.adaptadores.entrada.cli.recolectar --fuente diario --productos 5,12,30
    python -m src.infraestructura.adaptadores.entrada.cli.recolectar --disponibilidad

Sin BASE_DATOS_URL configurada avisa y no guarda nada: es preferible
fallar ruidosamente antes que perder días de serie en silencio.

Códigos de salida:
    0  entró al menos un hecho nuevo
    1  todos los productos fallaron
    2  configuración o fuente indisponible
    3  la fuente respondió pero no trajo NI UN hecho nuevo. Para la tesis
       es una corrida fallida: el dato no avanzó. Se distingue de 0 para
       que la falta de datos nuevos sea visible en GitHub y no se
       confunda con éxito.
"""
from __future__ import annotations

import sys
import logging
import argparse

from src.infraestructura.adaptadores.salida.fuentes.cliente_resiliente import ClienteResiliente
from src.infraestructura.adaptadores.salida.fuentes.siip_diario import FuenteSiipDiario
from src.infraestructura.adaptadores.salida.fuentes.siip_ipc import FuenteSiipIpc
from src.infraestructura.adaptadores.salida.persistencia.repositorios import ObservacionesPostgres
from src.infraestructura.adaptadores.salida.persistencia.sesion import (
    crear_esquema, crear_motor, fabrica_sesiones,
)
from src.configuracion import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("recolector")

FUENTES = {"diario": FuenteSiipDiario, "ipc": FuenteSiipIpc}


def _abrir_repositorio() -> ObservacionesPostgres | None:
    if not config.base_datos_url:
        log.error(
            "BASE_DATOS_URL no está configurada. El recolector no va a guardar nada "
            "y el día se pierde: la ventana diaria del SIIP no se puede recuperar."
        )
        return None
    motor = crear_motor(config.base_datos_url)
    crear_esquema(motor)
    return ObservacionesPostgres(fabrica_sesiones(motor))


def _mostrar_disponibilidad(repositorio: ObservacionesPostgres) -> int:
    filas = repositorio.disponibilidad()
    if not filas:
        print("Todavía no hay intentos registrados.")
    else:
        print("\n1. DISPONIBILIDAD DE LA FUENTE: intentos crudos contra cada portal (incluye reintentos).")
        print("   Mide si el servidor responde. No dice nada del dato.")
        print(f"\n{'FUENTE':<26}{'INTENTOS':>10}{'ÉXITOS':>9}{'%':>8}{'MS':>9}")
        print("-" * 62)
        for f in filas:
            print(f"{f['fuente']:<26}{f['intentos']:>10}{f['exitosos']:>9}"
                  f"{f['porcentaje']:>7}%{f['ms_promedio']:>9}")

    avance = repositorio.avance_del_dato()
    print("\n2. AVANCE DEL DATO: corridas que trajeron al menos un hecho NUEVO.")
    print("   Una corrida con 200 hechos ya conocidos y 0 nuevos cuenta como fallida.")
    if not avance:
        print("   Todavía no hay corridas registradas.")
        return 0
    print(f"\n{'FUENTE':<26}{'CORRIDAS':>9}{'C/NUEVO':>9}{'%':>8}{'VISTOS':>9}{'NUEVOS':>8}  ÚLTIMO HECHO NUEVO")
    print("-" * 92)
    for f in avance:
        ultimo = f["ultimo_nuevo"].strftime("%Y-%m-%d %H:%M") if f["ultimo_nuevo"] else "nunca"
        print(f"{f['fuente']:<26}{f['corridas']:>9}{f['con_dato_nuevo']:>9}{f['porcentaje']:>7}%"
              f"{f['vistos']:>9}{f['nuevos']:>8}  {ultimo}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Recolector de fuentes de precios")
    p.add_argument("--fuente", choices=list(FUENTES))
    p.add_argument("--producto", help="Un código de producto")
    p.add_argument("--productos", help="Varios códigos separados por coma")
    p.add_argument("--disponibilidad", action="store_true",
                   help="Muestra el resumen de disponibilidad por fuente")
    args = p.parse_args()

    repositorio = _abrir_repositorio()
    if repositorio is None:
        return 2

    if args.disponibilidad:
        return _mostrar_disponibilidad(repositorio)

    if not args.fuente or not (args.producto or args.productos):
        p.error("hacen falta --fuente y --producto (o --productos)")

    codigos = (
        [c.strip() for c in args.productos.split(",") if c.strip()]
        if args.productos else [args.producto]
    )

    # El cliente registra CADA intento crudo contra el portal, incluidos los
    # que fallan y se reintentan. Sobre esos intentos se mide la
    # disponibilidad de la fuente original; sobre los productos resueltos,
    # la disponibilidad efectiva del sistema. La diferencia es lo que aporta
    # la arquitectura, y sin este registro sería invisible.
    cliente = ClienteResiliente(registrar_intento=repositorio.registrar_intento)
    fuente = FUENTES[args.fuente](cliente=cliente)

    if not fuente.esta_disponible():
        log.error("%s no está disponible (cortacircuito abierto)", fuente.nombre)
        return 2

    total_nuevas = fallidos = 0
    for codigo in codigos:
        try:
            observaciones = fuente.recolectar(codigo)
        except Exception as ex:
            log.warning("Producto %s falló: %s", codigo, ex)
            fallidos += 1
            continue

        # "nuevas" son HECHOS nuevos por clave natural, no filas insertadas.
        # La serie histórica completa viene en cada respuesta del SIIP (no
        # hay parámetro de rango), así que verla otra vez no cuenta.
        nuevas = repositorio.guardar_varias(observaciones)
        repositorio.registrar_corrida(fuente.nombre, codigo, len(observaciones), nuevas)
        total_nuevas += nuevas
        log.info("Producto %s: %s hechos vistos, %s nuevos",
                 codigo, len(observaciones), nuevas)

    resueltos = len(codigos) - fallidos
    log.info("Terminado. %s hechos nuevos, %s de %s productos resueltos.",
             total_nuevas, resueltos, len(codigos))
    log.info("Disponibilidad de la fuente en esta corrida: %.1f%%",
             100.0 * resueltos / len(codigos))
    # Que fallen algunos productos no debe marcar la corrida como rota:
    # la degradación parcial es un comportamiento esperado del sistema.
    if fallidos == len(codigos):
        return 1
    if total_nuevas == 0:
        log.warning("La fuente respondió pero NO trajo ningún hecho nuevo: el dato no avanzó.")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
