"""Salud del sistema sin base de datos: lo que se puede contar en memoria. No hay recolector ni respaldos."""
from __future__ import annotations

from collections import Counter
from datetime import date

from src.dominio.modelo import DatosDeFuente, DatosSalud
from src.dominio.valor import Ambito


class SaludEnMemoria:
    def __init__(self, productos, mercados, observaciones):
        self._productos = productos
        self._mercados = mercados
        self._observaciones = observaciones

    def leer(self, desde: date) -> DatosSalud:
        todas = [o for p in self._productos.listar() for o in self._observaciones.buscar(p.codigo)]
        por_fuente = Counter(o.fuente.value for o in todas)
        ultima = {}
        for o in todas:
            ultima[o.fuente.value] = max(ultima.get(o.fuente.value, o.capturada_en), o.capturada_en)
        pares = {(o.codigo_mercado, o.codigo_producto) for o in todas
                 if o.ambito is Ambito.PUNTO_VENTA and (o.fecha_observacion or o.capturada_en.date()) >= desde}
        return DatosSalud(
            fuentes=[DatosDeFuente(f, n, ultima[f]) for f, n in por_fuente.most_common()],
            pares_observados=len(pares),
            pares_posibles=len(self._productos.listar()) * len(self._mercados.listar()),
        )
