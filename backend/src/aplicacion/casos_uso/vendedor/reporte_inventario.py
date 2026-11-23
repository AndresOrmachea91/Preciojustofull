"""
El reporte del inventario (C148): lo que la casera necesita revisar hoy y una
sugerencia de precio por producto.

La sugerencia compara su precio con el que el sistema calcula para ese
producto en su mismo mercado, SIN contar los precios que ella misma puso
(si no, se estaría comparando consigo misma). Nunca cambia nada sola: solo
sugiere, y la casera decide si usa el precio sugerido con un toque.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from src.aplicacion.casos_uso.cuentas.permisos import exigir
from src.aplicacion.casos_uso.precios.ofertas_vigentes import informante_de
from src.aplicacion.casos_uso.precios.referencia_sistema import ReferenciaDelSistema
from src.aplicacion.puertos.salida import (
    LectorMercados, LectorObservaciones, LectorProductos, RepositorioInventario, RepositorioPuestos,
)
from src.dominio.excepciones import DatoInvalido
from src.dominio.modelo import ArticuloInventario, Disponibilidad, Permiso, Usuario
from src.dominio.servicio.motor_fusion import MotorFusion

# Hasta este porcentaje arriba o abajo del mercado, el precio se considera "en línea".
TOLERANCIA = 0.08
# Un precio sin tocar en más de estos días probablemente ya no es el de hoy.
DIAS_PARA_REVISAR = 7


@dataclass(frozen=True, slots=True)
class Sugerencia:
    """Qué hacer con el precio de un producto, en palabras de la casera."""
    tipo: str               # "bajar", "subir", "en_linea" o "sin_referencia"
    texto: str
    precio_sugerido: float | None   # en la misma presentación en que ella vende
    precio_mercado: float | None    # el del sistema en su mercado, en esa presentación
    diferencia: float | None        # +0,15 = 15 % más caro que el mercado


@dataclass(frozen=True, slots=True)
class RenglonReporte:
    articulo: ArticuloInventario
    nombre_producto: str
    categoria: str
    unidad_base: str
    sugerencia: Sugerencia
    alertas: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReporteInventario:
    renglones: list[RenglonReporte]
    productos: int
    con_cantidad: int
    valor_total: float
    agotados: int
    queda_poco: int
    para_revisar_precio: int
    sin_actualizar: int
    consejos: list[str] = field(default_factory=list)


def bs(monto: float) -> str:
    return f"{monto:.2f}".replace(".", ",")


def redondear_a_cincuenta(monto: float) -> float:
    """Como se cobra en el mercado: de 50 en 50 centavos (Bs 7,37 → 7,50)."""
    return max(0.5, round(monto * 2) / 2)


def sugerir(monto: float, factor: float, precio_unidad_base_mercado: float | None, nombre_presentacion: str) -> Sugerencia:
    if not precio_unidad_base_mercado:
        return Sugerencia("sin_referencia", "Todavía no hay un precio del mercado para comparar.", None, None, None)
    mercado = round(precio_unidad_base_mercado * factor, 2)
    diferencia = round(monto / mercado - 1, 4)
    sugerido = redondear_a_cincuenta(mercado)
    por = nombre_presentacion.lower()
    if diferencia > TOLERANCIA:
        return Sugerencia("bajar", f"Está {round(diferencia * 100)} % más caro que en su mercado. "
                                   f"A Bs {bs(sugerido)} por {por} llegaría a más compradores.",
                          sugerido, mercado, diferencia)
    if diferencia < -TOLERANCIA * 2:
        return Sugerencia("subir", f"Está {round(-diferencia * 100)} % más barato que en su mercado: podría "
                                   f"cobrar hasta Bs {bs(sugerido)} y seguir siendo de los más baratos.",
                          sugerido, mercado, diferencia)
    if diferencia < -TOLERANCIA:
        return Sugerencia("en_linea", f"Está {round(-diferencia * 100)} % más barato que el mercado: buen precio "
                                      "para destacar con una oferta.", None, mercado, diferencia)
    return Sugerencia("en_linea", "Su precio está en línea con el mercado.", None, mercado, diferencia)


class ReporteDelInventario:
    def __init__(self, productos: LectorProductos, mercados: LectorMercados, observaciones: LectorObservaciones,
                 motor: MotorFusion, puestos: RepositorioPuestos, inventario: RepositorioInventario,
                 reloj: Callable[[], object] | None = None, ahora: Callable[[], datetime] | None = None):
        self._productos = productos
        self._mercados = mercados
        self._observaciones = observaciones
        self._motor = motor
        self._puestos = puestos
        self._inventario = inventario
        self._reloj = reloj
        self._ahora = ahora or (lambda: datetime.now(timezone.utc))

    def ejecutar(self, vendedor: Usuario) -> ReporteInventario:
        exigir(vendedor, Permiso.PUBLICAR_PRECIO_PROPIO)
        puesto = self._puestos.del_vendedor(vendedor.id)
        if puesto is None:
            raise DatoInvalido("Primero registre su puesto: el reporte es de su inventario")
        mercado = self._mercados.obtener(puesto.codigo_mercado)
        referencia = ReferenciaDelSistema(self._productos, self._observaciones, self._motor, reloj=self._reloj)
        ahora = self._ahora()
        renglones: list[RenglonReporte] = []
        for articulo in sorted(self._inventario.del_puesto(puesto.id), key=lambda a: a.codigo_producto):
            producto = self._productos.obtener(articulo.codigo_producto)
            if producto is None:
                continue
            sistema = (referencia.precio(producto.codigo, mercado, sin_informante=informante_de(vendedor.id))
                       if mercado is not None else None)
            sugerencia = sugerir(articulo.monto, articulo.presentacion.factor,
                                 sistema.rango.centro if sistema else None, articulo.presentacion.nombre)
            alertas: list[str] = []
            if articulo.disponibilidad is Disponibilidad.AGOTADO:
                alertas.append("Se acabó: los compradores lo ven como agotado.")
            elif articulo.disponibilidad is Disponibilidad.POCO:
                alertas.append("Queda poco: conviene reponer.")
            if articulo.actualizado_en and ahora - articulo.actualizado_en > timedelta(days=DIAS_PARA_REVISAR):
                dias = (ahora - articulo.actualizado_en).days
                alertas.append(f"No lo actualiza hace {dias} días: confirme que el precio sigue igual.")
            renglones.append(RenglonReporte(articulo, producto.nombre, producto.categoria.value,
                                            producto.unidad_base.value, sugerencia, tuple(alertas)))
        con_cantidad = [r for r in renglones if r.articulo.cantidad is not None]
        agotados = sum(r.articulo.disponibilidad is Disponibilidad.AGOTADO for r in renglones)
        poco = sum(r.articulo.disponibilidad is Disponibilidad.POCO for r in renglones)
        revisar = sum(r.sugerencia.tipo in ("bajar", "subir") for r in renglones)
        viejos = sum(any("No lo actualiza" in a for a in r.alertas) for r in renglones)
        return ReporteInventario(
            renglones=renglones, productos=len(renglones), con_cantidad=len(con_cantidad),
            valor_total=round(sum(r.articulo.valor or 0 for r in con_cantidad), 2),
            agotados=agotados, queda_poco=poco, para_revisar_precio=revisar, sin_actualizar=viejos,
            consejos=_consejos(renglones, agotados, poco, revisar, len(con_cantidad)),
        )


def _consejos(renglones: list[RenglonReporte], agotados: int, poco: int, revisar: int, con_cantidad: int) -> list[str]:
    """Dos o tres frases cortas con lo más importante del día."""
    consejos: list[str] = []
    if not renglones:
        return ["Agregue los productos que vende: así aparece en el plan de compra de quien los busca."]
    if agotados:
        consejos.append(f"Tiene {agotados} producto{'s' if agotados > 1 else ''} agotado{'s' if agotados > 1 else ''}. "
                        "Si ya repuso, súmele la cantidad para que vuelva a aparecer.")
    if poco:
        consejos.append(f"{poco} producto{'s' if poco > 1 else ''} se está{'n' if poco > 1 else ''} acabando.")
    if revisar:
        consejos.append(f"Revise el precio de {revisar} producto{'s' if revisar > 1 else ''}: "
                        "hay una sugerencia al lado de cada uno.")
    baratos = [r for r in renglones if r.sugerencia.diferencia is not None and r.sugerencia.diferencia < -TOLERANCIA]
    if baratos:
        consejos.append(f"Su {baratos[0].nombre_producto.lower()} está más barato que en su mercado: publíquelo como "
                        "oferta y llegará a más gente.")
    if con_cantidad < len(renglones):
        consejos.append("Anote cuánto le queda de cada producto: el sistema le avisará antes de que se acabe.")
    return consejos[:3] or ["Todo en orden: sus precios están en línea y no le falta nada."]
