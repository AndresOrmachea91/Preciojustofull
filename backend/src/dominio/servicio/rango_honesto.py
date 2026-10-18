"""
Rango honesto: un precio viejo o estimado no puede mostrarse tan seguro
como uno medido ayer.

El motor de fusión da un rango según cuánto discrepan las fuentes. Eso
mide el desacuerdo de HOY entre quienes hablaron, pero no lo que pudo
moverse el precio desde que hablaron, ni lo que falla el factor del
mercado cuando el precio es estimado. Acá se suma esa incertidumbre:

- antigüedad: +2 % del precio por semana desde la observación más
  reciente, con tope de 15 % (un mercado se mueve, pero no sin límite);
- estimado: +5 %, porque el factor del local se aprendió con pocos datos.

El centro NO se toca: el orden entre mercados queda igual. Solo cambia lo
que se dice de cuán seguro es. Es dominio puro: recibe "hoy", no lo lee.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date

from src.dominio.modelo.precio_consolidado import PrecioConsolidado, RangoPrecio

POR_SEMANA = 0.02
TOPE_ANTIGUEDAD = 0.15
POR_ESTIMADO = 0.05


def fecha_de_referencia(p: PrecioConsolidado) -> date:
    """La fecha del dato; si no se conoce, el primer día del período (lo más conservador)."""
    if p.fecha_observacion_mas_reciente is not None:
        return p.fecha_observacion_mas_reciente
    return date(p.periodo.anio, p.periodo.mes or 1, p.periodo.dia or 1)


def rango_honesto(p: PrecioConsolidado, hoy: date) -> PrecioConsolidado:
    dias = max((hoy - fecha_de_referencia(p)).days, 0)
    por_antiguedad = min(POR_SEMANA * dias / 7, TOPE_ANTIGUEDAD)
    motivos: list[str] = []
    if por_antiguedad >= 0.005:
        motivos.append(f"El dato tiene {dias} días: +{por_antiguedad:.0%}")
    extra = por_antiguedad
    if p.es_estimado:
        extra += POR_ESTIMADO
        motivos.append(f"Es estimado: +{POR_ESTIMADO:.0%} por el factor del mercado")
    if not motivos:
        return replace(p, antiguedad_dias=dias)
    centro = p.rango.centro
    mitad = (p.rango.maximo - p.rango.minimo) / 2 + centro * extra
    return replace(
        p,
        rango=RangoPrecio(round(max(centro - mitad, 0.0), 2), round(centro + mitad, 2)),
        antiguedad_dias=dias,
        motivos_rango=motivos,
    )


def empatan(a: RangoPrecio, b: RangoPrecio) -> bool:
    """
    Dos precios empatan cuando la diferencia entre ellos es menor que la
    incertidumbre de alguno: el centro de uno cae dentro del rango del
    otro. Decir que uno "gana" por 20 centavos con un error de 1 Bs es
    inventar un ganador.
    """
    return a.minimo <= b.centro <= a.maximo or b.minimo <= a.centro <= b.maximo
