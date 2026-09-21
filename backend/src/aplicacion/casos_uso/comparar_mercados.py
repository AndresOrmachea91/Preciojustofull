from __future__ import annotations

from src.aplicacion.puertos.entrada import PrecioEnMercado
from src.aplicacion.puertos.salida import (
    RepositorioMercados,
    RepositorioObservaciones,
    RepositorioProductos,
)
from src.dominio.excepciones import ProductoNoEncontrado, SinObservaciones
from src.dominio.modelo import Mercado, Observacion, PrecioConsolidado
from src.dominio.servicio.motor_fusion import MotorFusion
from src.dominio.valor import NivelPrecio

CIUDAD_POR_DEFECTO = "la_paz"


def precio_del_local(
    motor: MotorFusion,
    mercado: Mercado,
    locales: list[Observacion],
    referencia_ciudad: list[Observacion],
) -> PrecioConsolidado | None:
    """
    El precio de un local, con su procedencia:
    - OBSERVADO si alguien midió en ese local (grupo más reciente);
    - ESTIMADO desde la referencia de ciudad del mismo nivel y el
      factor_mercado, si nadie midió ahí todavía;
    - None si no hay ni lo uno ni lo otro. No se inventa.
    """
    locales = [o for o in locales if o.nivel is mercado.nivel_precio]
    if locales:
        try:
            return motor.consolidar_grupos(locales)[0]
        except SinObservaciones:
            pass
    referencia = [o for o in referencia_ciudad if o.nivel is mercado.nivel_precio]
    grupos = motor.agrupar(referencia)
    if not grupos:
        return None
    mas_reciente = next(iter(grupos.values()))
    return motor.estimar_desde_ciudad(mas_reciente, mercado)


class CompararMercadosCasoUso:
    """
    Mismo producto en varios puntos de venta, ordenado de más barato a más
    caro DENTRO de cada nivel de precio. Un mayorista y un puesto no
    compiten: se devuelven con su nivel para que quien muestre los separe.
    """

    def __init__(
        self,
        productos: RepositorioProductos,
        mercados: RepositorioMercados,
        observaciones: RepositorioObservaciones,
        motor: MotorFusion | None = None,
        ciudad: str = CIUDAD_POR_DEFECTO,
    ):
        self._productos = productos
        self._mercados = mercados
        self._observaciones = observaciones
        self._motor = motor or MotorFusion()
        self._ciudad = ciudad

    def ejecutar(self, codigo_producto: str, zona: str | None = None) -> list[PrecioEnMercado]:
        if self._productos.obtener(codigo_producto) is None:
            raise ProductoNoEncontrado(codigo_producto)

        # UNA consulta por producto, no una por mercado: contra una base remota
        # 88 viajes de medio segundo son casi un minuto. Se agrupa en memoria.
        todas = self._observaciones.buscar(codigo_producto)
        referencia = [o for o in todas if o.es_referencia_de_ciudad and o.ciudad == self._ciudad]
        locales_por_mercado: dict[str, list[Observacion]] = {}
        for o in todas:
            if o.codigo_mercado is not None:
                locales_por_mercado.setdefault(o.codigo_mercado, []).append(o)

        resultado: list[PrecioEnMercado] = []
        for mercado in self._mercados.listar(zona):
            locales = locales_por_mercado.get(mercado.codigo, [])
            precio = precio_del_local(self._motor, mercado, locales, referencia)
            if precio is None:
                continue   # sin medición ni referencia: se omite, no se inventa
            resultado.append(
                PrecioEnMercado(
                    codigo_mercado=mercado.codigo,
                    nombre_mercado=mercado.nombre,
                    tipo=mercado.tipo.value,
                    zona=mercado.zona,
                    precio=precio,
                    nivel_precio=mercado.nivel_precio.value,
                )
            )

        orden_nivel = {NivelPrecio.MINORISTA.value: 0, NivelPrecio.MAYORISTA.value: 1}
        resultado.sort(key=lambda p: (orden_nivel[p.nivel_precio], p.precio.rango.centro))
        return resultado

