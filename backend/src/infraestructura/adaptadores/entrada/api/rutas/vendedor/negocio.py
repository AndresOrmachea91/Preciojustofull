"""
El negocio del casero desde el celular (C137): su distribuidora, la foto
del puesto y el inventario.

    PUT    /api/v1/vendedor/distribuidora
    PUT    /api/v1/vendedor/puesto/foto
    GET    /api/v1/vendedor/inventario
    PUT    /api/v1/vendedor/inventario
    DELETE /api/v1/vendedor/inventario/{codigo_producto}
"""
import base64
import binascii

from fastapi import APIRouter, Depends

from src.dominio.excepciones import DatoInvalido
from src.dominio.modelo import Disponibilidad, Presentacion
from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.cache_fichas import olvidar
from src.infraestructura.adaptadores.entrada.api.dependencias import caso_inventario, caso_mi_puesto
from src.infraestructura.adaptadores.entrada.api.mapeo import articulo_a_salida, puesto_a_salida
from src.infraestructura.adaptadores.entrada.api.seguridad import usuario_actual

router = APIRouter(prefix="/vendedor", tags=["vendedor"])


@router.put("/distribuidora", response_model=e.PuestoSalida)
def registrar_distribuidora(cuerpo: e.DistribuidoraEntrada, vendedor=Depends(usuario_actual),
                            caso=Depends(caso_mi_puesto)):
    """Una distribuidora: su propio punto en el mapa, con el local como puesto."""
    local = caso.registrar_distribuidora(
        vendedor, nombre=cuerpo.nombre, zona=cuerpo.zona, macrodistrito=cuerpo.macrodistrito,
        latitud=cuerpo.latitud, longitud=cuerpo.longitud, rubros=cuerpo.rubros, referencia=cuerpo.referencia,
    )
    olvidar()
    return puesto_a_salida(local)


@router.put("/puesto/foto", response_model=e.PuestoSalida)
def poner_foto(cuerpo: e.FotoEntrada, vendedor=Depends(usuario_actual), caso=Depends(caso_mi_puesto)):
    # Se acepta la data URL que da el navegador; lo que vale es lo que dicen los bytes.
    datos = cuerpo.imagen.split(",", 1)[1] if cuerpo.imagen.startswith("data:") else cuerpo.imagen
    try:
        contenido = base64.b64decode(datos, validate=True)
    except (binascii.Error, ValueError):
        raise DatoInvalido("La foto no llegó bien: vuelva a elegirla") from None
    puesto = caso.poner_foto(vendedor, contenido)
    olvidar()
    return puesto_a_salida(puesto)


@router.get("/inventario", response_model=list[e.ArticuloSalida])
def ver_inventario(vendedor=Depends(usuario_actual), caso=Depends(caso_inventario)):
    return [articulo_a_salida(a, caso.producto(a.codigo_producto)) for a in caso.ver(vendedor)]


@router.put("/inventario", response_model=e.ArticuloSalida)
def guardar_articulo(cuerpo: e.ArticuloEntrada, vendedor=Depends(usuario_actual), caso=Depends(caso_inventario)):
    """Precio y disponibilidad de un producto del puesto. Si el precio cambia, se publica como declarado."""
    try:
        presentacion = Presentacion(cuerpo.presentacion)
    except ValueError:
        raise DatoInvalido(f"Presentación desconocida: {cuerpo.presentacion}") from None
    articulo = caso.guardar(vendedor, cuerpo.codigo_producto, cuerpo.monto, presentacion,
                            Disponibilidad(cuerpo.disponibilidad))
    olvidar()
    return articulo_a_salida(articulo, caso.producto(articulo.codigo_producto))


@router.delete("/inventario/{codigo_producto}", status_code=204)
def quitar_articulo(codigo_producto: str, vendedor=Depends(usuario_actual), caso=Depends(caso_inventario)):
    caso.quitar(vendedor, codigo_producto)
    olvidar()
