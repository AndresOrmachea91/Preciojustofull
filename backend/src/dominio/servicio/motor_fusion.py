"""
Motor de fusión: el corazón del proyecto.

Decide qué precio publicar cuando varias fuentes afirman precios distintos
para el mismo producto en el mismo lugar, sin conocer la verdad.

Es un servicio de DOMINIO: no sabe de bases de datos, ni de HTTP, ni de
frameworks. Se le pasan observaciones y devuelve un precio consolidado.
Por eso se puede probar entero sin levantar nada.
"""
from __future__ import annotations
import statistics as est
from datetime import datetime, timezone

from src.dominio.excepciones import NivelesNoComparables, SinObservaciones
from src.dominio.modelo.observacion import Observacion
from src.dominio.modelo.precio_consolidado import PrecioConsolidado, RangoPrecio
from src.dominio.valor import NivelConfianza, UnidadCanonica


class MotorFusion:
    def __init__(self, umbral_atipico: float = 2.5, umbral_conflicto: float = 0.30):
        # umbral_atipico: cuántas desviaciones medias absolutas tolera antes
        # de descartar una observación.
        self.umbral_atipico = umbral_atipico
        # umbral_conflicto: qué tanta discrepancia relativa se registra como
        # conflicto para auditar después.
        self.umbral_conflicto = umbral_conflicto

    def consolidar(self, observaciones: list[Observacion]) -> PrecioConsolidado:
        if not observaciones:
            raise SinObservaciones("No hay observaciones para consolidar")

        # Un precio mayorista y uno de consumidor final no miden lo mismo:
        # promediarlos daría un número que no existe en ningún puesto.
        niveles = {o.nivel.value for o in observaciones}
        if len(niveles) > 1:
            raise NivelesNoComparables(niveles)

        base = observaciones[0]
        validas = [o for o in observaciones if o.precio.unidad.es_conocida()]
        if not validas:
            raise SinObservaciones("Ninguna observación tiene unidad reconocible")

        valores = [o.precio_canonico() for o in validas]
        conflictos = self._detectar_conflictos(valores)
        conservadas, descartadas = self._quitar_atipicos(validas, valores)
        if descartadas:
            conflictos.append(f"{len(descartadas)} observación(es) descartada(s) por atípicas")

        precio = self._promedio_ponderado(conservadas)
        dispersion = self._dispersion(conservadas, precio)
        confianza = self._confianza(conservadas, dispersion)
        _, unidad = conservadas[0].precio.por_unidad_canonica()

        return PrecioConsolidado(
            codigo_producto=base.codigo_producto,
            codigo_mercado=base.codigo_mercado,
            periodo=base.periodo,
            rango=RangoPrecio(
                minimo=round(precio * (1 - dispersion), 2),
                maximo=round(precio * (1 + dispersion), 2),
            ),
            unidad=unidad if isinstance(unidad, UnidadCanonica) else UnidadCanonica.KILOGRAMO,
            confianza=confianza,
            observaciones_usadas=len(conservadas),
            calculado_en=datetime.now(timezone.utc),
            conflictos=conflictos,
        )

    # -- pasos internos --------------------------------------------------

    def _detectar_conflictos(self, valores: list[float]) -> list[str]:
        """Registrar la discrepancia es tan importante como resolverla."""
        if len(valores) < 2:
            return []
        menor, mayor = min(valores), max(valores)
        if menor <= 0:
            return []
        discrepancia = (mayor - menor) / menor
        if discrepancia > self.umbral_conflicto:
            return [f"Discrepancia entre fuentes del {discrepancia:.0%}"]
        return []

    def _quitar_atipicos(self, obs, valores):
        if len(obs) < 3:
            return list(obs), []
        mediana = est.median(valores)
        desviaciones = [abs(v - mediana) for v in valores]
        # Piso para la desviacion mediana absoluta: sin el, un conjunto muy
        # apretado (10,0 / 10,1 / 10,2) produce un DAM diminuto y termina
        # descartando observaciones legitimas junto con la manipulada.
        dam = max(est.median(desviaciones), abs(mediana) * 0.05, 1e-9)
        conservadas, descartadas = [], []
        for o, d in zip(obs, desviaciones):
            (conservadas if d / dam <= self.umbral_atipico else descartadas).append(o)
        return (conservadas or list(obs)), descartadas

    def _promedio_ponderado(self, obs: list[Observacion]) -> float:
        """
        Cada fuente pesa según su confianza y la reputación de quien reportó.
        Un dato verificado en campo pesa cuatro veces más que un reporte
        ciudadano sin historial.
        """
        total_peso = sum(o.confianza.peso * o.reputacion_informante for o in obs)
        if total_peso == 0:
            return round(est.mean(o.precio_canonico() for o in obs), 4)
        acumulado = sum(
            o.precio_canonico() * o.confianza.peso * o.reputacion_informante for o in obs
        )
        return round(acumulado / total_peso, 4)

    def _dispersion(self, obs: list[Observacion], centro: float) -> float:
        """Media amplitud del rango, como fracción del precio."""
        if len(obs) < 2 or centro <= 0:
            return 0.08   # rango mínimo: ningún precio de mercado es exacto
        desv = est.pstdev([o.precio_canonico() for o in obs])
        return min(max(desv / centro, 0.05), 0.35)

    def _confianza(self, obs: list[Observacion], dispersion: float) -> NivelConfianza:
        if any(o.confianza is NivelConfianza.VERIFICADO for o in obs):
            return NivelConfianza.VERIFICADO
        if len(obs) >= 2 and dispersion < 0.15:
            return NivelConfianza.ALTO
        if len(obs) >= 2:
            return NivelConfianza.MEDIO
        return obs[0].confianza

