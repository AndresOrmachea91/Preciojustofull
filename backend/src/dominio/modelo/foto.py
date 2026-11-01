"""
La foto de un puesto: la reconoce quien llega al mercado ("es el de la
lona verde"). Se acepta solo lo que es de verdad una imagen, por su firma
de bytes y no por la extensión que dice el archivo, y de tamaño razonable:
el celular la achica antes de mandarla.
"""
from __future__ import annotations

from src.dominio.excepciones import DatoInvalido

BYTES_MAXIMOS = 2_500_000
_FIRMAS = (
    (b"\xff\xd8\xff", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
)


def extension_de_imagen(contenido: bytes) -> str:
    """La extensión que corresponde a los bytes; DatoInvalido si no es una imagen aceptada."""
    if not contenido:
        raise DatoInvalido("La foto llegó vacía")
    if len(contenido) > BYTES_MAXIMOS:
        raise DatoInvalido(f"La foto pesa más de {BYTES_MAXIMOS // 1_000_000} MB: tómela de nuevo o achíquela")
    for firma, extension in _FIRMAS:
        if contenido.startswith(firma):
            return extension
    # WEBP: "RIFF" + 4 bytes de largo + "WEBP".
    if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "webp"
    raise DatoInvalido("La foto tiene que ser JPG, PNG o WEBP")
