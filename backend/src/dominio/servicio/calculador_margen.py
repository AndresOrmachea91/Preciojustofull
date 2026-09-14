"""
Calculador de margen: el segundo servicio de dominio.

Implementa el modelo de tres niveles ya validado empíricamente sobre datos
del SIIP (margen estable, CV entre 0,06 y 0,21 en series de hasta 82 meses):

    precio_mercado = precio_mayorista x margen_ciudad x factor_mercado

El margen de ciudad se recalibra solo cada mes contra el dato oficial al
consumidor. El factor de mercado se mide en campo y es lo único que exige
trabajo humano.
"""
from __future__ import annotations
import statistics as est
from dataclasses import dataclass

from src.dominio.modelo.mercado import Mercado


@dataclass(frozen=True, slots=True)
class Margen:
    codigo_producto: str
    valor: float
    coeficiente_variacion: float
    meses_observados: int

    @property
    def es_confiable(self) -> bool:
        """Por debajo de 0,30 el margen sirve para estimar."""
        return self.coeficiente_variacion <= 0.30 and self.meses_observados >= 6


class CalculadorMargen:
    def calcular(
        self, codigo_producto: str, mayoristas: list[float], minoristas: list[float]
    ) -> Margen:
        pares = [
            (may, men)
            for may, men in zip(mayoristas, minoristas)
            if may and men and may > 0
        ]
        if not pares:
            return Margen(codigo_producto, 1.0, 999.0, 0)

        razones = [men / may for may, men in pares]
        media = est.mean(razones)
        desv = est.pstdev(razones) if len(razones) > 1 else 0.0
        return Margen(
            codigo_producto=codigo_producto,
            valor=round(est.median(razones), 4),
            coeficiente_variacion=round(desv / media, 4) if media else 999.0,
            meses_observados=len(razones),
        )

    def estimar_precio_mercado(
        self, precio_mayorista: float, margen: Margen, mercado: Mercado
    ) -> float:
        return round(precio_mayorista * margen.valor * mercado.factor_mercado, 2)

