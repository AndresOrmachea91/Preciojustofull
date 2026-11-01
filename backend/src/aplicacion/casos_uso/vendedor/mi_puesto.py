"""
El negocio del vendedor: su puesto en un mercado o su distribuidora, con
foto (C133, C137).

Desde la decisión 26 el casero elige él mismo en qué mercado está y qué
número tiene su puesto ("Mercado Rodríguez, puesto 14"): es quien lo sabe,
y esperar a que un administrador lo asigne frenaba a todos. El
administrador sigue pudiendo corregirlo o darlo de baja.

Una distribuidora no está dentro de un mercado: es su propio punto en el
mapa (tipo distribuidor) y su "puesto" es el local entero (número LOCAL),
para que foto, rubros e inventario funcionen igual para todos.
"""
from __future__ import annotations

from dataclasses import replace

from src.aplicacion.casos_uso.administracion.gestionar_catalogo import codigo_desde_nombre
from src.aplicacion.casos_uso.cuentas.permisos import exigir
from src.aplicacion.puertos.salida import (
    AlmacenFotos, RepositorioMercados, RepositorioPuestos, RepositorioUsuarios,
)
from src.dominio.excepciones import CodigoYaExiste, DatoInvalido, MercadoNoEncontrado
from src.dominio.modelo import Categoria, Mercado, Permiso, Puesto, TipoPuntoVenta, Usuario
from src.dominio.modelo.foto import extension_de_imagen
from src.dominio.modelo.mercado import ubicacion_valida
from src.dominio.modelo.puesto import NUMERO_LOCAL


def _rubros(rubros: list[str]) -> tuple[Categoria, ...]:
    try:
        return tuple(Categoria(r) for r in rubros)
    except ValueError:
        raise DatoInvalido(f"Rubro desconocido en {rubros}: use las categorías del catálogo") from None


class MiPuestoCasoUso:
    def __init__(self, mercados: RepositorioMercados, puestos: RepositorioPuestos,
                 usuarios: RepositorioUsuarios | None = None, fotos: AlmacenFotos | None = None):
        self._mercados = mercados
        self._puestos = puestos
        self._usuarios = usuarios
        self._fotos = fotos

    def ver(self, vendedor: Usuario) -> Puesto | None:
        exigir(vendedor, Permiso.PUBLICAR_PRECIO_PROPIO)
        return self._puestos.del_vendedor(vendedor.id)

    def guardar(self, vendedor: Usuario, numero: str, nombre: str, rubros: list[str],
                referencia: str = "", codigo_mercado: str | None = None) -> Puesto:
        """Su puesto en un mercado. Sin codigo_mercado, el mercado que ya tenía."""
        exigir(vendedor, Permiso.PUBLICAR_PRECIO_PROPIO)
        codigo = codigo_mercado or vendedor.codigo_punto_venta
        if not codigo:
            raise DatoInvalido("Elija en qué mercado está su puesto")
        mercado = self._mercados.obtener(codigo)
        if mercado is None:
            raise MercadoNoEncontrado(codigo)
        if mercado.tipo is not TipoPuntoVenta.MERCADO:
            raise DatoInvalido(
                f"{mercado.nombre} es {mercado.tipo.value}, no un mercado: elija el mercado donde está su puesto"
            )
        actual = self._puestos.del_vendedor(vendedor.id)
        nuevo = Puesto(codigo_mercado=mercado.codigo, numero=numero, nombre=nombre, rubros=_rubros(rubros),
                       referencia=referencia, id_vendedor=vendedor.id, foto=actual.foto if actual else None)
        if nuevo.es_local:
            raise DatoInvalido("Ese número está reservado: use el número de su puesto")
        if actual is not None and actual.codigo_mercado != mercado.codigo:
            # Se cambió de mercado: el puesto viejo queda sin dueño (no se borra:
            # las mediciones de campo lo pueden seguir nombrando).
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
        guardado = self._puestos.guardar(replace(nuevo, id=actual.id) if actual is not None else nuevo)
        self._asignar_punto(vendedor, mercado.codigo)
        return guardado

    def registrar_distribuidora(self, vendedor: Usuario, *, nombre: str, zona: str, macrodistrito: str = "",
                                latitud: float | None, longitud: float | None, rubros: list[str],
                                referencia: str = "") -> Puesto:
        """Una distribuidora: su propio punto en el mapa, con el local como único puesto."""
        exigir(vendedor, Permiso.PUBLICAR_PRECIO_PROPIO)
        nombre = " ".join((nombre or "").split())
        if not nombre:
            raise DatoInvalido("La distribuidora necesita un nombre")
        if latitud is None or longitud is None or not ubicacion_valida(latitud, longitud):
            raise DatoInvalido("Marque en el mapa dónde está la distribuidora (dentro de La Paz o El Alto)")
        actual = self._puestos.del_vendedor(vendedor.id)
        punto_actual = self._mercados.obtener(actual.codigo_mercado) if actual else None
        if punto_actual is not None and punto_actual.tipo is TipoPuntoVenta.DISTRIBUIDOR:
            codigo = punto_actual.codigo
        else:
            base = codigo_desde_nombre(nombre)
            codigo, n = base, 2
            while self._mercados.obtener(codigo) is not None:
                codigo, n = f"{base}_{n}", n + 1
        self._mercados.guardar(Mercado(
            codigo=codigo, nombre=nombre, tipo=TipoPuntoVenta.DISTRIBUIDOR, zona=" ".join(zona.split()),
            latitud=latitud, longitud=longitud, macrodistrito=" ".join(macrodistrito.split()),
        ))
        if actual is not None and actual.codigo_mercado != codigo:
            self._puestos.guardar(replace(actual, id_vendedor=None))
            actual = None
        local = Puesto(codigo_mercado=codigo, numero=NUMERO_LOCAL, nombre=nombre, rubros=_rubros(rubros),
                       referencia=referencia, id_vendedor=vendedor.id, foto=actual.foto if actual else None,
                       id=actual.id if actual else None)
        guardado = self._puestos.guardar(local)
        self._asignar_punto(vendedor, codigo)
        return guardado

    def poner_foto(self, vendedor: Usuario, contenido: bytes) -> Puesto:
        exigir(vendedor, Permiso.PUBLICAR_PRECIO_PROPIO)
        if self._fotos is None:
            raise DatoInvalido("Este servidor no tiene dónde guardar fotos")
        puesto = self._puestos.del_vendedor(vendedor.id)
        if puesto is None:
            raise DatoInvalido("Primero registre su puesto; después la foto")
        extension = extension_de_imagen(contenido)
        return self._puestos.guardar(replace(puesto, foto=self._fotos.guardar(contenido, extension)))

    def _asignar_punto(self, vendedor: Usuario, codigo: str) -> None:
        """Donde está su puesto es donde publica sus precios."""
        if self._usuarios is None or vendedor.codigo_punto_venta == codigo:
            return
        cuenta = self._usuarios.obtener(vendedor.id)
        if cuenta is not None:
            self._usuarios.guardar(replace(cuenta, codigo_punto_venta=codigo))
