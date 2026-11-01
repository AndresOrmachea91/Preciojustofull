"""
El inventario del puesto (C137): qué vende el casero, a cuánto y si le
queda. Lo maneja desde el celular.

Cuando el precio cambia (o es nuevo), se publica además como su precio
declarado (PublicarPrecioPropio, fuente VENDEDOR): así el inventario y el
mapa no se contradicen, y el motor de fusión lo pesa como declarado. Si
solo cambia la disponibilidad ("se acabó"), no se publica nada: no es un
precio nuevo.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from src.aplicacion.casos_uso.cuentas.permisos import exigir
from src.aplicacion.casos_uso.vendedor.publicar_precio import PublicarPrecioPropio
from src.aplicacion.puertos.salida import LectorProductos, RepositorioInventario, RepositorioPuestos
from src.dominio.excepciones import DatoInvalido, PresentacionInvalida, ProductoNoEncontrado
from src.dominio.modelo import ArticuloInventario, Disponibilidad, Permiso, Presentacion, Puesto, Usuario


class InventarioDelPuesto:
    def __init__(self, productos: LectorProductos, puestos: RepositorioPuestos, inventario: RepositorioInventario,
                 publicar: PublicarPrecioPropio | None = None,
                 ahora: Callable[[], datetime] | None = None):
        self._productos = productos
        self._puestos = puestos
        self._inventario = inventario
        self._publicar = publicar
        self._ahora = ahora or (lambda: datetime.now(timezone.utc))

    def producto(self, codigo: str):
        """El producto del catálogo, para mostrar su nombre junto al artículo."""
        producto = self._productos.obtener(codigo)
        if producto is None:
            raise ProductoNoEncontrado(codigo)
        return producto

    def ver(self, vendedor: Usuario) -> list[ArticuloInventario]:
        puesto = self._puesto(vendedor)
        return sorted(self._inventario.del_puesto(puesto.id), key=lambda a: a.codigo_producto)

    def guardar(self, vendedor: Usuario, codigo_producto: str, monto: float, presentacion: Presentacion,
                disponibilidad: Disponibilidad = Disponibilidad.HAY) -> ArticuloInventario:
        puesto = self._puesto(vendedor)
        producto = self._productos.obtener(codigo_producto)
        if producto is None:
            raise ProductoNoEncontrado(codigo_producto)
        if presentacion not in producto.presentaciones:
            raise PresentacionInvalida(f"{producto.nombre} no se vende por {presentacion.value}")
        anterior = next((a for a in self._inventario.del_puesto(puesto.id) if a.codigo_producto == codigo_producto),
                        None)
        articulo = self._inventario.guardar(ArticuloInventario(
            id_puesto=puesto.id, codigo_producto=codigo_producto, monto=round(monto, 2), presentacion=presentacion,
            disponibilidad=disponibilidad, actualizado_en=self._ahora(), id=anterior.id if anterior else None,
        ))
        precio_nuevo = anterior is None or (anterior.monto, anterior.presentacion) != (articulo.monto, presentacion)
        if self._publicar is not None and precio_nuevo and disponibilidad.se_puede_comprar:
            self._publicar.ejecutar(vendedor, codigo_producto, articulo.monto, presentacion)
        return articulo

    def quitar(self, vendedor: Usuario, codigo_producto: str) -> None:
        puesto = self._puesto(vendedor)
        self._inventario.quitar(puesto.id, codigo_producto)

    def _puesto(self, vendedor: Usuario) -> Puesto:
        exigir(vendedor, Permiso.PUBLICAR_PRECIO_PROPIO)
        puesto = self._puestos.del_vendedor(vendedor.id)
        if puesto is None:
            raise DatoInvalido("Primero registre su puesto: el inventario es de su puesto")
        return puesto
