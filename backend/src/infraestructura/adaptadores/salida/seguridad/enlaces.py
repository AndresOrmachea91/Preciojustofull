"""
Enlaces de recuperación de contraseña: un JWT corto con propósito propio.

Lleva una HUELLA del hash de la contraseña actual: cuando la persona elige
una nueva, la huella deja de coincidir y el enlace muere. Así sirve una sola
vez sin guardar nada en la base. Un token de sesión no sirve como enlace
(propósito distinto), y viceversa.
"""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import jwt

from src.dominio.modelo import Usuario

_ALGORITMO = "HS256"
_PROPOSITO = "recuperar-contrasena"


def _huella(usuario: Usuario) -> str:
    return hashlib.sha256(usuario.hash_contrasena.encode()).hexdigest()[:24]


class EnlacesJwt:
    def __init__(self, secreto: str, minutos_validez: int = 30, emisor: str = "preciojusto"):
        if len(secreto) < 32:
            raise ValueError("El secreto de los enlaces debe tener al menos 32 caracteres")
        self._secreto = secreto
        self._validez = timedelta(minutes=minutos_validez)
        self._emisor = emisor

    def emitir(self, usuario: Usuario) -> str:
        ahora = datetime.now(timezone.utc)
        return jwt.encode(
            {"sub": str(usuario.id), "iss": self._emisor, "aud": _PROPOSITO, "iat": ahora,
             "exp": ahora + self._validez, "h": _huella(usuario)},
            self._secreto, algorithm=_ALGORITMO,
        )

    def _datos(self, enlace: str) -> dict | None:
        try:
            return jwt.decode(enlace, self._secreto, algorithms=[_ALGORITMO], issuer=self._emisor,
                              audience=_PROPOSITO, options={"require": ["sub", "exp", "iss", "aud", "h"]})
        except jwt.InvalidTokenError:
            return None

    def id_de(self, enlace: str) -> int | None:
        datos = self._datos(enlace)
        try:
            return int(datos["sub"]) if datos else None
        except (ValueError, KeyError):
            return None

    def vigente_para(self, enlace: str, usuario: Usuario) -> bool:
        datos = self._datos(enlace)
        return bool(datos) and hmac.compare_digest(str(datos.get("h")), _huella(usuario))
