"""Traducción entre objetos del dominio y esquemas de la API."""
from __future__ import annotations

from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.aplicacion.puertos.entrada import CostoCanastaEnMercado, PrecioEnMercado
from src.aplicacion.casos_uso.vendedor.publicar_precio import PrecioPublicado
from src.dominio.modelo import (
    Auditoria, ListaCompras, Mercado, PERMISOS_POR_ROL, PrecioConsolidado, Producto, RegistroAuditado,
    Reporte, Usuario,
)


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
        voces=p.voces,
        factor_mercado=p.factor_mercado,
        antiguedad_dias=p.antiguedad_dias,
        motivos_rango=p.motivos_rango,
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
        faltantes=c.faltantes, productos_estimados=c.productos_estimados, nivel_precio=c.nivel_precio,
        costo_minimo=c.costo_minimo, costo_maximo=c.costo_maximo,
    )



def auditoria_a_salida(a: Auditoria) -> e.AuditoriaSalida:
    return e.AuditoriaSalida(
        creado_en=a.creado_en, creado_por=a.creado_por, modificado_en=a.modificado_en,
        modificado_por=a.modificado_por, eliminado=a.eliminado,
    )


def registro_auditado_a_salida(r: RegistroAuditado) -> e.RegistroAuditadoSalida:
    return e.RegistroAuditadoSalida(
        tabla=r.tabla, clave=r.clave, descripcion=r.descripcion, accion=r.accion,
        ultimo_cambio=r.ultimo_cambio, auditoria=auditoria_a_salida(r.auditoria),
    )


