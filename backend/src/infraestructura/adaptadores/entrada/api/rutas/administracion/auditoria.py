"""Auditoría y catálogos de referencia: /api/v1/admin/auditoria y /api/v1/admin/referencias."""
from dataclasses import asdict

from fastapi import APIRouter, Depends, Query

from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.dependencias import (
    caso_consultar_referencias, caso_ver_auditoria,
)
from src.infraestructura.adaptadores.entrada.api.mapeo import registro_auditado_a_salida
from src.infraestructura.adaptadores.entrada.api.seguridad import usuario_actual

router = APIRouter(prefix="/admin", tags=["administración"])


@router.get("/auditoria", response_model=list[e.RegistroAuditadoSalida])
def recientes(tabla: str | None = Query(default=None), limite: int = Query(default=50, ge=1, le=200),
              actor=Depends(usuario_actual), caso=Depends(caso_ver_auditoria)):
    """Quién creó, modificó o eliminó cada registro, lo más reciente primero."""
    return [registro_auditado_a_salida(r) for r in caso.recientes(actor, tabla, limite)]


@router.get("/auditoria/tablas", response_model=list[str])
def tablas(actor=Depends(usuario_actual), caso=Depends(caso_ver_auditoria)):
    return caso.tablas(actor)


@router.get("/referencias", response_model=e.ReferenciasSalida)
def referencias(actor=Depends(usuario_actual), caso=Depends(caso_consultar_referencias)):
    """Los roles con sus permisos y las fuentes de precios con su confianza."""
    return e.ReferenciasSalida(
        roles=[e.RolSalida(**asdict(r)) for r in caso.roles(actor)],
        fuentes=[e.FuenteSalida(**asdict(f)) for f in caso.fuentes(actor)],
    )
