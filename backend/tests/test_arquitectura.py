"""
Prueba que la arquitectura no se degrade con el tiempo.

Es la regla que sostiene todo: las dependencias apuntan hacia adentro. El
dominio no puede importar frameworks ni capas externas, y la aplicación no
puede importar infraestructura. Si alguien lo rompe, esta prueba falla.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1] / "src"

PROHIBIDO_EN_DOMINIO = ("fastapi", "sqlalchemy", "requests", "pydantic", "bs4",
                        "src.infraestructura", "src.aplicacion")
PROHIBIDO_EN_APLICACION = ("fastapi", "sqlalchemy", "requests", "bs4",
                           "src.infraestructura")


def _archivos(subcarpeta: str):
    return (RAIZ / subcarpeta).rglob("*.py")


def test_el_dominio_no_depende_de_ningun_framework():
    infracciones = []
    for archivo in _archivos("dominio"):
        texto = archivo.read_text(encoding="utf-8")
        for prohibido in PROHIBIDO_EN_DOMINIO:
            if f"import {prohibido}" in texto or f"from {prohibido}" in texto:
                infracciones.append(f"{archivo.name} importa {prohibido}")
    assert not infracciones, "El dominio se contaminó: " + "; ".join(infracciones)


def test_la_aplicacion_no_depende_de_los_adaptadores():
    infracciones = []
    for archivo in _archivos("aplicacion"):
        texto = archivo.read_text(encoding="utf-8")
        for prohibido in PROHIBIDO_EN_APLICACION:
            if f"import {prohibido}" in texto or f"from {prohibido}" in texto:
                infracciones.append(f"{archivo.name} importa {prohibido}")
    assert not infracciones, "La aplicación se contaminó: " + "; ".join(infracciones)

