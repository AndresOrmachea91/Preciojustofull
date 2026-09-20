#!/usr/bin/env python3
"""
Reparación de los datos existentes, una sola vez, idempotente.

    python -m src.infraestructura.adaptadores.entrada.cli.reparar_datos            # simulación (por defecto)
    python -m src.infraestructura.adaptadores.entrada.cli.reparar_datos --aplicar  # escribe

Diagnóstico del 20 de septiembre de 2026 sobre Neon: 15.455 filas en
observacion_precio que son 271 hechos distintos repetidos ~57 veces, todos
con el mismo valor; 5.925 filas con '46 Kg.' sin unidad canónica; 208 del
SIIP con ámbito punto_venta; 'la_paz' como si fuera un mercado; catálogo
sin sembrar. Este script deja la base como la dejaría el código de hoy.

Orden, y no otro:
  1. Sembrar el catálogo (puntos de venta y productos).
  2. La ciudad a su campo: las filas del SIIP pasan a ámbito ciudad, con
     ciudad = lo que estaba en codigo_mercado y codigo_mercado = NULL.
     Y el producto pasa del código del SIIP ("5") al del catálogo
     ("arroz_primera"), que es con el que el recolector guarda desde ahora.
  3. Reprocesar el parseo con el parser actual: unidad canónica, precio
     canónico, tipo de precio, fecha de observación. precio_monto y
     unidad_texto no se tocan: son el dato original.
  4. Deduplicar por clave natural conservando la PRIMERA captura. Antes
     de borrar se verifica que cada grupo tenga un solo valor; si no, se
     PARA y se reporta, porque eso sería una revisión y no un duplicado.
  5. Crear el índice único del hecho observado.

Sin --aplicar no escribe nada y reporta qué haría. Correrlo primero así
es obligatorio. El respaldo es la rama respaldo-pre-migracion-2026-09-20.
"""
from __future__ import annotations

import sys
import logging
import argparse
from collections import defaultdict
from datetime import date

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from src.aplicacion.casos_uso.sembrar_catalogo import SembrarCatalogo
from src.dominio.modelo import Fuente
from src.dominio.valor import TipoPrecio, Unidad
from src.infraestructura.adaptadores.entrada.cli.sembrar import (
    CATALOGO_POR_DEFECTO, PRODUCTOS_POR_DEFECTO,
)
from src.infraestructura.adaptadores.salida.catalogo.lector_csv import (
    leer_mapeo_fuentes, leer_productos, leer_puntos_venta,
)
from src.infraestructura.adaptadores.salida.persistencia.repositorios import (
    MercadosPostgres, ObservacionesPostgres, ProductosPostgres,
)
from src.infraestructura.adaptadores.salida.persistencia.sesion import (
    asegurar_indice_clave_natural, crear_esquema, crear_motor, fabrica_sesiones,
)
from src.configuracion import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("reparar")

FUENTES_CIUDAD = tuple(f.value for f in Fuente if f.ambito.value == "ciudad")


class GrupoConValoresDistintos(RuntimeError):
    """Un hecho con más de un valor no es un duplicado: no se borra nada."""


# --- pasos --------------------------------------------------------------

def sembrar_catalogo(motor: Engine, simular: bool) -> dict:
    fabrica = fabrica_sesiones(motor)
    caso = SembrarCatalogo(MercadosPostgres(fabrica), ProductosPostgres(fabrica))
    puntos = caso.sembrar_puntos_venta(leer_puntos_venta(CATALOGO_POR_DEFECTO), simular=simular)
    productos = caso.sembrar_productos(leer_productos(PRODUCTOS_POR_DEFECTO), simular=simular)
    return {
        "puntos_insertados": len(puntos.insertados), "puntos_actualizados": len(puntos.actualizados),
        "productos_insertados": len(productos.insertados), "productos_actualizados": len(productos.actualizados),
    }


def ciudad_a_su_campo(c: Connection, simular: bool) -> int:
    """'la_paz' no es un mercado. Las filas del SIIP son de ámbito ciudad y la ciudad va en su campo."""
    fuentes = ", ".join(repr(f) for f in FUENTES_CIUDAD)
    filas = c.execute(text(
        "SELECT id, codigo_mercado, ciudad FROM observacion_precio "
        f"WHERE fuente IN ({fuentes}) "
        "AND (ambito <> 'ciudad' OR ciudad IS NULL OR codigo_mercado IS NOT NULL)"
    )).all()
    if not simular and filas:
        c.execute(
            text("UPDATE observacion_precio SET ambito = 'ciudad', ciudad = :ciudad, codigo_mercado = NULL WHERE id = :id"),
            [{"id": f.id, "ciudad": f.ciudad or f.codigo_mercado} for f in filas],
        )
    return len(filas)


