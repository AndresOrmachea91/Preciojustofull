"""
Las fotos de los puestos en una carpeta del servidor (C137). En Docker es
un volumen propio (fotos), así sobreviven a reconstruir la imagen.

El nombre del archivo es aleatorio (no el número del puesto ni el del
vendedor): no se puede adivinar ni pisar una foto ajena. Al servir, solo se
aceptan nombres con esa misma forma, así nadie pide "../../.env".
"""
from __future__ import annotations

import re
import secrets
from pathlib import Path

_NOMBRE_VALIDO = re.compile(r"^[0-9a-f]{32}\.(jpg|png|webp)$")


class AlmacenFotosLocal:
    def __init__(self, carpeta: str | Path):
        self._carpeta = Path(carpeta)

    def guardar(self, contenido: bytes, extension: str) -> str:
        self._carpeta.mkdir(parents=True, exist_ok=True)
        nombre = f"{secrets.token_hex(16)}.{extension}"
        (self._carpeta / nombre).write_bytes(contenido)
        return nombre

    def ruta(self, nombre: str) -> str | None:
        if not _NOMBRE_VALIDO.match(nombre or ""):
            return None
        archivo = self._carpeta / nombre
        return str(archivo) if archivo.is_file() else None
