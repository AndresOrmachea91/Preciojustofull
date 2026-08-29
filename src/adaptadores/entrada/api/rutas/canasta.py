from fastapi import APIRouter, Depends

from src.adaptadores.entrada.api import esquemas as e
from src.adaptadores.entrada.api.dependencias import caso_calcular_canasta
from src.adaptadores.entrada.api.mapeo import canasta_a_salida
from src.aplicacion.puertos.entrada import ItemCanasta

router = APIRouter(prefix="/canasta", tags=["canasta"])


@router.post("/calcular", response_model=list[e.CanastaSalida])
def calcular(cuerpo: e.CanastaEntrada, caso=Depends(caso_calcular_canasta)):
    """Cuánto sale la lista completa de compras en cada punto de venta."""
    items = [ItemCanasta(i.codigo_producto, i.cantidad) for i in cuerpo.items]
    return [canasta_a_salida(c) for c in caso.ejecutar(items, cuerpo.zona)]