def producto_al_codigo_del_catalogo(c: Connection, simular: bool) -> dict:
    """'5' es el código del SIIP; el producto es 'arroz_primera'. Lo que no está en el catálogo se reporta y se deja."""
    mapeos = leer_mapeo_fuentes(PRODUCTOS_POR_DEFECTO)
    inverso = {fuente: {v: k for k, v in m.items()} for fuente, m in mapeos.items()}
    filas = c.execute(text(
        "SELECT DISTINCT fuente, codigo_producto FROM observacion_precio"
    )).all()
    cambios, sin_mapeo = [], []
    for f in filas:
        catalogo = inverso.get(f.fuente, {}).get(f.codigo_producto)
        if catalogo is None:
            if f.codigo_producto not in mapeos.get(f.fuente, {}):
                sin_mapeo.append((f.fuente, f.codigo_producto))
            continue
        cambios.append({"fuente": f.fuente, "viejo": f.codigo_producto, "nuevo": catalogo})
    if not simular and cambios:
        c.execute(text(
            "UPDATE observacion_precio SET codigo_producto = :nuevo "
            "WHERE fuente = :fuente AND codigo_producto = :viejo"
        ), cambios)
    for fuente, codigo in sin_mapeo:
        log.warning("%s/%s no está en el catálogo de productos: se deja como está", fuente, codigo)
    return {"remapeados": [(x["viejo"], x["nuevo"]) for x in cambios], "sin_mapeo": sin_mapeo}


def reprocesar_parseo(c: Connection, simular: bool) -> dict:
    """El parser de hoy sobre unidad_texto. El par original no se toca."""
    filas = c.execute(text(
        "SELECT id, fuente, unidad_texto, cantidad, precio_monto, unidad_canonica, precio_canonico, "
        "tipo_precio, fecha_observacion, anio, mes, dia FROM observacion_precio"
    )).all()
    cambios, no_convertibles = [], 0
    for f in filas:
        unidad = Unidad(f.unidad_texto)
        cantidad = f.cantidad or 1.0
        if unidad.es_conocida():
            canonica, factor = unidad.equivalencia()
            canonico = round(f.precio_monto / factor / cantidad, 6)
            unidad_canonica = canonica.value
        else:
            canonico, unidad_canonica = None, None
            no_convertibles += 1
        tipo = TipoPrecio.COTIZADO.value if f.fuente in FUENTES_CIUDAD else (f.tipo_precio or "desconocido")
        fecha = f.fecha_observacion
        if fecha is None and f.mes and f.dia:
            fecha = date(f.anio, f.mes, f.dia)
        nuevo = (unidad_canonica, canonico, tipo, fecha)
        viejo = (f.unidad_canonica, f.precio_canonico, f.tipo_precio, f.fecha_observacion)
        if nuevo != viejo:
            cambios.append({"id": f.id, "uc": unidad_canonica, "pc": canonico, "tp": tipo, "fo": fecha})
    if not simular and cambios:
        c.execute(text(
            "UPDATE observacion_precio SET unidad_canonica = :uc, precio_canonico = :pc, "
            "tipo_precio = :tp, fecha_observacion = :fo WHERE id = :id"
        ), cambios)
    return {"revisadas": len(filas), "corregidas": len(cambios), "no_convertibles": no_convertibles}


def deduplicar(c: Connection, simular: bool) -> dict:
    """Una fila por clave natural, la de la PRIMERA captura. Antes, verifica que no haya nada que perder."""
    filas = c.execute(text(
        "SELECT id, fuente, nivel, codigo_producto, ambito, codigo_mercado, ciudad, anio, mes, dia, "
        "unidad_texto, cantidad, precio_monto, capturada_en FROM observacion_precio ORDER BY id"
    )).all()
    grupos: dict[tuple, list] = defaultdict(list)
    for f in filas:
        clave = (f.fuente, f.nivel, f.codigo_producto, f.ambito, f.codigo_mercado, f.ciudad,
                 f.anio, f.mes, f.dia, f.unidad_texto, f.cantidad or 1.0)
        grupos[clave].append(f)

    con_valores_distintos = {k: sorted({f.precio_monto for f in v}) for k, v in grupos.items()
                             if len({f.precio_monto for f in v}) > 1}
    if con_valores_distintos:
        for k, valores in list(con_valores_distintos.items())[:10]:
            log.error("Hecho con valores distintos: %s -> %s", k, valores)
        raise GrupoConValoresDistintos(
            f"{len(con_valores_distintos)} hecho(s) con más de un valor entre sus repeticiones. "
            "No es duplicación, es revisión: no se borra nada. Revisar a mano."
        )

    a_borrar, a_marcar = [], []
    for v in grupos.values():
        if len(v) == 1:
            continue
        primera, resto = v[0], v[1:]
        a_borrar.extend(f.id for f in resto)
        a_marcar.append({"id": primera.id, "ultima": max(v, key=lambda f: str(f.capturada_en)).capturada_en})
    if not simular and a_borrar:
        c.execute(text("UPDATE observacion_precio SET ultima_captura_en = :ultima WHERE id = :id"), a_marcar)
        for i in range(0, len(a_borrar), 500):
            lote = a_borrar[i:i + 500]
            c.execute(text(f"DELETE FROM observacion_precio WHERE id IN ({', '.join(map(str, lote))})"))
    return {"filas": len(filas), "hechos": len(grupos), "borradas": len(a_borrar)}


