"""
El administrador gestiona el catálogo: /api/v1/admin/mercados y /api/v1/admin/productos.

Para LISTAR se usan las rutas públicas (/api/v1/mercados y /api/v1/productos):
lo que ve el administrador es lo mismo que ve todo el mundo.
"""
from fastapi import APIRouter, Depends, Response

from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.dependencias import (
    caso_gestionar_productos, caso_gestionar_puntos_venta,
)
from src.infraestructura.adaptadores.entrada.api.mapeo import mercado_a_salida, producto_a_salida
from src.infraestructura.adaptadores.entrada.api.seguridad import usuario_actual
from src.dominio.modelo import Categoria, Presentacion, TipoPuntoVenta
from src.dominio.valor import UnidadCanonica

router = APIRouter(prefix="/admin", tags=["administración"])


def _datos_punto(cuerpo: e.PuntoVentaEntrada) -> dict:
    return dict(
        nombre=cuerpo.nombre, tipo=TipoPuntoVenta(cuerpo.tipo), zona=cuerpo.zona,
        macrodistrito=cuerpo.macrodistrito, latitud=cuerpo.latitud, longitud=cuerpo.longitud,
        codigo_padre=cuerpo.codigo_padre,
    )


def _datos_producto(cuerpo: e.ProductoEntrada) -> dict:
    return dict(
        nombre=cuerpo.nombre, categoria=Categoria(cuerpo.categoria),
        unidad_base=UnidadCanonica(cuerpo.unidad_base),
        presentaciones=tuple(Presentacion(p) for p in cuerpo.presentaciones),
        dias_conservacion=cuerpo.dias_conservacion,
    )


@router.post("/mercados", response_model=e.MercadoSalida, status_code=201)
def crear_punto(cuerpo: e.NuevoPuntoVentaEntrada, actor=Depends(usuario_actual),
                caso=Depends(caso_gestionar_puntos_venta)):
    return mercado_a_salida(caso.crear(actor, codigo=cuerpo.codigo, **_datos_punto(cuerpo)))


@router.put("/mercados/{codigo}", response_model=e.MercadoSalida)
def actualizar_punto(codigo: str, cuerpo: e.PuntoVentaEntrada, actor=Depends(usuario_actual),
                     caso=Depends(caso_gestionar_puntos_venta)):
    return mercado_a_salida(caso.actualizar(actor, codigo, **_datos_punto(cuerpo)))


@router.delete("/mercados/{codigo}", status_code=204)
def eliminar_punto(codigo: str, actor=Depends(usuario_actual), caso=Depends(caso_gestionar_puntos_venta)):
    """Borrado lógico: deja de verse, pero la fila y su historial quedan en la base."""
    caso.eliminar(actor, codigo)
    return Response(status_code=204)


@router.post("/productos", response_model=e.ProductoSalida, status_code=201)
def crear_producto(cuerpo: e.NuevoProductoEntrada, actor=Depends(usuario_actual),
                   caso=Depends(caso_gestionar_productos)):
    return producto_a_salida(caso.crear(actor, codigo=cuerpo.codigo, **_datos_producto(cuerpo)))


@router.put("/productos/{codigo}", response_model=e.ProductoSalida)
def actualizar_producto(codigo: str, cuerpo: e.ProductoEntrada, actor=Depends(usuario_actual),
                        caso=Depends(caso_gestionar_productos)):
    return producto_a_salida(caso.actualizar(actor, codigo, **_datos_producto(cuerpo)))


@router.delete("/productos/{codigo}", status_code=204)
def eliminar_producto(codigo: str, actor=Depends(usuario_actual), caso=Depends(caso_gestionar_productos)):
    """Borrado lógico. Sus observaciones de precio se conservan."""
    caso.eliminar(actor, codigo)
    return Response(status_code=204)
