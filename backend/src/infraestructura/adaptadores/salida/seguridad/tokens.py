"""
Tokens de sesión firmados (JWT, HS256).

El token solo lleva el id del usuario y su vencimiento. El rol NO se confía
al token: se lee de la base en cada petición (ResolverSesion), para que
quitarle un permiso a alguien rija de inmediato.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from src.dominio.modelo import Usuario

_ALGORITMO = "HS256"


class EmisorJwt:
    def __init__(self, secreto: str, horas_validez: float = 8.0, emisor: str = "preciojusto"):
        if len(secreto) < 32:
            raise ValueError("El secreto de los tokens debe tener al menos 32 caracteres")
        self._secreto = secreto
        self._validez = timedelta(hours=horas_validez)
        self._emisor = emisor

    def emitir(self, usuario: Usuario) -> str:
        ahora = datetime.now(timezone.utc)
        return jwt.encode(
            {"sub": str(usuario.id), "iss": self._emisor, "iat": ahora, "exp": ahora + self._validez},
            self._secreto,
            algorithm=_ALGORITMO,
        )

    def leer(self, token: str) -> int | None:
        try:
            datos = jwt.decode(
                token, self._secreto, algorithms=[_ALGORITMO], issuer=self._emisor,
                options={"require": ["sub", "exp", "iss"]},
            )
            return int(datos["sub"])
        except (jwt.InvalidTokenError, ValueError, KeyError):
            return None
