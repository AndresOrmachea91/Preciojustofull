"""
Los datos de prueba (sembrar_demo): las fotos ilustradas son imágenes que el
almacén acepta, y el comando nunca escribe sin base o contra Neon.
"""
from src.dominio.modelo.foto import extension_de_imagen
from src.infraestructura.adaptadores.entrada.cli import sembrar_demo
from src.infraestructura.adaptadores.entrada.cli.sembrar_demo import PUESTOS, SURTIDO, foto_de_puesto


def test_la_foto_ilustrada_es_un_png_valido_y_liviano():
    foto = foto_de_puesto("verduras", 3)
    assert extension_de_imagen(foto) == "png"
    assert len(foto) < 2_500_000


def test_cada_puesto_de_prueba_tiene_un_surtido_conocido():
    assert all(clase in SURTIDO for _, _, _, clase, _ in PUESTOS)
    # Un número por mercado: dos caseros no comparten puesto.
    assert len({(m, n) for m, n, *_ in PUESTOS}) == len(PUESTOS)


def test_sin_base_de_datos_no_siembra(monkeypatch):
    monkeypatch.setattr(sembrar_demo.config, "base_datos_url", "")
    monkeypatch.setattr("sys.argv", ["sembrar_demo"])
    assert sembrar_demo.main() == 2


def test_nunca_siembra_en_neon(monkeypatch):
    monkeypatch.setattr(sembrar_demo.config, "base_datos_url", "postgresql://x@ep-algo.neon.tech/db")
    monkeypatch.setattr("sys.argv", ["sembrar_demo"])
    assert sembrar_demo.main() == 2
