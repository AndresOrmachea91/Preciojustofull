"""
Qué conviene ir a medir primero (A4230, recolección adaptativa) y cuánto se
mueve el precio de cada producto (A5020).

Una ronda de campo tiene horas contadas. En vez de medir todo por igual,
se mide primero lo que más incertidumbre le saca al sistema:

- lo que NADIE midió en un lugar concreto (hoy, casi todo es estimado);
- lo que se midió hace tanto que ya caducó para ese producto (un tomate
  de hace dos semanas ya no dice nada; un arroz sí);
- lo que más se mueve de un mes a otro en la ciudad, porque una estimación
  de algo que cambia mucho se equivoca más;
- lo que tiene el rango más ancho, porque ahí la gente ve menos certeza.

Puntaje de un producto = (cambio mensual típico + ancho relativo del rango)
x proporción de lugares sin un dato vigente. Es una regla simple y
explicable a propósito: la tesis compara este orden contra el calendario
fijo (A5040), y una caja negra no se podría defender.

Los lugares se sugieren de menos a más cubiertos y repartidos por
macrodistrito, para que una ronda cubra la ciudad y no un solo barrio.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from statistics import median

from src.aplicacion.casos_uso.precios.referencia_sistema import ReferenciaDelSistema
from src.aplicacion.puertos.salida import LectorMercados, LectorObservaciones, LectorProductos
from src.dominio.modelo import Mercado, Observacion, Producto
from src.dominio.servicio.motor_fusion import MotorFusion
from src.dominio.valor import NivelPrecio

# Meses de la serie de la ciudad con que se mide cuánto se mueve un precio.
MESES_DE_VARIACION = 12
# Con menos meses que esto no se dice cuánto varía: sería adivinar.
MESES_MINIMOS = 3


@dataclass(frozen=True, slots=True)
class VariacionDeProducto:
    """Cuánto se movió el precio de la ciudad mes a mes (A5020)."""

    producto: Producto
    # Cambio mensual típico: la media de |precio del mes / mes anterior - 1|.
    cambio_mensual: float
    # Mayor subida y mayor bajada de un mes al siguiente, en el periodo.
    mayor_subida: float
    mayor_bajada: float
    meses: int
    nivel: str


@dataclass(frozen=True, slots=True)
class PrioridadDeProducto:
    producto: Producto
    puntaje: float
    lugares_sin_dato: int
    lugares_con_dato_viejo: int
    lugares_al_dia: int
    cambio_mensual: float | None
    ancho_relativo: float | None
    motivos: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class LugarPorVisitar:
    mercado: Mercado
    productos_al_dia: int
    productos_total: int

    @property
    def cobertura(self) -> float:
        return self.productos_al_dia / self.productos_total if self.productos_total else 0.0


@dataclass(frozen=True, slots=True)
class PlanDeVerificacion:
    productos: list[PrioridadDeProducto]
    lugares: list[LugarPorVisitar]
    variaciones: list[VariacionDeProducto]
    fecha: date


class PriorizarVerificaciones:
    def __init__(self, productos: LectorProductos, mercados: LectorMercados, observaciones: LectorObservaciones,
                 motor: MotorFusion, reloj: Callable[[], date] | None = None):
        self._productos = productos
        self._mercados = mercados
        self._observaciones = observaciones
        self._motor = motor
        self._reloj = reloj

    def ejecutar(self) -> PlanDeVerificacion:
        hoy = self._reloj() if self._reloj else date.today()
        # Solo los lugares de consumo final: la ronda de campo mide lo que paga una familia.
        lugares = [m for m in self._mercados.listar() if m.nivel_precio is NivelPrecio.MINORISTA]
        referencia = ReferenciaDelSistema(self._productos, self._observaciones, self._motor, reloj=self._reloj)
        al_dia_por_lugar = {m.codigo: 0 for m in lugares}
        productos = self._productos.listar()

        prioridades: list[PrioridadDeProducto] = []
        variaciones: list[VariacionDeProducto] = []
        for producto in productos:
            todas = referencia.observaciones(producto.codigo)
            variacion = variacion_mensual(producto, todas)
            if variacion is not None:
                variaciones.append(variacion)

            vigencia = hoy - timedelta(days=producto.dias_conservacion)
            ultima: dict[str, date] = {}
            for o in todas:
                if o.codigo_mercado and not o.es_referencia_de_ciudad:
                    cuando = fecha_de(o)
                    if o.codigo_mercado not in ultima or cuando > ultima[o.codigo_mercado]:
                        ultima[o.codigo_mercado] = cuando
            sin_dato = viejo = al_dia = 0
            for m in lugares:
                fecha = ultima.get(m.codigo)
                if fecha is None:
                    sin_dato += 1
                elif fecha < vigencia:
                    viejo += 1
                else:
                    al_dia += 1
                    al_dia_por_lugar[m.codigo] += 1

            ancho = None
            if lugares:
                ciudad = referencia.de_la_ciudad(producto.codigo, lugares[0])
                if ciudad and ciudad.rango.centro:
                    ancho = round((ciudad.rango.maximo - ciudad.rango.minimo) / ciudad.rango.centro, 4)
            cambio = variacion.cambio_mensual if variacion else None
            prioridades.append(PrioridadDeProducto(
                producto=producto, puntaje=0.0, lugares_sin_dato=sin_dato,
                lugares_con_dato_viejo=viejo, lugares_al_dia=al_dia, cambio_mensual=cambio,
                ancho_relativo=ancho, motivos=_motivos(sin_dato, viejo, len(lugares), cambio, ancho),
            ))

        prioridades = puntuar(prioridades, len(lugares))
        prioridades.sort(key=lambda p: (-p.puntaje, p.producto.nombre))
        variaciones.sort(key=lambda v: (-v.cambio_mensual, v.producto.nombre))
        visitas = [LugarPorVisitar(m, al_dia_por_lugar[m.codigo], len(productos)) for m in lugares]
        return PlanDeVerificacion(prioridades, repartir_por_macrodistrito(visitas), variaciones, hoy)


def fecha_de(o: Observacion) -> date:
    """La fecha del dato; si no la trae, cuándo lo supimos (igual que la ficha del mercado)."""
    return o.fecha_observacion or o.capturada_en.date()


def variacion_mensual(producto: Producto, observaciones: list[Observacion]) -> VariacionDeProducto | None:
    """
    El cambio de un mes al siguiente en la referencia de la ciudad. Se prefiere
    el precio al consumidor; si la ciudad solo publica el mayorista, ese.
    """
    for nivel in (NivelPrecio.MINORISTA, NivelPrecio.MAYORISTA):
        por_mes: dict[tuple[int, int], list[float]] = {}
        for o in observaciones:
            if o.es_referencia_de_ciudad and o.nivel is nivel and o.periodo.mes is not None:
                por_mes.setdefault((o.periodo.anio, o.periodo.mes), []).append(o.precio_canonico())
        meses = sorted(por_mes)[-(MESES_DE_VARIACION + 1):]
        if len(meses) < MESES_MINIMOS:
            continue
        serie = [median(por_mes[m]) for m in meses]
        cambios = [actual / anterior - 1 for anterior, actual in zip(serie, serie[1:]) if anterior > 0]
        if not cambios:
            continue
        return VariacionDeProducto(
            producto=producto,
            cambio_mensual=round(sum(abs(c) for c in cambios) / len(cambios), 4),
            mayor_subida=round(max(0.0, max(cambios)), 4),
            mayor_bajada=round(min(0.0, min(cambios)), 4),
            meses=len(serie),
            nivel=nivel.value,
        )
    return None


def repartir_por_macrodistrito(lugares: list[LugarPorVisitar]) -> list[LugarPorVisitar]:
    """
    De menos a más cubiertos, pero turnándose entre macrodistritos: si los 66
    mercados empatan en cero, la ronda no se queda en un solo barrio.
    """
    grupos: dict[str, list[LugarPorVisitar]] = {}
    for lugar in sorted(lugares, key=lambda x: (x.cobertura, x.mercado.tipo.value != "mercado", x.mercado.nombre)):
        grupos.setdefault(lugar.mercado.macrodistrito or lugar.mercado.zona, []).append(lugar)
    salida: list[LugarPorVisitar] = []
    while any(grupos.values()):
        # En cada vuelta, el menos cubierto de cada macrodistrito; entre ellos, el menos cubierto primero.
        vuelta = sorted((g.pop(0) for g in grupos.values() if g),
                        key=lambda x: (x.cobertura, x.mercado.tipo.value != "mercado", x.mercado.nombre))
        salida.extend(vuelta)
    return salida


def puntuar(prioridades: list[PrioridadDeProducto], lugares: int) -> list[PrioridadDeProducto]:
    """
    Puntaje = incertidumbre x proporción de lugares sin un dato vigente. La
    incertidumbre es el cambio mensual típico más el ancho relativo del
    rango. Sin serie ni rango no hay con qué medirla: se toma la típica de
    los demás, para no esconder ese producto al final.
    """
    conocidas = [(p.cambio_mensual or 0.0) + (p.ancho_relativo or 0.0) for p in prioridades
                 if p.cambio_mensual is not None or p.ancho_relativo is not None]
    tipica = median(conocidas) if conocidas else 1.0
    salida = []
    for p in prioridades:
        sin_medida = p.cambio_mensual is None and p.ancho_relativo is None
        incertidumbre = tipica if sin_medida else (p.cambio_mensual or 0.0) + (p.ancho_relativo or 0.0)
        faltante = (p.lugares_sin_dato + p.lugares_con_dato_viejo) / lugares if lugares else 0.0
        motivos = [*p.motivos, "sin serie de la ciudad: no se sabe cuánto varía"] if sin_medida and faltante else p.motivos
        salida.append(replace(p, puntaje=round(incertidumbre * faltante, 4), motivos=motivos))
    return salida


def _motivos(sin_dato: int, viejo: int, total: int, cambio: float | None, ancho: float | None) -> list[str]:
    motivos = []
    if total and sin_dato == total:
        motivos.append("nadie lo midió todavía en ningún lugar")
    elif sin_dato:
        motivos.append(f"sin medir en {sin_dato} de {total} lugares")
    if viejo:
        motivos.append(f"dato vencido en {viejo} {'lugar' if viejo == 1 else 'lugares'}")
    if cambio is not None and cambio >= 0.03:
        motivos.append(f"cambia en promedio {cambio * 100:.0f} % de un mes a otro")
    if ancho is not None and ancho >= 0.2:
        motivos.append(f"rango ancho ({ancho * 100:.0f} % del precio)")
    return motivos
