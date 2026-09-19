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

from src.dominio.modelo import Mercado, TipoPuntoVenta

COLUMNAS_OBLIGATORIAS = ("codigo", "nombre", "tipo", "macrodistrito", "latitud", "longitud")


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
