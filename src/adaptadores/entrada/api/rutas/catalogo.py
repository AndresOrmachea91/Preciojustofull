from fastapi import APIRouter, Depends, Query

from src.adaptadores.entrada.api import esquemas as e
from src.adaptadores.entrada.api.dependencias import obtener_mercados, obtener_productos
from src.adaptadores.entrada.api.mapeo import mercado_a_salida, producto_a_salida

router = APIRouter(tags=["catalogo"])


@router.get("/productos", response_model=list[e.ProductoSalida])
def listar_productos(repo=Depends(obtener_productos)):
    return [producto_a_salida(p) for p in repo.listar()]


@router.get("/mercados", response_model=list[e.MercadoSalida])
def listar_mercados(
    zona: str | None = Query(default=None, description="Filtra por zona de la ciudad"),
    repo=Depends(obtener_mercados),
):
    return [mercado_a_salida(m) for m in repo.listar(zona)]

