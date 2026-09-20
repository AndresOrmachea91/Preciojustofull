"""
Motor de fusión: el corazón del proyecto.

Decide qué precio publicar cuando varias fuentes afirman precios distintos
para el mismo producto en el mismo lugar, sin conocer la verdad.

Es un servicio de DOMINIO: no sabe de bases de datos, ni de HTTP, ni de
frameworks. Se le pasan observaciones y devuelve un precio consolidado.
Por eso se puede probar entero sin levantar nada.

Dos reglas sostienen la honestidad del resultado:

1. COMPARABILIDAD. Solo se fusionan observaciones de la misma clave:
   producto + variedad + unidad canónica + nivel de precio + período.
   Grupos distintos no se fusionan y no son conflicto: se publican por
   separado. Conflicto es desacuerdo DENTRO de un grupo.

2. INDEPENDENCIA. Dos fuentes que dicen lo mismo porque una copia a la
   otra no son dos evidencias. Las observaciones se agrupan en clanes de
   derivación y cada clan aporta una sola evidencia. La confianza sube
   con el número de clanes independientes, no de observaciones.
"""
from __future__ import annotations
import statistics as est
from dataclasses import dataclass
from datetime import datetime, timezone

from src.dominio.excepciones import (
    GruposNoComparables, NivelesNoComparables, ReferenciaNoEsMedicion, SinObservaciones,
)
from src.dominio.modelo.mercado import Mercado
from src.dominio.modelo.observacion import Fuente, Observacion
from src.dominio.modelo.precio_consolidado import PrecioConsolidado, RangoPrecio
from src.dominio.valor import NivelConfianza, NivelPrecio, Procedencia, UnidadCanonica


@dataclass(frozen=True, slots=True, order=True)
class ClaveComparabilidad:
    """
    Lo que tiene que coincidir para que dos observaciones hablen del mismo
    precio.

    El período va en la clave, con granularidad de MES, y no como ventana
    que el llamador elige. Tres razones: (1) el mes es el período más fino
    que TODA observación tiene —el IPC es mensual, el diario tiene día—,
    así que una diaria y una mensual del mismo mes se comparan y julio
    nunca se mezcla con septiembre; (2) el motor sigue siendo una función
    pura de sus observaciones, sin un "hoy" inyectado que haga variar el
    resultado según cuándo se corra; (3) qué grupo publicar (el más
    reciente) es decisión del caso de uso, no del motor.
    """

    codigo_producto: str
    variedad: str
    unidad: UnidadCanonica
    nivel: NivelPrecio
    anio: int
    mes: int | None

    @classmethod
    def de(cls, o: Observacion) -> "ClaveComparabilidad":
        return cls(o.codigo_producto, o.variedad, o.unidad_canonica, o.nivel, o.periodo.anio, o.periodo.mes)

    def __str__(self) -> str:
        periodo = f"{self.anio:04d}-{self.mes:02d}" if self.mes else str(self.anio)
        return f"{self.codigo_producto}/{self.variedad}/{self.unidad.value}/{self.nivel.value}/{periodo}"


