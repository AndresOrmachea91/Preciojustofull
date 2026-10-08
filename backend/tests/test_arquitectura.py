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



def test_los_casos_de_uso_no_construyen_sus_dependencias():
    """
    Los objetos se construyen solo en la raíz de composición
    (api/dependencias.py, los comandos de consola y las pruebas). Un caso de
    uso que hace `MotorFusion()` por su cuenta esconde una dependencia y ya
    no se le puede pasar otra configuración del motor.
    """
    infracciones = [
        archivo.name for archivo in _archivos("aplicacion")
        if "MotorFusion()" in archivo.read_text(encoding="utf-8")
    ]
    assert not infracciones, "Construyen el motor por su cuenta: " + ", ".join(infracciones)


PUBLICAN_PRECIOS = ("consultar_precio.py", "comparar_mercados.py", "calcular_canasta.py")


def test_los_casos_que_publican_precios_solo_reciben_lectores():
    """Consultar, comparar y la canasta no pueden escribir en la base, ni por descuido."""
    infracciones = []
    for archivo in _archivos("aplicacion/casos_uso"):
        if archivo.name not in PUBLICAN_PRECIOS:
            continue
        texto = archivo.read_text(encoding="utf-8")
        for puerto in ("Escritor", "RepositorioProductos", "RepositorioMercados", "RepositorioObservaciones"):
            if puerto in texto:
                infracciones.append(f"{archivo.name} usa {puerto}")
    assert not infracciones, "; ".join(infracciones)
