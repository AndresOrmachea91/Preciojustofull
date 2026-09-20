#!/usr/bin/env python3
"""
Adaptador de entrada por línea de comandos: la siembra del catálogo.

    python -m src.infraestructura.adaptadores.entrada.cli.sembrar
    python -m src.infraestructura.adaptadores.entrada.cli.sembrar --dry-run
    python -m src.infraestructura.adaptadores.entrada.cli.sembrar --archivo otro.csv --productos otro_p.csv

Siembra los dos catálogos: puntos de venta y productos. Es idempotente:
correrlo dos veces deja la base igual que correrlo una. Inserta lo que
falta y actualiza lo que cambió, por código; nunca borra, porque las
observaciones ya apuntan a esos códigos.
"""
from __future__ import annotations

import sys
import logging
import argparse
from pathlib import Path

from src.aplicacion.casos_uso.sembrar_catalogo import ResumenSiembra, SembrarCatalogo
from src.dominio.excepciones import JerarquiaInvalida
from src.infraestructura.adaptadores.salida.catalogo.lector_csv import (
    CatalogoCorrupto, leer_productos, leer_puntos_venta,
)
from src.infraestructura.adaptadores.salida.persistencia.repositorios import (
    MercadosPostgres, ProductosPostgres,
)
from src.infraestructura.adaptadores.salida.persistencia.sesion import (
    crear_esquema, crear_motor, fabrica_sesiones,
)
from src.configuracion import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sembrar")

CARPETA_CATALOGO = Path(__file__).resolve().parents[5] / "datos" / "catalogo"
CATALOGO_POR_DEFECTO = CARPETA_CATALOGO / "puntos_venta.csv"
PRODUCTOS_POR_DEFECTO = CARPETA_CATALOGO / "productos.csv"


def _imprimir(resumen: ResumenSiembra, que: str) -> None:
    modo = "SIMULACIÓN (no se escribió nada)" if resumen.simulado else "Siembra aplicada"
    verbo = "insertaría" if resumen.simulado else "insertados"
    print(f"\n{modo}: {resumen.total} {que} en el catálogo")
    print(f"  {verbo:<12} {len(resumen.insertados):>4}")
    print(f"  {'actualizaría' if resumen.simulado else 'actualizados':<12} {len(resumen.actualizados):>4}")
    print(f"  {'sin cambios':<12} {len(resumen.sin_cambios):>4}")
    for etiqueta, codigos in (("nuevos", resumen.insertados), ("cambiados", resumen.actualizados)):
        if codigos:
            print(f"  {etiqueta}: {', '.join(codigos)}")


def main() -> int:
    p = argparse.ArgumentParser(description="Siembra el catálogo de puntos de venta")
    p.add_argument("--archivo", type=Path, default=CATALOGO_POR_DEFECTO,
                   help=f"CSV de puntos de venta (por defecto {CATALOGO_POR_DEFECTO})")
    p.add_argument("--productos", type=Path, default=PRODUCTOS_POR_DEFECTO,
                   help=f"CSV de productos (por defecto {PRODUCTOS_POR_DEFECTO})")
    p.add_argument("--dry-run", action="store_true",
                   help="Reporta qué haría sin tocar la base")
    args = p.parse_args()

    if not config.base_datos_url:
        log.error("BASE_DATOS_URL no está configurada: no hay dónde sembrar.")
        return 2

    try:
        puntos = leer_puntos_venta(args.archivo)
        productos = leer_productos(args.productos)
    except (CatalogoCorrupto, FileNotFoundError) as e:
        log.error("No se pudo leer el catálogo: %s", e)
        return 2
    log.info("Catálogo leído: %s puntos de venta y %s productos", len(puntos), len(productos))

    motor = crear_motor(config.base_datos_url)
    crear_esquema(motor)
    fabrica = fabrica_sesiones(motor)
    caso = SembrarCatalogo(MercadosPostgres(fabrica), ProductosPostgres(fabrica))

    try:
        resumen_puntos = caso.sembrar_puntos_venta(puntos, simular=args.dry_run)
    except JerarquiaInvalida as e:
        for infraccion in e.infracciones:
            log.error("Jerarquía: %s", infraccion)
        return 2
    resumen_productos = caso.sembrar_productos(productos, simular=args.dry_run)

    _imprimir(resumen_puntos, "puntos de venta")
    _imprimir(resumen_productos, "productos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
