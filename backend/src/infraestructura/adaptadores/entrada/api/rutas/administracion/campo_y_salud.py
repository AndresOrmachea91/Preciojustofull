"""Levantamiento de campo y salud del sistema: /api/v1/admin/campo/... y /api/v1/admin/salud."""
import csv
import io
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from src.aplicacion.casos_uso.administracion.importar_campo import COLUMNAS_OBLIGATORIAS, COLUMNAS_OPCIONALES
from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.dependencias import (
    caso_importar_campo, caso_salud_sistema, hoy_en_bolivia,
)
from src.infraestructura.adaptadores.entrada.api.seguridad import usuario_actual

router = APIRouter(prefix="/admin", tags=["administración"])

_EJEMPLO = [
    ("2026-10-18", "rodriguez", "papa_holandesa", "8,50", "kilo", "", "", "ana", "cotizado"),
    ("2026-10-18", "rodriguez", "tomate", "60", "arroba", "", "", "ana", "pagado"),
]


def _filas(texto: str) -> list[dict[str, str]]:
    """Del texto CSV a filas. Acepta coma o punto y coma (Excel en español guarda con ';')."""
    texto = texto.lstrip("﻿")
    encabezado = texto.splitlines()[0] if texto.strip() else ""
    if not encabezado:
        raise HTTPException(status_code=400, detail="La planilla está vacía")
    separador = ";" if encabezado.count(";") > encabezado.count(",") else ","
    lector = csv.DictReader(io.StringIO(texto), delimiter=separador)
    lector.fieldnames = [c.strip().lower() for c in (lector.fieldnames or [])]
    faltan = [c for c in COLUMNAS_OBLIGATORIAS if c not in lector.fieldnames]
    if faltan:
        raise HTTPException(status_code=400, detail=f"Faltan las columnas: {', '.join(faltan)}")
    return [fila for fila in lector if any((v or "").strip() for v in fila.values() if isinstance(v, str))]


@router.get("/campo/plantilla", response_class=PlainTextResponse)
def plantilla():
    """Una planilla de ejemplo con las columnas que se esperan."""
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";")
    escritor.writerow(COLUMNAS_OBLIGATORIAS + COLUMNAS_OPCIONALES)
    escritor.writerows(_EJEMPLO)
    return PlainTextResponse(salida.getvalue(), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": 'attachment; filename="plantilla_campo.csv"'})


@router.post("/campo/importar", response_model=e.ImportarCampoSalida)
def importar(cuerpo: e.ImportarCampoEntrada, actor=Depends(usuario_actual), caso=Depends(caso_importar_campo)):
    """Carga las cotizaciones de campo. Con solo_revisar=true dice qué entraría, sin guardar."""
    r = caso.ejecutar(actor, _filas(cuerpo.csv), hoy_en_bolivia(), cuerpo.solo_revisar, cuerpo.archivo)
    return e.ImportarCampoSalida(
        leidas=r.leidas, validas=r.validas, guardadas=r.guardadas, solo_revisar=cuerpo.solo_revisar,
        rechazadas=[e.FilaRechazadaSalida(fila=f.fila, motivo=f.motivo) for f in r.rechazadas],
    )


@router.get("/salud", response_model=e.SaludSalida)
def salud(actor=Depends(usuario_actual), caso=Depends(caso_salud_sistema)):
    """Recolección, respaldos y cobertura de datos observados, con un estado por punto."""
    s = caso.ejecutar(actor, hoy_en_bolivia())
    return e.SaludSalida(
        estado_general=s.estado_general,
        puntos=[e.PuntoSaludSalida(**asdict(p)) for p in s.puntos],
        fuentes=[e.FuenteSaludSalida(**asdict(f)) for f in s.fuentes],
        recolecciones=[e.RecoleccionSalida(**asdict(r)) for r in s.recolecciones],
        respaldo=e.RespaldoSalida(**asdict(s.respaldo)) if s.respaldo else None,
        cobertura_observada=s.cobertura_observada,
        ventana_dias=s.ventana_dias,
    )
