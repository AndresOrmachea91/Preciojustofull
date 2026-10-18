"""
Backtest del estimador (C130): ¿qué tan bien adivina el sistema donde nadie midió?

El estimado de un local es referencia de ciudad (SIIP) × factor del
mercado. Para saber cuánto se equivoca se toma cada precio OBSERVADO en un
local (lo midió una persona en ese puesto, ese mes), se calcula lo que el
sistema habría estimado para ese mismo local y mes SIN mirar la medición, y
se compara:

- error porcentual absoluto medio (MAPE): cuánto se equivoca en promedio;
- sesgo: si tiende a quedarse corto (negativo) o a pasarse (positivo);
- cobertura: en cuántos casos el precio medido cayó dentro del rango que
  el sistema habría mostrado (con el rango honesto de un estimado).

Línea base: la referencia de ciudad SIN factor (todos los mercados igual).
Si el factor no mejora a la línea base, el factor no aporta y se dice.

No hay fuga de información: el estimado usa solo la referencia de ciudad,
nunca las observaciones del local. El factor de cada mercado sí se calibró
con datos de campo (A5030); por eso, cuando lleguen las mediciones nuevas,
este mismo cálculo sobre ellas es la prueba fuera de muestra.
"""
from __future__ import annotations

import statistics as est
from dataclasses import dataclass, field, replace

from src.aplicacion.casos_uso.precios.comparar_mercados import CIUDAD_POR_DEFECTO, en_unidad_del_producto
from src.aplicacion.puertos.salida import LectorMercados, LectorObservaciones, LectorProductos
from src.dominio.excepciones import ErrorDominio
from src.dominio.modelo import Mercado, NivelPrecio, Observacion, PrecioConsolidado
from src.dominio.servicio.motor_fusion import ClaveComparabilidad, MotorFusion
from src.dominio.servicio.rango_honesto import fecha_de_referencia, rango_honesto

MAXIMO_CASOS_MOSTRADOS = 60


@dataclass(frozen=True, slots=True)
class CasoEvaluado:
    codigo_producto: str
    nombre_producto: str
    codigo_mercado: str
    nombre_mercado: str
    periodo: str
    observado: float
    estimado: float
    estimado_minimo: float
    estimado_maximo: float
    sin_factor: float
    voces: dict[str, int]

    @property
    def error(self) -> float:
        """Error relativo con signo: positivo si el estimado se pasó."""
        return (self.estimado - self.observado) / self.observado

    @property
    def error_sin_factor(self) -> float:
        return (self.sin_factor - self.observado) / self.observado

    @property
    def dentro_del_rango(self) -> bool:
        return self.estimado_minimo <= self.observado <= self.estimado_maximo


@dataclass(frozen=True, slots=True)
class ResumenProducto:
    codigo_producto: str
    nombre_producto: str
    casos: int
    error_medio: float
    cobertura: float


@dataclass(slots=True)
class EvaluacionEstimador:
    casos: int = 0
    error_medio: float | None = None
    sesgo: float | None = None
    cobertura: float | None = None
    error_medio_sin_factor: float | None = None
    mercados: int = 0
    productos: int = 0
    por_producto: list[ResumenProducto] = field(default_factory=list)
    detalle: list[CasoEvaluado] = field(default_factory=list)

    @property
    def el_factor_ayuda(self) -> bool | None:
        if self.error_medio is None or self.error_medio_sin_factor is None:
            return None
        return self.error_medio < self.error_medio_sin_factor


