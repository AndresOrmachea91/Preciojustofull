"""
El administrador gestiona el catálogo: mercados y tiendas, y productos.

Eliminar es siempre LÓGICO (la fila queda en la base, auditada): las
observaciones de precio ya apuntan a esos códigos y no pueden quedar
huérfanas. El código de cada registro no cambia nunca por la misma razón.
"""
from __future__ import annotations

import re
import unicodedata

from src.aplicacion.casos_uso.cuentas.permisos import exigir
from src.aplicacion.puertos.salida import (
    RepositorioMercados, RepositorioProductos, RepositorioUsuarios,
)
from src.dominio.excepciones import (
    CodigoYaExiste, DatoInvalido, MercadoNoEncontrado, ProductoNoEncontrado,
    PuntoVentaConDependientes,
)
from src.dominio.modelo import Categoria, Mercado, Permiso, Presentacion, Producto, TipoPuntoVenta, Usuario
from src.dominio.modelo.mercado import ubicacion_valida
from src.dominio.servicio.jerarquia import validar_jerarquia
from src.dominio.valor import UnidadCanonica


def codigo_desde_nombre(nombre: str) -> str:
    """'Mercado Rodríguez' -> 'mercado_rodriguez'. Es el mismo estilo que los códigos sembrados."""
    sin_tildes = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    codigo = re.sub(r"[^a-z0-9]+", "_", sin_tildes.lower()).strip("_")
    return codigo[:60] or "sin_nombre"


def _codigo_libre(base: str, existe) -> str:
    codigo, n = base, 2
    while existe(codigo):
        codigo, n = f"{base}_{n}", n + 1
    return codigo


class GestionarPuntosVenta:
    def __init__(self, mercados: RepositorioMercados, usuarios: RepositorioUsuarios):
        self._mercados = mercados
        self._usuarios = usuarios

    def crear(self, actor: Usuario, *, nombre: str, tipo: TipoPuntoVenta, zona: str = "",
              macrodistrito: str = "", latitud: float | None = None, longitud: float | None = None,
              codigo_padre: str | None = None, codigo: str | None = None) -> Mercado:
        exigir(actor, Permiso.GESTIONAR_CATALOGO)
        if codigo:
            if self._mercados.obtener(codigo) is not None:
                raise CodigoYaExiste("punto de venta", codigo)
        else:
            codigo = _codigo_libre(codigo_desde_nombre(nombre), lambda c: self._mercados.obtener(c) is not None)
        mercado = self._validar(Mercado(
            codigo=codigo, nombre=nombre.strip(), tipo=tipo, zona=zona.strip(),
            macrodistrito=macrodistrito.strip(), latitud=latitud, longitud=longitud,
            codigo_padre=codigo_padre or None,
        ))
        self._mercados.guardar(mercado)
        return mercado

    def actualizar(self, actor: Usuario, codigo: str, *, nombre: str, tipo: TipoPuntoVenta,
                   zona: str = "", macrodistrito: str = "", latitud: float | None = None,
                   longitud: float | None = None, codigo_padre: str | None = None) -> Mercado:
        exigir(actor, Permiso.GESTIONAR_CATALOGO)
        actual = self._obtener(codigo)
        mercado = self._validar(Mercado(
            codigo=codigo, nombre=nombre.strip(), tipo=tipo, zona=zona.strip(),
            macrodistrito=macrodistrito.strip(), latitud=latitud, longitud=longitud,
            # El factor de mercado lo calibra el trabajo de campo, no el formulario.
            factor_mercado=actual.factor_mercado, codigo_padre=codigo_padre or None,
        ))
        self._mercados.guardar(mercado)
        return mercado

    def eliminar(self, actor: Usuario, codigo: str) -> None:
        exigir(actor, Permiso.GESTIONAR_CATALOGO)
        self._obtener(codigo)
        sectores = [m.nombre for m in self._mercados.listar() if m.codigo_padre == codigo]
        if sectores:
            raise PuntoVentaConDependientes(codigo, f"tiene sectores ({', '.join(sectores)})")
        vendedores = [u.correo for u in self._usuarios.listar() if u.codigo_punto_venta == codigo]
        if vendedores:
            raise PuntoVentaConDependientes(codigo, f"tiene vendedores asignados ({', '.join(vendedores)})")
        self._mercados.eliminar(codigo)

    def _validar(self, mercado: Mercado) -> Mercado:
        if not mercado.nombre:
            raise DatoInvalido("El punto de venta necesita un nombre")
        if not ubicacion_valida(mercado.latitud, mercado.longitud):
            raise DatoInvalido("La ubicación tiene que tener latitud y longitud, dentro de La Paz o El Alto")
        if mercado.codigo_padre is not None and self._mercados.obtener(mercado.codigo_padre) is None:
            raise MercadoNoEncontrado(mercado.codigo_padre)
        # Las reglas de padre e hijo (solo un mercado agrupa sectores, sin
        # ciclos, un solo nivel) ya existen en el dominio: se reusan.
        otros = [m for m in self._mercados.listar() if m.codigo != mercado.codigo]
        validar_jerarquia([*otros, mercado])
        return mercado

    def _obtener(self, codigo: str) -> Mercado:
        mercado = self._mercados.obtener(codigo)
        if mercado is None:
            raise MercadoNoEncontrado(codigo)
        return mercado


class GestionarProductos:
    def __init__(self, productos: RepositorioProductos):
        self._productos = productos

    def crear(self, actor: Usuario, *, nombre: str, categoria: Categoria, unidad_base: UnidadCanonica,
              presentaciones: tuple[Presentacion, ...] = (), dias_conservacion: int = 30,
              codigo: str | None = None) -> Producto:
        exigir(actor, Permiso.GESTIONAR_CATALOGO)
        if codigo:
            if self._productos.obtener(codigo) is not None:
                raise CodigoYaExiste("producto", codigo)
        else:
            codigo = _codigo_libre(codigo_desde_nombre(nombre), lambda c: self._productos.obtener(c) is not None)
        producto = self._construir(codigo, nombre, categoria, unidad_base, presentaciones, dias_conservacion, None)
        self._productos.guardar(producto)
        return producto

    def actualizar(self, actor: Usuario, codigo: str, *, nombre: str, categoria: Categoria,
                   unidad_base: UnidadCanonica, presentaciones: tuple[Presentacion, ...] = (),
                   dias_conservacion: int = 30) -> Producto:
        exigir(actor, Permiso.GESTIONAR_CATALOGO)
        actual = self._obtener(codigo)
        producto = self._construir(codigo, nombre, categoria, unidad_base, presentaciones,
                                   dias_conservacion, actual.zona_origen)
        self._productos.guardar(producto)
        return producto

    def eliminar(self, actor: Usuario, codigo: str) -> None:
        exigir(actor, Permiso.GESTIONAR_CATALOGO)
        self._obtener(codigo)
        self._productos.eliminar(codigo)

    @staticmethod
    def _construir(codigo, nombre, categoria, unidad_base, presentaciones, dias, zona_origen) -> Producto:
        if not nombre.strip():
            raise DatoInvalido("El producto necesita un nombre")
        if dias < 1:
            raise DatoInvalido("Los días de conservación tienen que ser al menos 1")
        return Producto(
            codigo=codigo, nombre=nombre.strip(), categoria=categoria, dias_conservacion=dias,
            zona_origen=zona_origen, unidad_base=unidad_base, presentaciones=tuple(presentaciones),
        )

    def _obtener(self, codigo: str) -> Producto:
        producto = self._productos.obtener(codigo)
        if producto is None:
            raise ProductoNoEncontrado(codigo)
        return producto
