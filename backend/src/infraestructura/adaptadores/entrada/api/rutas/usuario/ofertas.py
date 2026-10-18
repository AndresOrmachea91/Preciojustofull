"""¿Lo viste así? El comprador confirma o desmiente una oferta: POST /api/v1/ofertas/{id}/confirmar."""
from fastapi import APIRouter, Depends

from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.cache_fichas import olvidar
from src.infraestructura.adaptadores.entrada.api.dependencias import caso_confirmar_oferta
from src.infraestructura.adaptadores.entrada.api.seguridad import usuario_actual

router = APIRouter(prefix="/ofertas", tags=["usuario"])


@router.post("/{id_oferta}/confirmar", response_model=e.ConfirmacionSalida)
def confirmar(id_oferta: int, cuerpo: e.ConfirmacionEntrada, comprador=Depends(usuario_actual),
              caso=Depends(caso_confirmar_oferta)):
    """Dos desmentidos de personas distintas pausan la oferta y la mandan a revisión."""
    r = caso.ejecutar(comprador, id_oferta, cuerpo.la_vio_asi)
    olvidar()
    return e.ConfirmacionSalida(confirmaron=r.confirmaron, desmintieron=r.desmintieron, pausada=r.pausada)
