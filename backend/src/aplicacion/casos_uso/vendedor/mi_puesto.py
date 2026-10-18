"""
El vendedor registra su puesto dentro del mercado (C133): número, nombre,
qué vende y cómo encontrarlo.

El MERCADO se lo asigna el administrador (decisión 13); el número y los
datos del puesto los pone el casero, que es quien los sabe. En una tienda o
un minimarket no hay puestos: el local entero es "el puesto".
"""
from __future__ import annotations

from dataclasses import replace

from src.aplicacion.casos_uso.cuentas.permisos import exigir
from src.aplicacion.casos_uso.vendedor.publicar_precio import punto_de_venta_del
from src.aplicacion.puertos.salida import LectorMercados, RepositorioPuestos
from src.dominio.excepciones import CodigoYaExiste, DatoInvalido
from src.dominio.modelo import Categoria, Permiso, Puesto, TipoPuntoVenta, Usuario


class MiPuestoCasoUso:
    def __init__(self, mercados: LectorMercados, puestos: RepositorioPuestos):
        self._mercados = mercados
        self._puestos = puestos

    def ver(self, vendedor: Usuario) -> Puesto | None:
        exigir(vendedor, Permiso.PUBLICAR_PRECIO_PROPIO)
        return self._puestos.del_vendedor(vendedor.id)

    def guardar(self, vendedor: Usuario, numero: str, nombre: str, rubros: list[str],
                referencia: str = "") -> Puesto:
        exigir(vendedor, Permiso.PUBLICAR_PRECIO_PROPIO)
        mercado = punto_de_venta_del(vendedor, self._mercados)
        if mercado.tipo is not TipoPuntoVenta.MERCADO:
            raise DatoInvalido(
                f"{mercado.nombre} es {mercado.tipo.value}: ahí el local entero es su puesto, no hace falta número"
            )
        try:
            categorias = tuple(Categoria(r) for r in rubros)
        except ValueError:
            raise DatoInvalido(f"Rubro desconocido en {rubros}: use las categorías del catálogo") from None

        actual = self._puestos.del_vendedor(vendedor.id)
        nuevo = Puesto(codigo_mercado=mercado.codigo, numero=numero, nombre=nombre, rubros=categorias,
                       referencia=referencia, id_vendedor=vendedor.id)
        if actual is not None and actual.codigo_mercado != mercado.codigo:
            # Lo cambiaron de mercado: el puesto viejo queda sin dueño.
            self._puestos.guardar(replace(actual, id_vendedor=None))
            actual = None
        ocupado = self._puestos.obtener_por_numero(mercado.codigo, nuevo.numero)
        if ocupado is not None and (actual is None or ocupado.id != actual.id):
            # El número es de otro casero, o ya tengo un puesto y quiero
            # pasarme a uno registrado: no se pisa.
            if ocupado.id_vendedor is not None or actual is not None:
                raise CodigoYaExiste("puesto en este mercado", nuevo.numero)
            # Registrado sin dueño (lo cargó el administrador): lo reclama.
            actual = ocupado
        return self._puestos.guardar(replace(nuevo, id=actual.id) if actual is not None else nuevo)
