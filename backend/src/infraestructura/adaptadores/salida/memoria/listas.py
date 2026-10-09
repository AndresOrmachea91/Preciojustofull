"""Listas de compras en memoria: el mismo puerto que ListasPostgres."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from src.dominio.modelo import ListaCompras


class ListasEnMemoria:
    def __init__(self):
        self._datos: dict[int, ListaCompras] = {}
        self._siguiente = 1

    def obtener(self, id_lista: int) -> ListaCompras | None:
        return self._datos.get(id_lista)

    def listar_de(self, id_usuario: int) -> list[ListaCompras]:
        return sorted((l for l in self._datos.values() if l.id_usuario == id_usuario), key=lambda l: l.id)

    def guardar(self, lista: ListaCompras) -> ListaCompras:
        if lista.id is None:
            lista = replace(lista, id=self._siguiente, creado_en=datetime.now(timezone.utc))
            self._siguiente += 1
        self._datos[lista.id] = lista
        return lista

    def eliminar(self, id_lista: int) -> None:
        self._datos.pop(id_lista, None)
