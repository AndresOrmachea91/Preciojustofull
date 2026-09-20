#!/usr/bin/env python3
"""
Adaptador de entrada por línea de comandos: el recolector.

Es otro adaptador sobre los mismos puertos que usa la API. Lo ejecuta
GitHub Actions tres veces al día.

    python -m src.infraestructura.adaptadores.entrada.cli.recolectar                 # todo el catálogo, las dos fuentes
    python -m src.infraestructura.adaptadores.entrada.cli.recolectar --fuente diario
    python -m src.infraestructura.adaptadores.entrada.cli.recolectar --productos arroz_primera,papa_holandesa
    python -m src.infraestructura.adaptadores.entrada.cli.recolectar --disponibilidad

Los productos salen de datos/catalogo/productos.csv, que dice qué código
usa cada fuente para cada uno. Las observaciones se guardan con el código
del catálogo.

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
from pathlib import Path

from src.infraestructura.adaptadores.entrada.cli.sembrar import PRODUCTOS_POR_DEFECTO
from src.infraestructura.adaptadores.salida.catalogo.lector_csv import leer_mapeo_fuentes
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

# nombre en la línea de comandos -> (adaptador, columna del catálogo)
FUENTES = {"diario": (FuenteSiipDiario, "siip_diario"), "ipc": (FuenteSiipIpc, "siip_ipc")}


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


def _recolectar_fuente(repositorio, nombre_fuente: str, mapeo: dict[str, str], codigos: list[str]) -> tuple[int, int, int]:
    """Corre una fuente sobre sus productos. Devuelve (hechos nuevos, resueltos, fallidos)."""
    adaptador, _ = FUENTES[nombre_fuente]
    # El cliente registra CADA intento crudo contra el portal, incluidos los
    # que fallan y se reintentan. Sobre esos intentos se mide la
    # disponibilidad de la fuente original; sobre los productos resueltos,
    # la disponibilidad efectiva del sistema. La diferencia es lo que aporta
    # la arquitectura, y sin este registro sería invisible.
    cliente = ClienteResiliente(registrar_intento=repositorio.registrar_intento)
    fuente = adaptador(cliente=cliente, mapeo=mapeo)

    if not fuente.esta_disponible():
        log.error("%s no está disponible (cortacircuito abierto)", fuente.nombre)
        return 0, 0, len(codigos)

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
        log.info("[%s] %s (%s): %s hechos vistos, %s nuevos",
                 nombre_fuente, codigo, mapeo.get(codigo, codigo), len(observaciones), nuevas)

    resueltos = len(codigos) - fallidos
    log.info("[%s] %s hechos nuevos, %s de %s productos resueltos (%.1f%%).",
             nombre_fuente, total_nuevas, resueltos, len(codigos),
             100.0 * resueltos / len(codigos) if codigos else 0.0)
    return total_nuevas, resueltos, fallidos


def main() -> int:
    p = argparse.ArgumentParser(description="Recolector de fuentes de precios")
    p.add_argument("--fuente", choices=list(FUENTES), help="Una sola fuente; por defecto las dos")
    p.add_argument("--productos", help="Códigos del CATÁLOGO separados por coma; por defecto todo el catálogo")
    p.add_argument("--catalogo", type=Path, default=PRODUCTOS_POR_DEFECTO,
                   help=f"CSV de productos (por defecto {PRODUCTOS_POR_DEFECTO})")
    p.add_argument("--disponibilidad", action="store_true",
                   help="Muestra el resumen de disponibilidad por fuente")
    args = p.parse_args()

    repositorio = _abrir_repositorio()
    if repositorio is None:
        return 2

    if args.disponibilidad:
        return _mostrar_disponibilidad(repositorio)

    mapeos = leer_mapeo_fuentes(args.catalogo)
    pedidos = [c.strip() for c in args.productos.split(",") if c.strip()] if args.productos else None
    fuentes = [args.fuente] if args.fuente else list(FUENTES)

    total_nuevas = total_resueltos = total_fallidos = total_pedidos = 0
    for nombre in fuentes:
        _, columna = FUENTES[nombre]
        mapeo = mapeos[columna]
        codigos = [c for c in (pedidos or mapeo) if c in mapeo]
        if pedidos:
            for c in pedidos:
                if c not in mapeo:
                    log.warning("[%s] %s no tiene código en esta fuente; se omite", nombre, c)
        if not codigos:
            log.warning("[%s] ningún producto que recolectar", nombre)
            continue
        nuevas, resueltos, fallidos = _recolectar_fuente(repositorio, nombre, mapeo, codigos)
        total_nuevas += nuevas
        total_resueltos += resueltos
        total_fallidos += fallidos
        total_pedidos += len(codigos)

    if not total_pedidos:
        p.error("no hay productos que recolectar")
    log.info("Terminado. %s hechos nuevos, %s de %s productos resueltos.",
             total_nuevas, total_resueltos, total_pedidos)
    # Que fallen algunos productos no debe marcar la corrida como rota:
    # la degradación parcial es un comportamiento esperado del sistema.
    if total_fallidos == total_pedidos:
        return 1
    if total_nuevas == 0:
        log.warning("Las fuentes respondieron pero NO trajeron ningún hecho nuevo: el dato no avanzó.")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
