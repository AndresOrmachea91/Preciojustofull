"""Ofertas pausadas por los compradores: /api/v1/admin/ofertas (C133)."""
from fastapi import APIRouter, Depends

from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.cache_fichas import olvidar
from src.infraestructura.adaptadores.entrada.api.dependencias import caso_revisar_ofertas
from src.infraestructura.adaptadores.entrada.api.mapeo import oferta_en_revision_a_salida
from src.infraestructura.adaptadores.entrada.api.seguridad import usuario_actual

router = APIRouter(prefix="/admin/ofertas", tags=["administracion"])


@router.get("/revision", response_model=list[e.OfertaEnRevisionSalida])
def en_revision(actor=Depends(usuario_actual), caso=Depends(caso_revisar_ofertas)):
    return [oferta_en_revision_a_salida(r) for r in caso.pendientes(actor)]


@router.post("/{id_oferta}/reactivar", status_code=204)
def reactivar(id_oferta: int, actor=Depends(usuario_actual), caso=Depends(caso_revisar_ofertas)):
    """Era verdad: vuelve a mostrarse hasta que venza."""
    caso.reactivar(actor, id_oferta)
    olvidar()


@router.post("/{id_oferta}/retirar", status_code=204)
def retirar(id_oferta: int, actor=Depends(usuario_actual), caso=Depends(caso_revisar_ofertas)):
    caso.retirar(actor, id_oferta)
    olvidar()
