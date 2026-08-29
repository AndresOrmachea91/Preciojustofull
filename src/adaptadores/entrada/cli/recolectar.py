#!/usr/bin/env python3
"""
Adaptador de entrada por línea de comandos: el recolector.

Es otro adaptador sobre los mismos puertos que usa la API. Lo ejecuta
GitHub Actions todas las noches.

    python -m src.adaptadores.entrada.cli.recolectar --fuente diario --producto 5
"""
from __future__ import annotations
import sys
import logging
import argparse

from src.adaptadores.salida.fuentes.siip_diario import FuenteSiipDiario
from src.adaptadores.salida.fuentes.siip_ipc import FuenteSiipIpc
from src.adaptadores.salida.memoria.repositorios import ObservacionesEnMemoria

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("recolector")

FUENTES = {"diario": FuenteSiipDiario, "ipc": FuenteSiipIpc}


def main() -> int:
    p = argparse.ArgumentParser(description="Recolector de fuentes de precios")
    p.add_argument("--fuente", choices=list(FUENTES), required=True)
    p.add_argument("--producto", required=True, help="Código del producto en esa fuente")
    args = p.parse_args()

    fuente = FUENTES[args.fuente]()
    if not fuente.esta_disponible():
        log.error("%s no está disponible (cortacircuito abierto)", fuente.nombre)
        return 2

    # TODO: reemplazar por el repositorio de PostgreSQL. El resto no cambia.
    repositorio = ObservacionesEnMemoria()

    try:
        observaciones = fuente.recolectar(args.producto)
    except Exception as ex:
        log.error("Falló la recolección de %s: %s", fuente.nombre, ex)
        return 1

    guardadas = repositorio.guardar_varias(observaciones)
    log.info("%s: %s observaciones guardadas", fuente.nombre, guardadas)
    return 0


if __name__ == "__main__":
    sys.exit(main())

