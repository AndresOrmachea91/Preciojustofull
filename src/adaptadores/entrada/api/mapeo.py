"""Traducción entre objetos del dominio y esquemas de la API."""
from __future__ import annotations

from src.adaptadores.entrada.api import esquemas as e
from src.aplicacion.puertos.entrada import CostoCanastaEnMercado, PrecioEnMercado
from src.dominio.modelo import Mercado, PrecioConsolidado, Producto


def precio_a_salida(p: PrecioConsolidado) -> e.PrecioSalida:
    return e.PrecioSalida(
        codigo_producto=p.codigo_producto,
        codigo_mercado=p.codigo_mercado,
        periodo=str(p.periodo),
        rango=e.RangoSalida(minimo=p.rango.minimo, maximo=p.rango.maximo, centro=p.rango.centro),
        unidad=p.unidad.value,
        confianza=p.confianza.value,
        observaciones_usadas=p.observaciones_usadas,
        conflictos=p.conflictos,
    )


def precio_en_mercado_a_salida(x: PrecioEnMercado) -> e.PrecioEnMercadoSalida:
    return e.PrecioEnMercadoSalida(
        codigo_mercado=x.codigo_mercado,
        nombre_mercado=x.nombre_mercado,
        tipo=x.tipo,
        zona=x.zona,
        precio=precio_a_salida(x.precio),
    )


def producto_a_salida(p: Producto) -> e.ProductoSalida:
    return e.ProductoSalida(
        codigo=p.codigo, nombre=p.nombre,
        categoria=p.categoria.value, es_perecedero=p.es_perecedero,
    )


def mercado_a_salida(m: Mercado) -> e.MercadoSalida:
    return e.MercadoSalida(
        codigo=m.codigo, nombre=m.nombre, tipo=m.tipo.value, zona=m.zona,
        latitud=m.latitud, longitud=m.longitud, publica_rango=m.publica_rango,
    )


def canasta_a_salida(c: CostoCanastaEnMercado) -> e.CanastaSalida:
    return e.CanastaSalida(
        codigo_mercado=c.codigo_mercado, nombre_mercado=c.nombre_mercado, zona=c.zona,
        costo_total=c.costo_total, productos_cubiertos=c.productos_cubiertos,
        productos_pedidos=c.productos_pedidos, cobertura=round(c.cobertura, 2),
        faltantes=c.faltantes,
    )

