"""El usuario reporta un precio que vio: POST /api/v1/reportes."""
from fastapi import APIRouter, Depends

from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.dependencias import caso_registrar_reporte
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
