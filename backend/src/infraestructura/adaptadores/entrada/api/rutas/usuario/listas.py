"""Listas de compras del usuario: /api/v1/listas."""
from fastapi import APIRouter, Depends, Query, Response

from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.dependencias import caso_gestionar_listas
from src.infraestructura.adaptadores.entrada.api.mapeo import canasta_a_salida, lista_a_salida
from src.infraestructura.adaptadores.entrada.api.seguridad import usuario_actual
from src.aplicacion.casos_uso.usuario.listas_compras import RenglonPedido
from src.dominio.modelo import Presentacion

router = APIRouter(prefix="/listas", tags=["usuario"])


def _renglones(cuerpo: e.ListaEntrada) -> list[RenglonPedido]:
    return [RenglonPedido(i.codigo_producto, i.cantidad, Presentacion(i.presentacion)) for i in cuerpo.items]


@router.get("", response_model=list[e.ListaSalida])
def mis_listas(actor=Depends(usuario_actual), caso=Depends(caso_gestionar_listas)):
    return [lista_a_salida(l) for l in caso.listar(actor)]


@router.post("", response_model=e.ListaSalida, status_code=201)
def crear(cuerpo: e.ListaEntrada, actor=Depends(usuario_actual), caso=Depends(caso_gestionar_listas)):
    return lista_a_salida(caso.crear(actor, cuerpo.nombre, _renglones(cuerpo)))


@router.put("/{id_lista}", response_model=e.ListaSalida)
def actualizar(id_lista: int, cuerpo: e.ListaEntrada, actor=Depends(usuario_actual),
               caso=Depends(caso_gestionar_listas)):
    return lista_a_salida(caso.actualizar(actor, id_lista, cuerpo.nombre, _renglones(cuerpo)))


@router.delete("/{id_lista}", status_code=204)
def eliminar(id_lista: int, actor=Depends(usuario_actual), caso=Depends(caso_gestionar_listas)):
    caso.eliminar(actor, id_lista)
    return Response(status_code=204)


@router.get("/{id_lista}/cotizar", response_model=list[e.CanastaSalida])
def cotizar(id_lista: int, zona: str | None = Query(default=None), actor=Depends(usuario_actual),
            caso=Depends(caso_gestionar_listas)):
    """Cuánto cuesta la lista completa en cada mercado, de más conveniente a menos."""
    return [canasta_a_salida(c) for c in caso.cotizar(actor, id_lista, zona)]
