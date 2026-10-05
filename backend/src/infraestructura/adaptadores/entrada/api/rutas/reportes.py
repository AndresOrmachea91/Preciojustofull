from typing import Literal

from fastapi import APIRouter, Depends

from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.dependencias import (
    caso_registrar_reporte, caso_validar_reportes,
)
from src.infraestructura.adaptadores.entrada.api.mapeo import reporte_a_salida
from src.infraestructura.adaptadores.entrada.api.seguridad import usuario_actual
from src.dominio.modelo import EstadoReporte

router = APIRouter(prefix="/reportes", tags=["reportes"])


@router.post("", response_model=e.ReporteSalida, status_code=201)
def reportar(cuerpo: e.ReporteEntrada, autor=Depends(usuario_actual),
             caso=Depends(caso_registrar_reporte)):
    """
    Un reporte no se publica directo: queda pendiente hasta que un
    administrador lo revisa, y recién aprobado entra al motor de fusión.
    """
    caso.ejecutar(autor, cuerpo.codigo_producto, cuerpo.codigo_mercado, cuerpo.monto, cuerpo.unidad)
    return e.ReporteSalida(
        aceptado=True,
        mensaje="Reporte recibido. Un administrador lo revisará antes de usarlo.",
    )


@router.get("", response_model=list[e.ReporteRevisionSalida])
def listar(estado: Literal["pendiente", "aprobado", "rechazado", "todos"] = "pendiente",
           actor=Depends(usuario_actual), caso=Depends(caso_validar_reportes)):
    filtro = None if estado == "todos" else EstadoReporte(estado)
    return [reporte_a_salida(r) for r in caso.listar(actor, filtro)]


@router.post("/{id_reporte}/aprobar", response_model=e.ReporteRevisionSalida)
def aprobar(id_reporte: int, actor=Depends(usuario_actual), caso=Depends(caso_validar_reportes)):
    return reporte_a_salida(caso.aprobar(actor, id_reporte))


@router.post("/{id_reporte}/rechazar", response_model=e.ReporteRevisionSalida)
def rechazar(id_reporte: int, cuerpo: e.RechazoEntrada, actor=Depends(usuario_actual),
             caso=Depends(caso_validar_reportes)):
    return reporte_a_salida(caso.rechazar(actor, id_reporte, cuerpo.motivo))
