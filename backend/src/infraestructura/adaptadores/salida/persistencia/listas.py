"""
Listas de compras sobre SQLAlchemy. Implementa RepositorioListas.

Las dos tablas son auditadas: al editar una lista, los renglones que se
quitaron no se borran, se marcan eliminados; los que siguen se actualizan
en su lugar. Así queda el rastro de qué tenía la lista y quién la cambió.
"""
from __future__ import annotations

from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from src.infraestructura.adaptadores.salida.persistencia.sesion import sesion_de
from src.infraestructura.adaptadores.salida.persistencia.tablas import ItemListaTabla, ListaComprasTabla
from src.dominio.modelo import ItemLista, ListaCompras, Presentacion


def _items_vigentes(s: Session, id_lista: int) -> list[ItemListaTabla]:
    return list(s.scalars(
        select(ItemListaTabla)
        .where(ItemListaTabla.id_lista == id_lista, ItemListaTabla.eliminado.is_(False))
        .order_by(ItemListaTabla.id)
    ))


def _a_lista(s: Session, f: ListaComprasTabla) -> ListaCompras:
    creado = f.creado_en
    if creado is not None and creado.tzinfo is None:
        creado = creado.replace(tzinfo=timezone.utc)
    return ListaCompras(
        id=f.id,
        id_usuario=f.id_usuario,
        nombre=f.nombre,
        creado_en=creado,
        items=tuple(
            ItemLista(i.codigo_producto, i.cantidad, Presentacion(i.presentacion))
            for i in _items_vigentes(s, f.id)
        ),
    )


class ListasPostgres:
    def __init__(self, fabrica: sessionmaker[Session]):
        self._fabrica = fabrica

    def obtener(self, id_lista: int) -> ListaCompras | None:
        with sesion_de(self._fabrica) as s:
            fila = s.get(ListaComprasTabla, id_lista)
            return _a_lista(s, fila) if fila is not None and not fila.eliminado else None

    def listar_de(self, id_usuario: int) -> list[ListaCompras]:
        with sesion_de(self._fabrica) as s:
            filas = s.scalars(
                select(ListaComprasTabla)
                .where(ListaComprasTabla.id_usuario == id_usuario, ListaComprasTabla.eliminado.is_(False))
                .order_by(ListaComprasTabla.id)
            )
            return [_a_lista(s, f) for f in filas]

    def guardar(self, lista: ListaCompras) -> ListaCompras:
        with sesion_de(self._fabrica) as s:
            fila = s.get(ListaComprasTabla, lista.id) if lista.id is not None else None
            if fila is None:
                fila = ListaComprasTabla(id_usuario=lista.id_usuario)
                s.add(fila)
            fila.nombre = lista.nombre
            s.flush()

            anteriores = {i.codigo_producto: i for i in _items_vigentes(s, fila.id)}
            for item in lista.items:
                renglon = anteriores.pop(item.codigo_producto, None)
                if renglon is None:
                    renglon = ItemListaTabla(id_lista=fila.id, codigo_producto=item.codigo_producto)
                    s.add(renglon)
                renglon.cantidad = item.cantidad
                renglon.presentacion = item.presentacion.value
            for quitado in anteriores.values():
                quitado.eliminado = True
            s.flush()
            return _a_lista(s, fila)

    def eliminar(self, id_lista: int) -> None:
        with sesion_de(self._fabrica) as s:
            fila = s.get(ListaComprasTabla, id_lista)
            if fila is not None:
                fila.eliminado = True
