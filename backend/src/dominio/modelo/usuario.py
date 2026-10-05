"""
Usuarios y roles.

El dominio decide QUÉ puede hacer cada rol; cómo se demuestra quién es
quién (contraseñas, tokens) es un detalle de los adaptadores. Por eso acá
no hay ni hash ni JWT: el hash viaja como un texto opaco que el dominio
guarda pero no interpreta.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum

from src.dominio.excepciones import ContrasenaDebil, CorreoInvalido

_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LARGO_MINIMO_CONTRASENA = 8


class Rol(str, Enum):
    """
    Tres roles, de menos a más privilegio. Una sola cuenta tiene un solo
    rol: el recolector no es "un usuario con permisos extra", es otro
    trabajo, y el administrador opera el sistema.
    """

    USUARIO = "usuario"
    RECOLECTOR = "recolector"
    ADMINISTRADOR = "administrador"


class Permiso(str, Enum):
    REPORTAR_PRECIO = "reportar_precio"
    REGISTRAR_COTIZACION = "registrar_cotizacion"
    GESTIONAR_USUARIOS = "gestionar_usuarios"
    VALIDAR_REPORTES = "validar_reportes"


# La matriz de permisos es una regla del negocio, no de la API: vive acá
# para que la web, la app móvil y la línea de comandos apliquen la misma.
PERMISOS_POR_ROL: dict[Rol, frozenset[Permiso]] = {
    Rol.USUARIO: frozenset({Permiso.REPORTAR_PRECIO}),
    Rol.RECOLECTOR: frozenset({Permiso.REPORTAR_PRECIO, Permiso.REGISTRAR_COTIZACION}),
    Rol.ADMINISTRADOR: frozenset(Permiso),
}


def normalizar_correo(correo: str) -> str:
    correo = correo.strip().lower()
    if not _CORREO.match(correo):
        raise CorreoInvalido(correo)
    return correo


def validar_contrasena(contrasena: str) -> None:
    if len(contrasena) < LARGO_MINIMO_CONTRASENA:
        raise ContrasenaDebil(f"La contraseña debe tener al menos {LARGO_MINIMO_CONTRASENA} caracteres")
    if contrasena.isdigit() or contrasena.isalpha():
        raise ContrasenaDebil("La contraseña debe combinar letras y números")


@dataclass(frozen=True, slots=True)
class Usuario:
    correo: str
    nombre: str
    rol: Rol
    hash_contrasena: str
    creado_en: datetime
    activo: bool = True
    # None hasta que el repositorio lo guarda por primera vez.
    id: int | None = None

    def puede(self, permiso: Permiso) -> bool:
        # Una cuenta desactivada no puede nada, sea cual sea su rol.
        return self.activo and permiso in PERMISOS_POR_ROL[self.rol]

    @property
    def es_administrador(self) -> bool:
        return self.activo and self.rol is Rol.ADMINISTRADOR

    def con_rol(self, rol: Rol) -> Usuario:
        return replace(self, rol=rol)

    def con_activo(self, activo: bool) -> Usuario:
        return replace(self, activo=activo)

    def con_hash(self, hash_contrasena: str) -> Usuario:
        return replace(self, hash_contrasena=hash_contrasena)
