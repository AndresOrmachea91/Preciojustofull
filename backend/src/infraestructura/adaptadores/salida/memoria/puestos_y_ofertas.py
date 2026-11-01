"""Puestos y ofertas en memoria: el mismo puerto que la persistencia, para pruebas y para correr sin base."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from src.dominio.modelo import ArticuloInventario, Confirmacion, EstadoOferta, Oferta, Puesto
from src.dominio.modelo.puesto import orden_de_numero


class PuestosEnMemoria:
    def __init__(self, puestos: list[Puesto] | None = None):
        self._datos: dict[int, Puesto] = {}
        self._siguiente = 1
        for p in puestos or []:
            self.guardar(p)

    def del_vendedor(self, id_vendedor: int) -> Puesto | None:
        return next((p for p in self._datos.values() if p.id_vendedor == id_vendedor), None)

    def del_mercado(self, codigo_mercado: str) -> list[Puesto]:
        return sorted((p for p in self._datos.values() if p.codigo_mercado == codigo_mercado),
                      key=lambda p: orden_de_numero(p.numero))

    def obtener_por_numero(self, codigo_mercado: str, numero: str) -> Puesto | None:
        return next((p for p in self._datos.values()
                     if p.codigo_mercado == codigo_mercado and p.numero == numero), None)

    def guardar(self, puesto: Puesto) -> Puesto:
        if puesto.id is None:
            puesto = replace(puesto, id=self._siguiente)
            self._siguiente += 1
        self._datos[puesto.id] = puesto
        return puesto

    def contar_por_mercado(self) -> dict[str, int]:
        cuenta: dict[str, int] = {}
        for p in self._datos.values():
            cuenta[p.codigo_mercado] = cuenta.get(p.codigo_mercado, 0) + 1
        return cuenta


class OfertasEnMemoria:
    def __init__(self):
        self._datos: dict[int, Oferta] = {}
        self._confirmaciones: dict[tuple[int, int], Confirmacion] = {}
        self._siguiente = 1

    def obtener(self, id_oferta: int) -> Oferta | None:
        return self._datos.get(id_oferta)

    def guardar(self, oferta: Oferta) -> Oferta:
        if oferta.id is None:
            oferta = replace(oferta, id=self._siguiente)
            self._siguiente += 1
        self._datos[oferta.id] = oferta
        return oferta

    def del_vendedor(self, id_vendedor: int) -> list[Oferta]:
        return sorted((o for o in self._datos.values() if o.id_vendedor == id_vendedor),
                      key=lambda o: (o.desde, o.id), reverse=True)

    def vigentes(self, ahora: datetime, codigo_mercado: str | None = None,
                 codigo_producto: str | None = None) -> list[Oferta]:
        return [
            o for o in self._datos.values()
            if o.vigente(ahora)
            and (codigo_mercado is None or o.codigo_mercado == codigo_mercado)
            and (codigo_producto is None or o.codigo_producto == codigo_producto)
        ]

    def en_revision(self) -> list[Oferta]:
        return [o for o in self._datos.values() if o.estado is EstadoOferta.EN_REVISION]

    def confirmaciones(self, ids_oferta: list[int]) -> dict[int, list[Confirmacion]]:
        salida: dict[int, list[Confirmacion]] = {}
        for (id_oferta, _), c in self._confirmaciones.items():
            if id_oferta in ids_oferta:
                salida.setdefault(id_oferta, []).append(c)
        return salida

    def guardar_confirmacion(self, confirmacion: Confirmacion) -> None:
        self._confirmaciones[(confirmacion.id_oferta, confirmacion.id_usuario)] = confirmacion


class InventarioEnMemoria:
    def __init__(self):
        self._datos: dict[tuple[int, str], ArticuloInventario] = {}
        self._siguiente = 1

    def del_puesto(self, id_puesto: int) -> list[ArticuloInventario]:
        return [a for (p, _), a in self._datos.items() if p == id_puesto]

    def de_puestos(self, ids_puestos: list[int]) -> dict[int, list[ArticuloInventario]]:
        salida: dict[int, list[ArticuloInventario]] = {}
        for (p, _), a in self._datos.items():
            if p in ids_puestos:
                salida.setdefault(p, []).append(a)
        return salida

    def guardar(self, articulo: ArticuloInventario) -> ArticuloInventario:
        clave = (articulo.id_puesto, articulo.codigo_producto)
        anterior = self._datos.get(clave)
        if anterior is not None:
            articulo = replace(articulo, id=anterior.id)
        elif articulo.id is None:
            articulo = replace(articulo, id=self._siguiente)
            self._siguiente += 1
        self._datos[clave] = articulo
        return articulo

    def quitar(self, id_puesto: int, codigo_producto: str) -> None:
        self._datos.pop((id_puesto, codigo_producto), None)
