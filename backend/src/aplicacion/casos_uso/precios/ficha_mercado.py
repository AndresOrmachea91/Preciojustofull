"""
Entrar a un mercado (C134): todo lo que el sistema sabe de un lugar.

- Los precios de TODOS los productos ahí, cada uno con su procedencia
  (observado o estimado) y cuánto se aparta de la referencia de la ciudad.
- Sus puestos: número, rubro y lo que cada uno declaró o se le midió.
- Las ofertas vigentes de sus caseros, con el ahorro contra el sistema.

No inventa nada nuevo: cada precio sale de la misma regla que el mapa y el
comparador (precio_del_local). Es otra forma de mirar los mismos datos: por
lugar en vez de por producto.

El directorio de mercados es la puerta de entrada: cuántos puestos y
ofertas tiene cada lugar, para saber adónde vale la pena entrar.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from src.aplicacion.casos_uso.precios.ofertas_vigentes import OfertaVista, VerOfertasVigentes
from src.aplicacion.casos_uso.precios.referencia_sistema import ReferenciaDelSistema
from src.aplicacion.puertos.salida import (
    LectorMercados, LectorObservaciones, LectorProductos, RepositorioPuestos,
)
from src.dominio.excepciones import MercadoNoEncontrado
from src.dominio.modelo import Fuente, Mercado, Observacion, PrecioConsolidado, Producto, Puesto
from src.dominio.modelo.puesto import orden_de_numero
from src.dominio.servicio.motor_fusion import MotorFusion


@dataclass(frozen=True, slots=True)
class PrecioDeProducto:
    producto: Producto
    precio: PrecioConsolidado
    # Centro de la referencia de la ciudad (mismo nivel), y cuánto se aparta
    # el precio de este lugar: +0.06 = 6 % más caro que la ciudad.
    ciudad: float | None
    diferencia: float | None


@dataclass(frozen=True, slots=True)
class PrecioDelPuesto:
    """Lo último que se supo de un producto en un puesto: lo que declaró el casero o lo que midió el campo."""

    producto: Producto
    monto: float
    unidad: str
    precio_por_unidad_base: float
    fecha: date | None
    fuente: str      # vendedor o campo


@dataclass(frozen=True, slots=True)
class PuestoEnFicha:
    puesto: Puesto
    # False si el número solo aparece en mediciones de campo: el puesto
    # existe, pero nadie lo registró todavía.
    registrado: bool
    precios: list[PrecioDelPuesto] = field(default_factory=list)
    ofertas: list[OfertaVista] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class FichaDeMercado:
    mercado: Mercado
    padre: Mercado | None
    sectores: list[Mercado]
    precios: list[PrecioDeProducto]
    puestos: list[PuestoEnFicha]
    ofertas: list[OfertaVista]
    productos_sin_precio: int

    @property
    def observados(self) -> int:
        return sum(1 for p in self.precios if not p.precio.es_estimado)

    @property
    def estimados(self) -> int:
        return sum(1 for p in self.precios if p.precio.es_estimado)

    @property
    def dato_mas_reciente(self) -> date | None:
        fechas = [p.precio.fecha_observacion_mas_reciente for p in self.precios
                  if not p.precio.es_estimado and p.precio.fecha_observacion_mas_reciente]
        return max(fechas) if fechas else None


@dataclass(frozen=True, slots=True)
class EntradaDirectorio:
    mercado: Mercado
    puestos: int
    ofertas: int
    sectores: int


class FichaMercado:
    def __init__(self, productos: LectorProductos, mercados: LectorMercados, observaciones: LectorObservaciones,
                 motor: MotorFusion, puestos: RepositorioPuestos, ofertas: VerOfertasVigentes,
                 reloj: Callable[[], date] | None = None):
        self._productos = productos
        self._mercados = mercados
        self._observaciones = observaciones
        self._motor = motor
        self._puestos = puestos
        self._ofertas = ofertas
        self._reloj = reloj

    def ejecutar(self, codigo_mercado: str) -> FichaDeMercado:
        mercado = self._mercados.obtener(codigo_mercado)
        if mercado is None:
            raise MercadoNoEncontrado(codigo_mercado)
        todos = self._mercados.listar()
        padre = next((m for m in todos if m.codigo == mercado.codigo_padre), None)
        sectores = [m for m in todos if m.codigo_padre == mercado.codigo]

        referencia = ReferenciaDelSistema(self._productos, self._observaciones, self._motor, reloj=self._reloj)
        precios: list[PrecioDeProducto] = []
        sin_precio = 0
        del_lugar: list[Observacion] = []
        for producto in self._productos.listar():
            precio = referencia.precio(producto.codigo, mercado)
            del_lugar += [o for o in referencia.observaciones(producto.codigo) if o.codigo_mercado == mercado.codigo]
            if precio is None:
                sin_precio += 1
                continue
            ciudad = referencia.de_la_ciudad(producto.codigo, mercado)
            centro_ciudad = ciudad.rango.centro if ciudad else None
            # Solo lo MEDIDO se compara con la ciudad: un estimado sale de la
            # ciudad por el factor, así que "igual que la ciudad" sería decir
            # lo mismo dos veces. El factor ya se muestra aparte.
            diferencia = (round(precio.rango.centro / centro_ciudad - 1, 4)
                          if centro_ciudad and not precio.es_estimado and precio.unidad is ciudad.unidad else None)
            precios.append(PrecioDeProducto(producto, precio, centro_ciudad, diferencia))
        precios.sort(key=lambda p: (p.producto.categoria.value, p.producto.nombre))

        ofertas = self._ofertas.ejecutar(codigo_mercado=mercado.codigo)
        return FichaDeMercado(
            mercado=mercado, padre=padre, sectores=sectores, precios=precios,
            puestos=self._puestos_de(mercado, del_lugar, ofertas),
            ofertas=ofertas, productos_sin_precio=sin_precio,
        )

    def _puestos_de(self, mercado: Mercado, observaciones: list[Observacion],
                    ofertas: list[OfertaVista]) -> list[PuestoEnFicha]:
        registrados = {p.numero: p for p in self._puestos.del_mercado(mercado.codigo)}
        # Lo último de cada producto en cada puesto, de quien vende o del campo.
        ultimos: dict[str, dict[str, Observacion]] = {}
        for o in observaciones:
            if not o.puesto or o.fuente not in (Fuente.VENDEDOR, Fuente.CAMPO):
                continue
            del_puesto = ultimos.setdefault(o.puesto, {})
            previa = del_puesto.get(o.codigo_producto)
            if previa is None or _cuando(o) > _cuando(previa):
                del_puesto[o.codigo_producto] = o
        numeros = set(registrados) | set(ultimos)
        salida = []
        for numero in sorted(numeros, key=orden_de_numero):
            puesto = registrados.get(numero) or Puesto(codigo_mercado=mercado.codigo, numero=numero, nombre="")
            precios = []
            for o in ultimos.get(numero, {}).values():
                producto = self._productos.obtener(o.codigo_producto)
                if producto is None:
                    continue
                precios.append(PrecioDelPuesto(
                    producto=producto, monto=o.precio.monto, unidad=o.precio.unidad.texto.lower(),
                    precio_por_unidad_base=o.precio_canonico(), fecha=o.fecha_observacion,
                    fuente=o.fuente.value,
                ))
            precios.sort(key=lambda p: p.producto.nombre)
            salida.append(PuestoEnFicha(
                puesto=puesto, registrado=numero in registrados, precios=precios,
                ofertas=[v for v in ofertas if v.oferta.numero_puesto == numero],
            ))
        return salida


def _cuando(o: Observacion) -> tuple:
    return (o.fecha_observacion or o.capturada_en.date(), o.capturada_en)


class DirectorioMercados:
    def __init__(self, mercados: LectorMercados, puestos: RepositorioPuestos, ofertas: VerOfertasVigentes):
        self._mercados = mercados
        self._puestos = puestos
        self._ofertas = ofertas

    def ejecutar(self) -> list[EntradaDirectorio]:
        todos = self._mercados.listar()
        puestos = self._puestos.contar_por_mercado()
        ofertas: dict[str, int] = {}
        for v in self._ofertas.ejecutar():
            ofertas[v.mercado.codigo] = ofertas.get(v.mercado.codigo, 0) + 1
        sectores: dict[str, int] = {}
        for m in todos:
            if m.codigo_padre:
                sectores[m.codigo_padre] = sectores.get(m.codigo_padre, 0) + 1
        return [
            EntradaDirectorio(m, puestos.get(m.codigo, 0), ofertas.get(m.codigo, 0), sectores.get(m.codigo, 0))
            for m in todos
        ]