class EvaluarEstimador:
    def __init__(self, productos: LectorProductos, mercados: LectorMercados,
                 observaciones: LectorObservaciones, motor: MotorFusion,
                 ciudad: str = CIUDAD_POR_DEFECTO):
        self._productos = productos
        self._mercados = mercados
        self._observaciones = observaciones
        self._motor = motor
        self._ciudad = ciudad

    def ejecutar(self) -> EvaluacionEstimador:
        mercados = {m.codigo: m for m in self._mercados.listar()}
        casos: list[CasoEvaluado] = []
        for producto in self._productos.listar():
            todas = en_unidad_del_producto(self._observaciones.buscar(producto.codigo), producto)
            referencia = [o for o in todas if o.es_referencia_de_ciudad and o.ciudad == self._ciudad]
            if not referencia:
                continue
            ciudad_por_mes = self._motor.agrupar(referencia)
            locales: dict[str, list[Observacion]] = {}
            for o in todas:
                if o.codigo_mercado in mercados:
                    locales.setdefault(o.codigo_mercado, []).append(o)
            for codigo, obs in locales.items():
                casos.extend(self._casos_del_local(producto.nombre, mercados[codigo], obs, ciudad_por_mes))
        return _resumir(casos)

    def _casos_del_local(self, nombre_producto: str, mercado: Mercado, obs: list[Observacion],
                         ciudad_por_mes: dict[ClaveComparabilidad, list[Observacion]]) -> list[CasoEvaluado]:
        propias = [o for o in obs if o.nivel is mercado.nivel_precio]
        if not propias:
            return []
        casos = []
        for observado in self._motor.consolidar_grupos(propias):
            ref = _referencia_del_mismo_mes(observado, mercado.nivel_precio, ciudad_por_mes)
            if ref is None:
                continue
            try:
                estimado = self._motor.estimar_desde_ciudad(ref, mercado)
                sin_factor = self._motor.estimar_desde_ciudad(ref, replace(mercado, factor_mercado=1.0))
            except ErrorDominio:
                continue
            # El rango que el sistema MOSTRARÍA ese día: el honesto de un estimado.
            mostrado = rango_honesto(estimado, fecha_de_referencia(observado))
            casos.append(CasoEvaluado(
                codigo_producto=observado.codigo_producto, nombre_producto=nombre_producto,
                codigo_mercado=mercado.codigo, nombre_mercado=mercado.nombre,
                periodo=str(observado.periodo)[:7],
                observado=observado.rango.centro, estimado=estimado.rango.centro,
                estimado_minimo=mostrado.rango.minimo, estimado_maximo=mostrado.rango.maximo,
                sin_factor=sin_factor.rango.centro, voces=observado.voces,
            ))
        return casos


def _referencia_del_mismo_mes(observado: PrecioConsolidado, nivel: NivelPrecio,
                              ciudad_por_mes: dict[ClaveComparabilidad, list[Observacion]]):
    """La referencia de ciudad del MISMO mes y nivel: comparar septiembre con julio no prueba nada."""
    for clave, grupo in ciudad_por_mes.items():
        if (clave.anio, clave.mes, clave.nivel) == (observado.periodo.anio, observado.periodo.mes, nivel):
            return grupo
    return None


def _resumir(casos: list[CasoEvaluado]) -> EvaluacionEstimador:
    if not casos:
        return EvaluacionEstimador()
    por_producto: dict[str, list[CasoEvaluado]] = {}
    for c in casos:
        por_producto.setdefault(c.codigo_producto, []).append(c)
    resumen = [
        ResumenProducto(
            codigo_producto=codigo, nombre_producto=lista[0].nombre_producto, casos=len(lista),
            error_medio=round(est.mean(abs(c.error) for c in lista), 4),
            cobertura=round(sum(c.dentro_del_rango for c in lista) / len(lista), 4),
        )
        for codigo, lista in por_producto.items()
    ]
    resumen.sort(key=lambda r: (-r.casos, r.nombre_producto))
    return EvaluacionEstimador(
        casos=len(casos),
        error_medio=round(est.mean(abs(c.error) for c in casos), 4),
        sesgo=round(est.mean(c.error for c in casos), 4),
        cobertura=round(sum(c.dentro_del_rango for c in casos) / len(casos), 4),
        error_medio_sin_factor=round(est.mean(abs(c.error_sin_factor) for c in casos), 4),
        mercados=len({c.codigo_mercado for c in casos}),
        productos=len(por_producto),
        por_producto=resumen,
        detalle=sorted(casos, key=lambda c: -abs(c.error))[:MAXIMO_CASOS_MOSTRADOS],
    )
