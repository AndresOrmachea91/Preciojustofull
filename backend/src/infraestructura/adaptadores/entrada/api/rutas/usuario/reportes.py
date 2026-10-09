"""El usuario reporta un precio que vio (POST /api/v1/reportes) y sigue sus reportes (GET /mios)."""
from fastapi import APIRouter, Depends

from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.dependencias import caso_mis_reportes, caso_registrar_reporte
from src.infraestructura.adaptadores.entrada.api.mapeo import reporte_a_salida
from src.infraestructura.adaptadores.entrada.api.seguridad import usuario_actual

router = APIRouter(prefix="/reportes", tags=["usuario"])


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


@router.get("/mios", response_model=list[e.ReporteRevisionSalida])
def mis_reportes(autor=Depends(usuario_actual), caso=Depends(caso_mis_reportes)):
    """Mis reportes, del más nuevo al más viejo, con su estado y el motivo si se rechazó."""
    return [reporte_a_salida(r) for r in caso.ejecutar(autor)]
