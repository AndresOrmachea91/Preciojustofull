"""
Cifrado de contraseñas con scrypt, de la biblioteca estándar.

scrypt es deliberadamente caro en memoria, lo que encarece los ataques por
fuerza bruta con GPU. No se suma una dependencia (bcrypt, passlib) para
algo que Python ya trae.

El hash guarda sus propios parámetros: "scrypt$n$r$p$sal$hash". Si mañana
se suben los costos, los hashes viejos se siguen verificando.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

_N, _R, _P = 2**14, 8, 1
_LARGO = 32


def _b64(datos: bytes) -> str:
    return base64.b64encode(datos).decode("ascii")


class CifradorScrypt:
    def cifrar(self, contrasena: str) -> str:
        sal = secrets.token_bytes(16)
        hash_ = hashlib.scrypt(contrasena.encode("utf-8"), salt=sal, n=_N, r=_R, p=_P, dklen=_LARGO)
        return f"scrypt${_N}${_R}${_P}${_b64(sal)}${_b64(hash_)}"

    def verificar(self, contrasena: str, hash_guardado: str) -> bool:
        try:
            esquema, n, r, p, sal, esperado = hash_guardado.split("$")
            if esquema != "scrypt":
                return False
            esperado_bytes = base64.b64decode(esperado)
            calculado = hashlib.scrypt(
                contrasena.encode("utf-8"), salt=base64.b64decode(sal),
                n=int(n), r=int(r), p=int(p), dklen=len(esperado_bytes),
            )
        except (ValueError, TypeError):
            return False
        # Comparación en tiempo constante: no filtra por cuántos bytes coinciden.
        return hmac.compare_digest(calculado, esperado_bytes)
