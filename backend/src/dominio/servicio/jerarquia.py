"""
Reglas de la jerarquía de puntos de venta.

Un local pertenece a un mercado (el sector cubierto del Rodríguez pertenece
al Rodríguez). Las reglas que necesitan mirar más de una entidad no caben
en la entidad: viven acá, como servicio de dominio.

Son las mismas invariantes que `tests/test_catalogo_csv.py` verifica sobre
el archivo. No es duplicación: el CSV valida el archivo; esto valida
cualquier origen (API, reportes, OCR) antes de que toque el repositorio.
"""
from __future__ import annotations
from typing import Iterable

from src.dominio.excepciones import JerarquiaInvalida
from src.dominio.modelo.mercado import Mercado


def validar_jerarquia(puntos: Iterable[Mercado]) -> None:
    """Lanza JerarquiaInvalida con TODAS las infracciones, no solo la primera."""
    por_codigo = {p.codigo: p for p in puntos}
    infracciones: list[str] = []

    for p in por_codigo.values():
        if not p.tiene_padre:
            continue
        padre = por_codigo.get(p.codigo_padre)
        if padre is None:
            infracciones.append(f"{p.codigo} apunta al padre inexistente {p.codigo_padre}")
            continue
        if not padre.tipo.puede_ser_padre:
            infracciones.append(
                f"{p.codigo} tiene como padre a {padre.codigo}, que es {padre.tipo.value} y no mercado"
            )
        if padre.tiene_padre:
            infracciones.append(
                f"{p.codigo} -> {padre.codigo} -> {padre.codigo_padre}: la jerarquía no pasa de dos niveles"
            )

    if infracciones:
        raise JerarquiaInvalida(infracciones)


def ordenar_padres_primero(puntos: Iterable[Mercado]) -> list[Mercado]:
    """
    Los padres antes que los hijos. Quien persista con clave foránea lo
    necesita; quien no, no pierde nada. El orden relativo dentro de cada
    grupo se conserva para que la salida sea reproducible.
    """
    lista = list(puntos)
    return [p for p in lista if not p.tiene_padre] + [p for p in lista if p.tiene_padre]
