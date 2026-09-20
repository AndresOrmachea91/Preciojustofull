"""
Lector del catálogo de puntos de venta en CSV.

Es un adaptador: acá se importa csv y se conocen los nombres de las
columnas. Traduce filas a entidades del dominio y nada más. Si el archivo
cambia de formato, cambia este archivo; el caso de uso no se entera.
"""
from __future__ import annotations
import csv
from pathlib import Path
from typing import Iterable

from src.dominio.modelo import Categoria, Mercado, Producto, TipoPuntoVenta
from src.dominio.valor import UnidadCanonica

COLUMNAS_OBLIGATORIAS = ("codigo", "nombre", "tipo", "macrodistrito", "latitud", "longitud")
COLUMNAS_PRODUCTO = ("codigo", "nombre", "categoria", "unidad_base", "es_perecedero")

# Cómo escribe el catálogo la unidad base y qué unidad canónica es.
UNIDADES_BASE = {
    "kg": UnidadCanonica.KILOGRAMO,
    "litro": UnidadCanonica.LITRO,
    "unidad": UnidadCanonica.UNIDAD,
    "atado": UnidadCanonica.ATADO,
}
# El dominio razona en días de conservación (cuán rápido le pega un
# bloqueo). El catálogo solo sabe si es perecedero: se traduce a un
# valor representativo de cada lado del umbral de 7 días.
DIAS_PERECEDERO, DIAS_NO_PERECEDERO = 5, 30
BOOLEANOS = {"si": True, "sí": True, "no": False}


class CatalogoCorrupto(ValueError):
    """Una fila del catálogo no se puede traducir. Dice cuál y por qué."""

    def __init__(self, ruta: Path | str, numero_fila: int, motivo: str):
        self.ruta = str(ruta)
        self.numero_fila = numero_fila
        self.motivo = motivo
        super().__init__(f"{self.ruta}, fila {numero_fila}: {motivo}")


def leer_puntos_venta(ruta: Path | str) -> list[Mercado]:
    ruta = Path(ruta)
    with ruta.open(encoding="utf-8", newline="") as archivo:
        lector = csv.DictReader(archivo)
        faltan = [c for c in COLUMNAS_OBLIGATORIAS if c not in (lector.fieldnames or [])]
        if faltan:
            raise CatalogoCorrupto(ruta, 1, f"faltan las columnas {faltan}")
        # La fila 1 es el encabezado; la primera de datos es la 2.
        return [_a_mercado(ruta, n, fila) for n, fila in enumerate(lector, start=2)]


def filas_a_puntos_venta(filas: Iterable[dict], origen: str = "<memoria>") -> list[Mercado]:
    """Misma traducción, sin archivo. Para pruebas y para otros orígenes tabulares."""
    return [_a_mercado(origen, n, fila) for n, fila in enumerate(filas, start=2)]


def leer_productos(ruta: Path | str) -> list[Producto]:
    ruta = Path(ruta)
    with ruta.open(encoding="utf-8", newline="") as archivo:
        lector = csv.DictReader(archivo)
        faltan = [c for c in COLUMNAS_PRODUCTO if c not in (lector.fieldnames or [])]
        if faltan:
            raise CatalogoCorrupto(ruta, 1, f"faltan las columnas {faltan}")
        return [_a_producto(ruta, n, fila) for n, fila in enumerate(lector, start=2)]


def filas_a_productos(filas: Iterable[dict], origen: str = "<memoria>") -> list[Producto]:
    return [_a_producto(origen, n, fila) for n, fila in enumerate(filas, start=2)]


COLUMNAS_FUENTE = ("siip_diario", "siip_ipc")


def leer_mapeo_fuentes(ruta: Path | str) -> dict[str, dict[str, str]]:
    """
    Por fuente, qué código usa esa fuente para cada producto del catálogo:
    {"siip_diario": {"arroz_primera": "5", ...}, "siip_ipc": {...}}.
    Solo entran los productos que tienen código en esa fuente.
    """
    ruta = Path(ruta)
    mapeo: dict[str, dict[str, str]] = {col: {} for col in COLUMNAS_FUENTE}
    with ruta.open(encoding="utf-8", newline="") as archivo:
        for n, fila in enumerate(csv.DictReader(archivo), start=2):
            for col in COLUMNAS_FUENTE:
                codigo_fuente = (fila.get(col) or "").strip()
                if codigo_fuente:
                    mapeo[col][fila["codigo"].strip()] = codigo_fuente
    return mapeo


def _a_producto(ruta, numero: int, fila: dict) -> Producto:
    for col in COLUMNAS_PRODUCTO:
        if not (fila.get(col) or "").strip():
            raise CatalogoCorrupto(ruta, numero, f"la columna '{col}' está vacía")

    categoria_texto = fila["categoria"].strip()
    try:
        categoria = Categoria(categoria_texto)
    except ValueError:
        validos = ", ".join(c.value for c in Categoria)
        raise CatalogoCorrupto(
            ruta, numero, f"categoría desconocida '{categoria_texto}' (válidas: {validos})"
        )

    unidad_texto = fila["unidad_base"].strip().lower()
    if unidad_texto not in UNIDADES_BASE:
        raise CatalogoCorrupto(
            ruta, numero,
            f"unidad_base desconocida '{unidad_texto}' (válidas: {', '.join(UNIDADES_BASE)})",
        )

    perecedero_texto = fila["es_perecedero"].strip().lower()
    if perecedero_texto not in BOOLEANOS:
        raise CatalogoCorrupto(ruta, numero, f"es_perecedero debe ser si o no, no '{perecedero_texto}'")

    return Producto(
        codigo=fila["codigo"].strip(),
        nombre=fila["nombre"].strip(),
        categoria=categoria,
        dias_conservacion=DIAS_PERECEDERO if BOOLEANOS[perecedero_texto] else DIAS_NO_PERECEDERO,
        unidad_base=UNIDADES_BASE[unidad_texto],
    )


def _a_mercado(ruta, numero: int, fila: dict) -> Mercado:
    for col in COLUMNAS_OBLIGATORIAS:
        if not (fila.get(col) or "").strip():
            raise CatalogoCorrupto(ruta, numero, f"la columna '{col}' está vacía")

    tipo_texto = fila["tipo"].strip()
    try:
        tipo = TipoPuntoVenta(tipo_texto)
    except ValueError:
        validos = ", ".join(t.value for t in TipoPuntoVenta)
        raise CatalogoCorrupto(ruta, numero, f"tipo desconocido '{tipo_texto}' (válidos: {validos})")

    try:
        latitud, longitud = float(fila["latitud"]), float(fila["longitud"])
    except ValueError:
        raise CatalogoCorrupto(
            ruta, numero, f"coordenadas ilegibles: {fila['latitud']!r}, {fila['longitud']!r}"
        )

    macrodistrito = fila["macrodistrito"].strip()
    padre = (fila.get("codigo_padre") or "").strip() or None
    try:
        return Mercado(
            codigo=fila["codigo"].strip(),
            nombre=fila["nombre"].strip(),
            tipo=tipo,
            # El catálogo no trae barrio: el macrodistrito es la zona más
            # fina que se conoce, y es lo que filtra /mercados?zona=.
            zona=macrodistrito,
            latitud=latitud,
            longitud=longitud,
            macrodistrito=macrodistrito,
            codigo_padre=padre,
        )
    except ValueError as e:
        raise CatalogoCorrupto(ruta, numero, str(e))
