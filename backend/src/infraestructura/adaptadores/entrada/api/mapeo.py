"""Traducción entre objetos del dominio y esquemas de la API."""
from __future__ import annotations

from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.aplicacion.puertos.entrada import CostoCanastaEnMercado, PrecioEnMercado
from src.dominio.modelo import Mercado, PERMISOS_POR_ROL, PrecioConsolidado, Producto, Reporte, Usuario


def precio_a_salida(p: PrecioConsolidado) -> e.PrecioSalida:
    return e.PrecioSalida(
        codigo_producto=p.codigo_producto,
        codigo_mercado=p.codigo_mercado,
        periodo=str(p.periodo),
        rango=e.RangoSalida(minimo=p.rango.minimo, maximo=p.rango.maximo, centro=p.rango.centro),
        unidad=p.unidad.value,
        confianza=p.confianza.value,
        procedencia=p.procedencia.value,
        observaciones_usadas=p.observaciones_usadas,
        fecha_observacion_mas_reciente=p.fecha_observacion_mas_reciente,
        conflictos=p.conflictos,
    )


def precio_en_mercado_a_salida(x: PrecioEnMercado) -> e.PrecioEnMercadoSalida:
    return e.PrecioEnMercadoSalida(
        codigo_mercado=x.codigo_mercado,
        nombre_mercado=x.nombre_mercado,
        tipo=x.tipo,
        zona=x.zona,
        nivel_precio=x.nivel_precio,
        precio=precio_a_salida(x.precio),
    )


def producto_a_salida(p: Producto) -> e.ProductoSalida:
    return e.ProductoSalida(
        codigo=p.codigo, nombre=p.nombre,
        categoria=p.categoria.value, es_perecedero=p.es_perecedero,
        unidad_base=p.unidad_base.value, dias_conservacion=p.dias_conservacion,
        presentaciones=[
            e.PresentacionSalida(codigo=x.value, nombre=x.nombre, factor=x.factor) for x in p.presentaciones
        ],
    )


def mercado_a_salida(m: Mercado) -> e.MercadoSalida:
    return e.MercadoSalida(
        codigo=m.codigo, nombre=m.nombre, tipo=m.tipo.value, zona=m.zona,
        macrodistrito=m.macrodistrito, codigo_padre=m.codigo_padre,
        nivel_precio=m.nivel_precio.value,
        latitud=m.latitud, longitud=m.longitud, publica_rango=m.publica_rango,
    )


def canasta_a_salida(c: CostoCanastaEnMercado) -> e.CanastaSalida:
    return e.CanastaSalida(
        codigo_mercado=c.codigo_mercado, nombre_mercado=c.nombre_mercado, zona=c.zona,
        costo_total=c.costo_total, productos_cubiertos=c.productos_cubiertos,
        productos_pedidos=c.productos_pedidos, cobertura=round(c.cobertura, 2),
        faltantes=c.faltantes,
    )



def usuario_a_salida(u: Usuario) -> e.UsuarioSalida:
    return e.UsuarioSalida(
        id=u.id,
        correo=u.correo,
        nombre=u.nombre,
        rol=u.rol.value,
        activo=u.activo,
        creado_en=u.creado_en,
        # Los permisos van en la respuesta para que la interfaz muestre u
        # oculte acciones sin repetir la matriz del dominio.
        permisos=sorted(p.value for p in PERMISOS_POR_ROL[u.rol]) if u.activo else [],
        codigo_punto_venta=u.codigo_punto_venta,
    )


def reporte_a_salida(r: Reporte) -> e.ReporteRevisionSalida:
    return e.ReporteRevisionSalida(
        id=r.id,
        codigo_producto=r.codigo_producto,
        codigo_mercado=r.codigo_mercado,
        monto=r.monto,
        unidad=r.unidad,
        id_autor=r.id_autor,
        creado_en=r.creado_en,
        estado=r.estado.value,
        id_revisor=r.id_revisor,
        revisado_en=r.revisado_en,
        motivo_rechazo=r.motivo_rechazo,
    )