class MotorFusion:
    def __init__(self, umbral_atipico: float = 2.5, umbral_conflicto: float = 0.30):
        # umbral_atipico: cuántas desviaciones medias absolutas tolera antes
        # de descartar una observación.
        self.umbral_atipico = umbral_atipico
        # umbral_conflicto: qué tanta discrepancia relativa se registra como
        # conflicto para auditar después.
        self.umbral_conflicto = umbral_conflicto
        # Un ciclo en la derivación haría que un clan se contenga a sí
        # mismo. Se falla acá, al construir, no en la observación 10.000.
        Fuente.validar_derivaciones()

    # -- API pública -------------------------------------------------------

    @staticmethod
    def agrupar(observaciones: list[Observacion]) -> dict[ClaveComparabilidad, list[Observacion]]:
        """
        Reparte las observaciones por clave de comparabilidad, del período
        más reciente al más viejo. Las no convertibles no entran en ningún
        grupo: sin unidad canónica no hay con qué compararlas.
        """
        grupos: dict[ClaveComparabilidad, list[Observacion]] = {}
        for o in observaciones:
            if not o.es_convertible:
                continue
            grupos.setdefault(ClaveComparabilidad.de(o), []).append(o)
        return dict(sorted(grupos.items(), key=lambda kv: (kv[0].anio, kv[0].mes or 0), reverse=True))

    def consolidar_grupos(self, observaciones: list[Observacion]) -> list[PrecioConsolidado]:
        """
        Un precio por grupo comparable, del más reciente al más viejo.
        Grupos distintos no son conflicto entre sí.
        """
        if not observaciones:
            raise SinObservaciones("No hay observaciones para consolidar")
        self._rechazar_referencias(observaciones)
        grupos = self.agrupar(observaciones)
        if not grupos:
            raise SinObservaciones("Ninguna observación tiene unidad reconocible")
        return [self._consolidar_grupo(obs) for obs in grupos.values()]

    def consolidar(self, observaciones: list[Observacion]) -> PrecioConsolidado:
        """
        El precio de UN local a partir de lo que se midió EN ese local,
        cuando todas las observaciones son comparables entre sí. Si no lo
        son, lo dice en vez de promediar peras con manzanas.

        Un dato publicado por ciudad no entra acá: no es una medición de
        ningún puesto. Para eso está estimar_desde_ciudad.
        """
        if not observaciones:
            raise SinObservaciones("No hay observaciones para consolidar")
        self._rechazar_referencias(observaciones)
        return self._consolidar_un_solo_grupo(observaciones)

    def estimar_desde_ciudad(
        self, referencia: list[Observacion], mercado: Mercado
    ) -> PrecioConsolidado:
        """
        Estima el precio en un local a partir de la referencia de ciudad
        (SIIP) y de cuánto se aparta ese local de la ciudad (factor_mercado,
        aprendido en campo). El resultado se marca como estimación: nunca
        alcanza la confianza de una medición.
        """
        if not referencia:
            raise SinObservaciones("No hay referencia de ciudad para estimar")
        if any(not o.es_referencia_de_ciudad for o in referencia):
            raise ValueError("estimar_desde_ciudad solo acepta observaciones de ámbito ciudad")
        if any(o.nivel is not mercado.nivel_precio for o in referencia):
            raise NivelesNoComparables(
                {o.nivel.value for o in referencia} | {mercado.nivel_precio.value}
            )

        ciudad = self._consolidar_un_solo_grupo(referencia)
        f = mercado.factor_mercado
        confianza = min(ciudad.confianza, NivelConfianza.MEDIO, key=lambda c: c.peso)
        return PrecioConsolidado(
            codigo_producto=ciudad.codigo_producto,
            codigo_mercado=mercado.codigo,
            periodo=ciudad.periodo,
            rango=RangoPrecio(round(ciudad.rango.minimo * f, 2), round(ciudad.rango.maximo * f, 2)),
            unidad=ciudad.unidad,
            confianza=confianza,
            observaciones_usadas=ciudad.observaciones_usadas,
            # Siempre ESTIMADO: aunque el insumo sea una medición, es
            # medición de otra cosa (la ciudad), no de este local.
            procedencia=Procedencia.ESTIMADO,
            fecha_observacion_mas_reciente=ciudad.fecha_observacion_mas_reciente,
            calculado_en=ciudad.calculado_en,
            conflictos=ciudad.conflictos + [
                f"Estimado desde la referencia de ciudad {referencia[0].codigo_mercado} "
                f"con factor {f:.2f}; no es una medición en {mercado.codigo}"
            ],
        )

    # -- comparabilidad ----------------------------------------------------

    @staticmethod
    def _rechazar_referencias(observaciones: list[Observacion]) -> None:
        referencia = next((o for o in observaciones if o.es_referencia_de_ciudad), None)
        if referencia is not None:
            raise ReferenciaNoEsMedicion(referencia.codigo_mercado)

    def _consolidar_un_solo_grupo(self, observaciones: list[Observacion]) -> PrecioConsolidado:
        grupos = self.agrupar(observaciones)
        if not grupos:
            raise SinObservaciones("Ninguna observación tiene unidad reconocible")
        if len(grupos) > 1:
            # Un precio mayorista y uno de consumidor final no miden lo
            # mismo: se dice con nombre propio. Cualquier otra diferencia
            # de clave también impide fusionar, pero no es conflicto.
            niveles = {c.nivel.value for c in grupos}
            if len(niveles) > 1:
                raise NivelesNoComparables(niveles)
            raise GruposNoComparables([str(c) for c in grupos])
        (obs,) = grupos.values()
        return self._consolidar_grupo(obs)

    def _consolidar_grupo(self, observaciones: list[Observacion]) -> PrecioConsolidado:
        """Fusiona un grupo YA comparable. Acá vive la política de fusión."""
        base = observaciones[0]

        # Primero una evidencia por clan, DESPUÉS los atípicos: si fuera al
        # revés, tres copias del mismo boletín podrían votar para expulsar
        # al dato original. Una copia no vota.
        clanes = self._una_evidencia_por_clan(observaciones)
        evidencias_todas = [representante for representante, _ in clanes]
        valores = [o.precio_canonico() for o in evidencias_todas]
        conflictos = self._detectar_conflictos(valores)
        evidencias, descartadas = self._quitar_atipicos(evidencias_todas, valores)
        if descartadas:
            conflictos.append(f"{len(descartadas)} observación(es) descartada(s) por atípicas")
        conservadas = [
            miembro for representante, miembros in clanes
            if representante in evidencias for miembro in miembros
        ]

        precio = self._promedio_ponderado(evidencias)
        dispersion = self._dispersion(evidencias, precio)
        confianza = self._confianza(evidencias, dispersion)

        return PrecioConsolidado(
            codigo_producto=base.codigo_producto,
            codigo_mercado=base.codigo_mercado,
            periodo=base.periodo,
            rango=RangoPrecio(
                minimo=round(precio * (1 - dispersion), 2),
                maximo=round(precio * (1 + dispersion), 2),
            ),
            unidad=base.unidad_canonica,
            confianza=confianza,
            observaciones_usadas=len(conservadas),
            procedencia=Procedencia.OBSERVADO,
            fecha_observacion_mas_reciente=self._fecha_mas_reciente(conservadas),
            calculado_en=datetime.now(timezone.utc),
            conflictos=conflictos,
        )

    # -- independencia -----------------------------------------------------

    @staticmethod
    def _una_evidencia_por_clan(
        obs: list[Observacion],
    ) -> list[tuple[Observacion, list[Observacion]]]:
        """
        Agrupa por clan de derivación (siguiendo deriva_de de forma
        transitiva hasta la fuente raíz) y elige UNA observación por clan
        como evidencia: la de su miembro más confiable. No se suman ni se
        promedian las confiabilidades: un boletín copiado veinte veces
        sigue siendo un boletín.

        Solo las fuentes de voz única forman clan. Cada reporte ciudadano,
        visita de campo o nota propia es una voz distinta y una evidencia
        propia. Devuelve (representante, miembros) por clan, en orden de
        aparición.
        """
        clanes: dict[object, list[Observacion]] = {}
        for i, o in enumerate(obs):
            clave = o.fuente.raiz if o.fuente.es_voz_unica else ("voz", i)
            clanes.setdefault(clave, []).append(o)
        return [
            (max(miembros, key=MotorFusion._confiabilidad), miembros)
            for miembros in clanes.values()
        ]

    @staticmethod
    def _confiabilidad(o: Observacion) -> float:
        return o.confianza.peso * o.reputacion_informante

    # -- pasos internos ----------------------------------------------------

    @staticmethod
    def _fecha_mas_reciente(obs: list[Observacion]):
        fechas = [o.fecha_observacion for o in obs if o.fecha_observacion_conocida]
        return max(fechas) if fechas else None

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

    def _promedio_ponderado(self, evidencias: list[Observacion]) -> float:
        """
        Cada evidencia pesa según su confianza y la reputación de quien
        reportó. Un dato verificado en campo pesa cuatro veces más que un
        reporte ciudadano sin historial.
        """
        total_peso = sum(self._confiabilidad(o) for o in evidencias)
        if total_peso == 0:
            return round(est.mean(o.precio_canonico() for o in evidencias), 4)
        acumulado = sum(o.precio_canonico() * self._confiabilidad(o) for o in evidencias)
        return round(acumulado / total_peso, 4)

    def _dispersion(self, evidencias: list[Observacion], centro: float) -> float:
        """Media amplitud del rango, como fracción del precio."""
        if len(evidencias) < 2 or centro <= 0:
            return 0.08   # rango mínimo: ningún precio de mercado es exacto
        desv = est.pstdev([o.precio_canonico() for o in evidencias])
        return min(max(desv / centro, 0.05), 0.35)

    def _confianza(self, evidencias: list[Observacion], dispersion: float) -> NivelConfianza:
        """Sube con el número de CLANES independientes que coinciden, no de observaciones."""
        if any(o.confianza is NivelConfianza.VERIFICADO for o in evidencias):
            return NivelConfianza.VERIFICADO
        if len(evidencias) >= 2 and dispersion < 0.15:
            return NivelConfianza.ALTO
        if len(evidencias) >= 2:
            return NivelConfianza.MEDIO
        return evidencias[0].confianza
