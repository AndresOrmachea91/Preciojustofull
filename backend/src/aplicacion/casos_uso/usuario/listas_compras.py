"""
Listas de compras del usuario: crearlas, editarlas, borrarlas y cotizarlas
(en qué mercado sale más barata la lista completa).

Cotizar no repite lógica: lleva cada renglón a la unidad base del producto
(2 arrobas de papa = 23 kg) y le pide el cálculo al caso de uso de la
canasta, a través de su puerto de entrada.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.aplicacion.casos_uso.cuentas.permisos import exigir
from src.aplicacion.puertos.entrada import CalcularCanasta, CostoCanastaEnMercado, ItemCanasta
from src.aplicacion.puertos.salida import LectorProductos, RepositorioListas
from src.dominio.excepciones import ListaNoEncontrada, ProductoNoEncontrado
from src.dominio.modelo import ItemLista, ListaCompras, Permiso, Presentacion, Usuario


@dataclass(frozen=True, slots=True)
class RenglonPedido:
    """Lo que llega para armar una lista, antes de validarlo."""

    codigo_producto: str
    cantidad: float
    presentacion: Presentacion


class GestionarListas:
    def __init__(self, listas: RepositorioListas, productos: LectorProductos, canasta: CalcularCanasta):
        self._listas = listas
        self._productos = productos
        self._canasta = canasta

    def listar(self, actor: Usuario) -> list[ListaCompras]:
        exigir(actor, Permiso.GESTIONAR_LISTAS)
        return self._listas.listar_de(actor.id)

    def crear(self, actor: Usuario, nombre: str, renglones: list[RenglonPedido]) -> ListaCompras:
        exigir(actor, Permiso.GESTIONAR_LISTAS)
        lista = ListaCompras(id_usuario=actor.id, nombre=nombre.strip(), items=self._items(renglones))
        return self._listas.guardar(lista)

    def actualizar(self, actor: Usuario, id_lista: int, nombre: str,
                   renglones: list[RenglonPedido]) -> ListaCompras:
        exigir(actor, Permiso.GESTIONAR_LISTAS)
        lista = self._propia(actor, id_lista)
        return self._listas.guardar(lista.con(nombre.strip(), self._items(renglones)))

    def eliminar(self, actor: Usuario, id_lista: int) -> None:
        exigir(actor, Permiso.GESTIONAR_LISTAS)
        self._propia(actor, id_lista)
        self._listas.eliminar(id_lista)

    def cotizar(self, actor: Usuario, id_lista: int, zona: str | None = None) -> list[CostoCanastaEnMercado]:
        exigir(actor, Permiso.GESTIONAR_LISTAS)
        lista = self._propia(actor, id_lista)
        if not lista.items:
            return []
        pedido = [ItemCanasta(i.codigo_producto, i.en_unidad_base()) for i in lista.items]
        return self._canasta.ejecutar(pedido, zona)

    def _propia(self, actor: Usuario, id_lista: int) -> ListaCompras:
        lista = self._listas.obtener(id_lista)
        # La lista de otro se responde igual que una que no existe: no se
        # revela qué ids hay.
        if lista is None or not lista.es_de(actor.id):
            raise ListaNoEncontrada(id_lista)
        return lista

    def _items(self, renglones: list[RenglonPedido]) -> tuple[ItemLista, ...]:
        items = []
        for r in renglones:
            producto = self._productos.obtener(r.codigo_producto)
            if producto is None:
                raise ProductoNoEncontrado(r.codigo_producto)
            item = ItemLista(r.codigo_producto, r.cantidad, r.presentacion)
            item.validar_contra(producto)
            items.append(item)
        return tuple(items)