def usuario_auditado_a_salida(u: Usuario) -> e.UsuarioAuditadoSalida:
    a = u.auditoria
    return e.UsuarioAuditadoSalida(
        **usuario_a_salida(u).model_dump(),
        auditoria=None if a is None else auditoria_a_salida(a),
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



def lista_a_salida(l: ListaCompras) -> e.ListaSalida:
    return e.ListaSalida(
        id=l.id, nombre=l.nombre, creado_en=l.creado_en,
        items=[
            e.ItemListaSalida(codigo_producto=i.codigo_producto, cantidad=i.cantidad, presentacion=i.presentacion.value)
            for i in l.items
        ],
    )


def precio_publicado_a_salida(p: PrecioPublicado) -> e.PrecioPublicadoSalida:
    return e.PrecioPublicadoSalida(
        codigo_producto=p.producto.codigo, nombre_producto=p.producto.nombre, monto=p.monto,
        presentacion=p.presentacion, precio_por_unidad_base=round(p.precio_por_unidad_base, 4),
        unidad_base=p.producto.unidad_base.value, publicado_en=p.publicado_en,
    )


# --- puestos, ofertas y ficha del mercado (C133, C134) ---------------------------

def url_foto(nombre: str | None) -> str | None:
    return f"/api/v1/fotos/{nombre}" if nombre else None


def puesto_a_salida(p, registrado: bool = True) -> e.PuestoSalida:
    return e.PuestoSalida(
        id=p.id, codigo_mercado=p.codigo_mercado, numero=p.numero, nombre=p.nombre,
        rubros=[r.value for r in p.rubros], referencia=p.referencia, registrado=registrado,
        foto=url_foto(p.foto), es_local=p.es_local, celular=p.celular,
    )


def articulo_a_salida(a, producto) -> e.ArticuloSalida:
    return e.ArticuloSalida(
        codigo_producto=a.codigo_producto, nombre_producto=producto.nombre, categoria=producto.categoria.value,
        monto=a.monto, presentacion=a.presentacion.value, precio_por_unidad_base=round(a.precio_por_unidad_base, 4),
        unidad_base=producto.unidad_base.value, disponibilidad=a.disponibilidad.value, actualizado_en=a.actualizado_en,
        cantidad=a.cantidad, minimo=a.minimo,
    )


def reporte_inventario_a_salida(r) -> e.ReporteInventarioSalida:
    def articulo(x):
        return e.ArticuloSalida(
            codigo_producto=x.articulo.codigo_producto, nombre_producto=x.nombre_producto, categoria=x.categoria,
            monto=x.articulo.monto, presentacion=x.articulo.presentacion.value,
            precio_por_unidad_base=round(x.articulo.precio_por_unidad_base, 4), unidad_base=x.unidad_base,
            disponibilidad=x.articulo.disponibilidad.value, actualizado_en=x.articulo.actualizado_en,
            cantidad=x.articulo.cantidad, minimo=x.articulo.minimo,
        )
    return e.ReporteInventarioSalida(
        renglones=[e.RenglonReporteSalida(
            articulo=articulo(x),
            sugerencia=e.SugerenciaSalida(tipo=x.sugerencia.tipo, texto=x.sugerencia.texto,
                                          precio_sugerido=x.sugerencia.precio_sugerido,
                                          precio_mercado=x.sugerencia.precio_mercado,
                                          diferencia=x.sugerencia.diferencia),
            alertas=list(x.alertas),
        ) for x in r.renglones],
        productos=r.productos, con_cantidad=r.con_cantidad, valor_total=r.valor_total, agotados=r.agotados,
        queda_poco=r.queda_poco, para_revisar_precio=r.para_revisar_precio, sin_actualizar=r.sin_actualizar,
        consejos=r.consejos,
    )


def puestos_del_mercado_a_salida(r) -> e.PuestosDelMercadoSalida:
    return e.PuestosDelMercadoSalida(
        mercado=mercado_a_salida(r.mercado),
        puestos=[
            e.PuestoConInventarioSalida(
                puesto=puesto_a_salida(x.puesto),
                articulos=[articulo_a_salida(v.articulo, v.producto) for v in x.articulos],
                total=x.total,
            )
            for x in r.puestos
        ],
    )


def oferta_a_salida(v) -> e.OfertaSalida:
    o = v.oferta
    return e.OfertaSalida(
        id=o.id, codigo_producto=o.codigo_producto, nombre_producto=v.producto.nombre,
        unidad_base=v.producto.unidad_base.value, codigo_mercado=o.codigo_mercado,
        nombre_mercado=v.mercado.nombre, numero_puesto=o.numero_puesto,
        nombre_puesto=(v.puesto.nombre or None) if v.puesto else None,
        monto=o.monto, presentacion=o.presentacion.value, precio_por_unidad_base=o.precio_por_unidad_base,
        desde=o.desde, hasta=o.hasta, nota=o.nota, combo=o.combo,
        precio_sistema=v.precio_sistema.rango.centro, procedencia_sistema=v.precio_sistema.procedencia.value,
        ahorro_por_unidad=v.ahorro_por_unidad, ahorro_relativo=v.ahorro_relativo,
        confirmaron=v.confirmaron, desmintieron=v.desmintieron,
    )


def mi_oferta_a_salida(m) -> e.MiOfertaSalida:
    o = m.oferta
    return e.MiOfertaSalida(
        id=o.id, codigo_producto=o.codigo_producto, nombre_producto=m.nombre_producto, monto=o.monto,
        presentacion=o.presentacion.value, precio_por_unidad_base=o.precio_por_unidad_base,
        desde=o.desde, hasta=o.hasta, nota=o.nota, combo=o.combo, estado=m.estado,
        confirmaron=m.confirmaron, desmintieron=m.desmintieron,
    )


def oferta_en_revision_a_salida(r) -> e.OfertaEnRevisionSalida:
    o = r.oferta
    return e.OfertaEnRevisionSalida(
        id=o.id, nombre_producto=r.nombre_producto, nombre_mercado=r.nombre_mercado,
        numero_puesto=o.numero_puesto, monto=o.monto, presentacion=o.presentacion.value, hasta=o.hasta,
        nota=o.nota, confirmaron=r.confirmaron, desmintieron=r.desmintieron,
    )


def ficha_a_salida(f) -> e.FichaMercadoSalida:
    return e.FichaMercadoSalida(
        mercado=mercado_a_salida(f.mercado),
        padre=mercado_a_salida(f.padre) if f.padre else None,
        sectores=[mercado_a_salida(m) for m in f.sectores],
        factor_mercado=f.mercado.factor_mercado,
        precios=[e.PrecioDeProductoSalida(
            codigo_producto=p.producto.codigo, nombre_producto=p.producto.nombre,
            categoria=p.producto.categoria.value, precio=precio_a_salida(p.precio),
            ciudad=p.ciudad, diferencia=p.diferencia,
        ) for p in f.precios],
        puestos=[e.PuestoEnFichaSalida(
            puesto=puesto_a_salida(x.puesto, x.registrado),
            precios=[e.PrecioDelPuestoSalida(
                codigo_producto=p.producto.codigo, nombre_producto=p.producto.nombre, monto=p.monto,
                unidad=p.unidad, precio_por_unidad_base=p.precio_por_unidad_base,
                unidad_base=p.producto.unidad_base.value, fecha=p.fecha, fuente=p.fuente,
            ) for p in x.precios],
            ofertas=[oferta_a_salida(v) for v in x.ofertas],
        ) for x in f.puestos],
        ofertas=[oferta_a_salida(v) for v in f.ofertas],
        observados=f.observados, estimados=f.estimados, productos_sin_precio=f.productos_sin_precio,
        dato_mas_reciente=f.dato_mas_reciente,
    )


def entrada_directorio_a_salida(x) -> e.EntradaDirectorioSalida:
    return e.EntradaDirectorioSalida(
        mercado=mercado_a_salida(x.mercado), puestos=x.puestos, ofertas=x.ofertas, sectores=x.sectores,
    )


def plan_verificacion_a_salida(plan) -> e.PlanVerificacionSalida:
    return e.PlanVerificacionSalida(
        fecha=plan.fecha,
        productos=[
            e.PrioridadProductoSalida(
                producto=producto_a_salida(p.producto), puntaje=p.puntaje, lugares_sin_dato=p.lugares_sin_dato,
                lugares_con_dato_viejo=p.lugares_con_dato_viejo, lugares_al_dia=p.lugares_al_dia,
                cambio_mensual=p.cambio_mensual, ancho_relativo=p.ancho_relativo, motivos=p.motivos,
            )
            for p in plan.productos
        ],
        lugares=[
            e.LugarPorVisitarSalida(mercado=mercado_a_salida(x.mercado), productos_al_dia=x.productos_al_dia,
                                    productos_total=x.productos_total)
            for x in plan.lugares
        ],
        variaciones=[
            e.VariacionProductoSalida(
                producto=producto_a_salida(v.producto), cambio_mensual=v.cambio_mensual,
                mayor_subida=v.mayor_subida, mayor_bajada=v.mayor_bajada, meses=v.meses, nivel=v.nivel,
            )
            for v in plan.variaciones
        ],
    )
