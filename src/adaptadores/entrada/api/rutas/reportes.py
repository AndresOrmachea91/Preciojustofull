from fastapi import APIRouter, Depends, HTTPException

from src.adaptadores.entrada.api import esquemas as e
from src.adaptadores.entrada.api.dependencias import caso_registrar_reporte
from src.dominio.excepciones import ErrorDominio

router = APIRouter(prefix="/reportes", tags=["reportes"])


@router.post("", response_model=e.ReporteSalida, status_code=201)
def reportar(cuerpo: e.ReporteEntrada, caso=Depends(caso_registrar_reporte)):
    """
    Un reporte no se publica directo: entra como una observación más y el
    motor de fusión decide cuánto pesa frente a las otras fuentes.
    """
    try:
        caso.ejecutar(
            cuerpo.codigo_producto, cuerpo.codigo_mercado, cuerpo.monto, cuerpo.unidad
        )
    except ErrorDominio as ex:
        raise HTTPException(status_code=400, detail=str(ex))
    return e.ReporteSalida(
        aceptado=True,
        mensaje="Reporte recibido. Se contrastará con las demás fuentes antes de publicarse.",
    )

