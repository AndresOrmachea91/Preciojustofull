"""El vendedor publica y revisa los precios de su puesto: /api/v1/vendedor/precios."""
from fastapi import APIRouter, Depends

from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.dependencias import caso_mis_precios, caso_publicar_precio
from src.infraestructura.adaptadores.entrada.api.mapeo import precio_publicado_a_salida
from src.infraestructura.adaptadores.entrada.api.seguridad import usuario_actual
from src.dominio.modelo import Presentacion

router = APIRouter(prefix="/vendedor/precios", tags=["vendedor"])


@router.get("", response_model=list[e.PrecioPublicadoSalida])
def mis_precios(vendedor=Depends(usuario_actual), caso=Depends(caso_mis_precios)):
    """El último precio publicado de cada producto de mi puesto."""
    return [precio_publicado_a_salida(p) for p in caso.ejecutar(vendedor)]


@router.post("", response_model=e.ReporteSalida, status_code=201)
def publicar(cuerpo: e.PublicarPrecioEntrada, vendedor=Depends(usuario_actual),
             caso=Depends(caso_publicar_precio)):
    """Se publica al instante, marcado como declarado por el vendedor."""
    caso.ejecutar(vendedor, cuerpo.codigo_producto, cuerpo.monto, Presentacion(cuerpo.presentacion))
    return e.ReporteSalida(aceptado=True, mensaje="Precio publicado. Se muestra como declarado por el vendedor.")
