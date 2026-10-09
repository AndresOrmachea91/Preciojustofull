"""
El vendedor publica el precio de un producto en SU puesto o tienda.

Se publica al instante (decisión 13 del 8 de octubre), pero nunca como un
dato más: entra con fuente VENDEDOR, que el motor de fusión pesa como
"declarado por quien vende" frente al SIIP, al campo y a los reportes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.aplicacion.casos_uso.cuentas.permisos import exigir
from src.aplicacion.puertos.salida import (
    EscritorObservaciones, LectorMercados, LectorProductos, LectorPublicacionesPuntoVenta,
)
from src.dominio.excepciones import (
    DatoInvalido, MercadoNoEncontrado, PresentacionInvalida, ProductoNoEncontrado, SinPuntoVenta,
)
from src.dominio.modelo import Fuente, Mercado, Observacion, Permiso, Presentacion, Producto, Usuario
from src.dominio.valor import Dinero, Periodo, TipoPrecio, Unidad


@dataclass(frozen=True, slots=True)
class PrecioPublicado:
    """El último precio que el vendedor publicó de un producto."""

    producto: Producto
    monto: float
    presentacion: str
    precio_por_unidad_base: float
    publicado_en: datetime


def _puesto_del(vendedor: Usuario, mercados: LectorMercados) -> Mercado:
    if not vendedor.codigo_punto_venta:
        raise SinPuntoVenta()
    puesto = mercados.obtener(vendedor.codigo_punto_venta)
    if puesto is None:
        # El puesto se eliminó del catálogo después de asignarlo.
        raise MercadoNoEncontrado(vendedor.codigo_punto_venta)
    return puesto


class PublicarPrecioPropio:
    def __init__(self, productos: LectorProductos, mercados: LectorMercados,
                 observaciones: EscritorObservaciones):
        self._productos = productos
        self._mercados = mercados
        self._observaciones = observaciones

    def ejecutar(self, vendedor: Usuario, codigo_producto: str, monto: float,
                 presentacion: Presentacion) -> Observacion:
        exigir(vendedor, Permiso.PUBLICAR_PRECIO_PROPIO)
        puesto = _puesto_del(vendedor, self._mercados)
        producto = self._productos.obtener(codigo_producto)
        if producto is None:
            raise ProductoNoEncontrado(codigo_producto)
        if presentacion not in producto.presentaciones:
            raise PresentacionInvalida(f"{producto.nombre} no se vende por {presentacion.value}")
        if monto <= 0:
            raise DatoInvalido("El precio tiene que ser mayor a cero")

        ahora = datetime.now(timezone.utc)
        observacion = Observacion(
            fuente=Fuente.VENDEDOR,
            # Un mayorista declara precio mayorista: el nivel lo da el puesto.
            nivel=puesto.nivel_precio,
            codigo_producto=producto.codigo,
            codigo_mercado=puesto.codigo,
            periodo=Periodo(ahora.year, ahora.month, ahora.day),
            # "QUINTAL", "MAPLE"...: el mismo texto que entiende el lector de
            # unidades, así se convierte a la unidad base como todo lo demás.
            precio=Dinero(monto, Unidad(presentacion.value.upper())),
            capturada_en=ahora,
            fecha_observacion=ahora.date(),
            tipo_precio=TipoPrecio.ANUNCIADO,
            evidencia=f"vendedor:{vendedor.id}",
        )
        self._observaciones.guardar_varias([observacion])
        return observacion


class MisPrecios:
    """Lo último que el vendedor publicó de cada producto, para ver y corregir."""

    def __init__(self, productos: LectorProductos, mercados: LectorMercados,
                 publicaciones: LectorPublicacionesPuntoVenta):
        self._productos = productos
        self._mercados = mercados
        self._publicaciones = publicaciones

    def ejecutar(self, vendedor: Usuario) -> list[PrecioPublicado]:
        exigir(vendedor, Permiso.PUBLICAR_PRECIO_PROPIO)
        puesto = _puesto_del(vendedor, self._mercados)
        ultimos: dict[str, PrecioPublicado] = {}
        # Vienen del más nuevo al más viejo: el primero de cada producto gana.
        for o in self._publicaciones.publicadas_en(puesto.codigo, Fuente.VENDEDOR):
            if o.codigo_producto in ultimos:
                continue
            producto = self._productos.obtener(o.codigo_producto)
            if producto is None:
                continue
            ultimos[o.codigo_producto] = PrecioPublicado(
                producto=producto,
                monto=o.precio.monto,
                presentacion=o.precio.unidad.texto.lower(),
                precio_por_unidad_base=o.precio_canonico(),
                publicado_en=o.capturada_en,
            )
        return sorted(ultimos.values(), key=lambda p: p.producto.nombre)