def verificar(motor: Engine) -> dict:
    with motor.connect() as c:
        total = c.execute(text("SELECT count(*) FROM observacion_precio")).scalar()
        por_ambito = dict(c.execute(text(
            "SELECT ambito, count(*) FROM observacion_precio GROUP BY ambito"
        )).all())
        sin_canonica = c.execute(text(
            "SELECT count(*) FROM observacion_precio WHERE unidad_canonica IS NULL"
        )).scalar()
        productos = [r[0] for r in c.execute(text("SELECT DISTINCT codigo_producto FROM observacion_precio")).all()]
        mercados = c.execute(text("SELECT count(*) FROM mercado")).scalar()
        productos_catalogo = c.execute(text("SELECT count(*) FROM producto")).scalar()
    repo = ObservacionesPostgres(fabrica_sesiones(motor))
    fallan, cargadas = 0, 0
    for codigo in productos:
        try:
            cargadas += len(repo.buscar(codigo))
        except Exception as e:   # noqa: BLE001 - se cuenta y se reporta, no se oculta
            log.error("Producto %s no carga como entidad: %s", codigo, e)
            fallan += 1
    return {
        "total": total, "por_ambito": por_ambito, "sin_unidad_canonica": sin_canonica,
        "cargadas_como_entidad": cargadas, "productos_que_fallan_al_cargar": fallan,
        "mercados_en_catalogo": mercados, "productos_en_catalogo": productos_catalogo,
    }


# --- orquestación ---------------------------------------------------------

def reparar(motor: Engine, simular: bool) -> dict:
    modo = "SIMULACIÓN" if simular else "APLICANDO"
    log.info("== %s ==", modo)
    crear_esquema(motor)
    informe: dict = {}

    informe["1_catalogo"] = sembrar_catalogo(motor, simular)
    log.info("1. Catálogo: %s", informe["1_catalogo"])

    with motor.begin() as c:
        informe["2_ciudad"] = ciudad_a_su_campo(c, simular)
        log.info("2. Filas del SIIP con la ciudad en su campo: %s", informe["2_ciudad"])
        informe["2b_producto"] = producto_al_codigo_del_catalogo(c, simular)
        log.info("2b. Producto al código del catálogo: %s", informe["2b_producto"])
        informe["3_parseo"] = reprocesar_parseo(c, simular)
        log.info("3. Parseo: %s", informe["3_parseo"])
        informe["4_dedup"] = deduplicar(c, simular)
        log.info("4. Deduplicación: %s", informe["4_dedup"])

    if not simular:
        asegurar_indice_clave_natural(motor)
        log.info("5. Índice único del hecho observado creado")
    else:
        log.info("5. (simulación) el índice se crearía después de deduplicar")

    informe["verificacion"] = verificar(motor)
    log.info("Verificación: %s", informe["verificacion"])
    return informe


def main() -> int:
    p = argparse.ArgumentParser(description="Repara los datos existentes de observacion_precio")
    p.add_argument("--aplicar", action="store_true",
                   help="Escribe. Sin esto es una simulación y no toca nada.")
    args = p.parse_args()

    if not config.base_datos_url:
        log.error("BASE_DATOS_URL no está configurada.")
        return 2
    motor = crear_motor(config.base_datos_url)
    try:
        informe = reparar(motor, simular=not args.aplicar)
    except GrupoConValoresDistintos as e:
        log.error("PARADO: %s", e)
        return 3

    v = informe["verificacion"]
    print("\nRESULTADO" + (" (simulación: nada se escribió)" if not args.aplicar else ""))
    print(f"  filas en observacion_precio: {v['total']}")
    print(f"  por ámbito:                  {v['por_ambito']}")
    print(f"  sin unidad canónica:         {v['sin_unidad_canonica']}")
    print(f"  cargadas como entidad:       {v['cargadas_como_entidad']}")
    print(f"  productos que fallan:        {v['productos_que_fallan_al_cargar']}")
    print(f"  catálogo: {v['mercados_en_catalogo']} puntos de venta, {v['productos_en_catalogo']} productos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
