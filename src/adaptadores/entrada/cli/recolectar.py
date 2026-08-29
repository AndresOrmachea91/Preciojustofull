#!/usr/bin/env python3
"""
Adaptador de entrada por línea de comandos: el recolector.

Es otro adaptador sobre los mismos puertos que usa la API. Lo ejecuta
GitHub Actions tres veces al día.

    python -m src.adaptadores.entrada.cli.recolectar --fuente diario --producto 5
    python -m src.adaptadores.entrada.cli.recolectar --fuente diario --productos 5,12,30
    python -m src.adaptadores.entrada.cli.recolectar --disponibilidad

Sin BASE_DATOS_URL configurada avisa y no guarda nada: es preferible
fallar ruidosamente antes que perder días de serie en silencio.
"""
from __future__ import annotations

import sys
import logging
import argparse

from src.adaptadores.salida.fuentes.cliente_resiliente import ClienteResiliente
from src.adaptadores.salida.fuentes.siip_diario import FuenteSiipDiario
from src.adaptadores.salida.fuentes.siip_ipc import FuenteSiipIpc
from src.adaptadores.salida.persistencia.repositorios import ObservacionesPostgres
from src.adaptadores.salida.persistencia.sesion import (
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
        return 0
    print("\nIntentos CRUDOS contra cada portal (incluye reintentos):")
    print(f"\n{'FUENTE':<26}{'INTENTOS':>10}{'ÉXITOS':>9}{'%':>8}{'MS':>9}")
    print("-" * 62)
    for f in filas:
        print(f"{f['fuente']:<26}{f['intentos']:>10}{f['exitosos']:>9}"
              f"{f['porcentaje']:>7}%{f['ms_promedio']:>9}")
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

        nuevas = repositorio.guardar_varias(observaciones)
        total_nuevas += nuevas
        log.info("Producto %s: %s observaciones, %s nuevas",
                 codigo, len(observaciones), nuevas)

    resueltos = len(codigos) - fallidos
    log.info("Terminado. %s observaciones nuevas, %s de %s productos resueltos.",
             total_nuevas, resueltos, len(codigos))
    log.info("Disponibilidad efectiva de esta corrida: %.1f%%",
             100.0 * resueltos / len(codigos))
    # Que fallen algunos productos no debe marcar la corrida como rota:
    # la degradación parcial es un comportamiento esperado del sistema.
    return 1 if fallidos == len(codigos) else 0


if __name__ == "__main__":
    sys.exit(main())
