"""
El casero registra su puesto y maneja sus ofertas (C133):

    GET/PUT  /api/v1/vendedor/puesto
    GET/POST /api/v1/vendedor/ofertas
    POST     /api/v1/vendedor/ofertas/{id}/retirar
"""
from fastapi import APIRouter, Depends

from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.cache_fichas import olvidar
from src.infraestructura.adaptadores.entrada.api.dependencias import caso_mi_puesto, caso_ofertas_del_casero
from src.infraestructura.adaptadores.entrada.api.mapeo import mi_oferta_a_salida, puesto_a_salida
from src.infraestructura.adaptadores.entrada.api.seguridad import usuario_actual
from src.dominio.modelo import Presentacion

router = APIRouter(prefix="/vendedor", tags=["vendedor"])


@router.get("/puesto", response_model=e.PuestoSalida | None)
def mi_puesto(vendedor=Depends(usuario_actual), caso=Depends(caso_mi_puesto)):
    puesto = caso.ver(vendedor)
    return puesto_a_salida(puesto) if puesto else None


@router.put("/puesto", response_model=e.PuestoSalida)
def guardar_puesto(cuerpo: e.PuestoEntrada, vendedor=Depends(usuario_actual), caso=Depends(caso_mi_puesto)):
    puesto = caso.guardar(vendedor, cuerpo.numero, cuerpo.nombre, cuerpo.rubros, cuerpo.referencia,
                          cuerpo.codigo_mercado)
    olvidar()
    return puesto_a_salida(puesto)


@router.get("/ofertas", response_model=list[e.MiOfertaSalida])
def mis_ofertas(vendedor=Depends(usuario_actual), caso=Depends(caso_ofertas_del_casero)):
    return [mi_oferta_a_salida(m) for m in caso.mias(vendedor)]


@router.post("/ofertas", response_model=e.ReporteSalida, status_code=201)
def publicar(cuerpo: e.OfertaEntrada, vendedor=Depends(usuario_actual), caso=Depends(caso_ofertas_del_casero)):
    """Solo si es más barata que el precio del sistema en su mercado. Vence sola."""
    caso.publicar(vendedor, cuerpo.codigo_producto, cuerpo.monto, Presentacion(cuerpo.presentacion),
                  cuerpo.horas, cuerpo.nota)
    olvidar()
    return e.ReporteSalida(
        aceptado=True,
        mensaje=f"Oferta publicada por {cuerpo.horas} horas. Se muestra como declarada por usted.",
    )


@router.post("/ofertas/combo", response_model=e.ReporteSalida, status_code=201)
def publicar_combo(cuerpo: e.ComboEntrada, vendedor=Depends(usuario_actual),
                   caso=Depends(caso_ofertas_del_casero)):
    """C145: 2 o 3 productos en oferta juntos. Cada uno tiene que ser más barato que el sistema."""
    caso.publicar_combo(vendedor, cuerpo.nombre,
                        [(r.codigo_producto, r.monto, Presentacion(r.presentacion)) for r in cuerpo.renglones],
                        cuerpo.horas, cuerpo.nota)
    olvidar()
    return e.ReporteSalida(
        aceptado=True,
        mensaje=f"Combo «{cuerpo.nombre}» publicado por {cuerpo.horas} horas: cuenta como una sola oferta.",
    )


@router.post("/ofertas/{id_oferta}/retirar", status_code=204)
def retirar(id_oferta: int, vendedor=Depends(usuario_actual), caso=Depends(caso_ofertas_del_casero)):
    caso.retirar(vendedor, id_oferta)
    olvidar()
