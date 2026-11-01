"""
Los puestos de un mercado, con su foto y lo que tienen (C137). Es lo que
muestra la ventana del mapa al tocar un mercado: "Mercado Lanza, puesto 3,
Doña Rosa: tomate Bs 12 el kilo, papa Bs 80 la arroba".

No todos los mercados ni todos los puestos venden lo mismo, así que cada
puesto muestra SU inventario. Con un producto elegido en el mapa, primero
van los puestos que lo tienen, y de cada uno se muestra ese precio arriba.
Lo agotado va al final de su lista, visible: "se acabó" también sirve.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.aplicacion.puertos.salida import (
    LectorMercados, LectorProductos, RepositorioInventario, RepositorioPuestos,
)
from src.dominio.excepciones import MercadoNoEncontrado
from src.dominio.modelo import ArticuloInventario, Mercado, Producto, Puesto


@dataclass(frozen=True, slots=True)
class ArticuloVisible:
    articulo: ArticuloInventario
    producto: Producto


@dataclass(frozen=True, slots=True)
class PuestoConInventario:
    puesto: Puesto
    articulos: list[ArticuloVisible] = field(default_factory=list)
    # Cuántos artículos tiene en total (la lista puede venir recortada).
    total: int = 0

    @property
    def tiene(self) -> set[str]:
        return {a.producto.codigo for a in self.articulos if a.articulo.disponibilidad.se_puede_comprar}


@dataclass(frozen=True, slots=True)
class PuestosDeUnMercado:
    mercado: Mercado
    puestos: list[PuestoConInventario]


class PuestosDelMercado:
    def __init__(self, mercados: LectorMercados, productos: LectorProductos, puestos: RepositorioPuestos,
                 inventario: RepositorioInventario):
        self._mercados = mercados
        self._productos = productos
        self._puestos = puestos
        self._inventario = inventario

    def ejecutar(self, codigo_mercado: str, producto: str | None = None,
                 articulos_por_puesto: int | None = None) -> PuestosDeUnMercado:
        mercado = self._mercados.obtener(codigo_mercado)
        if mercado is None:
            raise MercadoNoEncontrado(codigo_mercado)
        # Un mercado con sectores: los puestos de los sectores también son suyos.
        codigos = [mercado.codigo] + [m.codigo for m in self._mercados.listar() if m.codigo_padre == mercado.codigo]
        puestos = [p for c in codigos for p in self._puestos.del_mercado(c)]
        inventarios = self._inventario.de_puestos([p.id for p in puestos if p.id is not None])
        catalogo: dict[str, Producto | None] = {}

        salida = []
        for p in puestos:
            visibles = []
            for a in inventarios.get(p.id, []):
                if a.codigo_producto not in catalogo:
                    catalogo[a.codigo_producto] = self._productos.obtener(a.codigo_producto)
                if catalogo[a.codigo_producto] is not None:
                    visibles.append(ArticuloVisible(a, catalogo[a.codigo_producto]))
            visibles.sort(key=lambda v: (
                v.producto.codigo != producto,                     # el producto buscado, primero
                not v.articulo.disponibilidad.se_puede_comprar,    # lo agotado, al final
                v.producto.nombre,
            ))
            recortados = visibles[:articulos_por_puesto] if articulos_por_puesto else visibles
            salida.append(PuestoConInventario(p, recortados, len(visibles)))

        salida.sort(key=lambda x: (
            producto is not None and producto not in x.tiene,       # quienes lo tienen, primero
            x.puesto.id_vendedor is None,                           # los atendidos por su casero, antes
            x.total == 0,
        ))
        return PuestosDeUnMercado(mercado, salida)
