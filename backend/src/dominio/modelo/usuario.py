"""
Usuarios y roles.

El dominio decide QUÉ puede hacer cada rol; cómo se demuestra quién es
quién (contraseñas, tokens) es un detalle de los adaptadores. Por eso acá
no hay ni hash ni JWT: el hash viaja como un texto opaco que el dominio
guarda pero no interpreta.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum

from src.dominio.excepciones import DatoInvalido, ContrasenaDebil, CorreoInvalido
from src.dominio.modelo.auditoria import Auditoria

_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LARGO_MINIMO_CONTRASENA = 8


class Rol(str, Enum):
    """
    Tres roles. Una cuenta tiene un solo rol:

    - USUARIO: consulta precios, arma sus listas y reporta lo que ve.
    - VENDEDOR: además publica los precios de SU puesto o tienda, que le
      asigna el administrador. No es "un usuario con permisos extra": su
      precio es una declaración sobre su propio negocio.
    - ADMINISTRADOR: opera el sistema (cuentas, catálogo, reportes, auditoría)
      y hace las rondas de campo.
    """

    USUARIO = "usuario"
    VENDEDOR = "vendedor"
    ADMINISTRADOR = "administrador"


class Permiso(str, Enum):
    REPORTAR_PRECIO = "reportar_precio"
    GESTIONAR_LISTAS = "gestionar_listas"
    PUBLICAR_PRECIO_PROPIO = "publicar_precio_propio"
    GESTIONAR_USUARIOS = "gestionar_usuarios"
    GESTIONAR_CATALOGO = "gestionar_catalogo"
    VALIDAR_REPORTES = "validar_reportes"
    VER_AUDITORIA = "ver_auditoria"
    IMPORTAR_CAMPO = "importar_campo"
    VER_SALUD = "ver_salud"


# La matriz de permisos es una regla del negocio, no de la API: vive acá
# para que la web, la app móvil y la línea de comandos apliquen la misma.
PERMISOS_POR_ROL: dict[Rol, frozenset[Permiso]] = {
    Rol.USUARIO: frozenset({Permiso.REPORTAR_PRECIO, Permiso.GESTIONAR_LISTAS}),
    Rol.VENDEDOR: frozenset({
        Permiso.REPORTAR_PRECIO, Permiso.GESTIONAR_LISTAS, Permiso.PUBLICAR_PRECIO_PROPIO,
    }),
    Rol.ADMINISTRADOR: frozenset(Permiso),
}


# Las caseras registradas en su puesto entran con su celular (C144): por
# dentro, la cuenta es <celular>@caseras.preciojusto.bo.
DOMINIO_CASERAS = "caseras.preciojusto.bo"
_CELULAR = re.compile(r"^[67]\d{7}$")


def celular_boliviano(texto: str) -> str | None:
    """'+591 712-34567' → '71234567'. None si no es un celular de Bolivia (8 dígitos, empieza en 6 o 7)."""
    digitos = re.sub(r"[\s\-().]", "", texto or "")
    if digitos.startswith("+591"):
        digitos = digitos[4:]
    elif digitos.startswith("591") and len(digitos) == 11:
        digitos = digitos[3:]
    return digitos if _CELULAR.match(digitos) else None


def correo_de_celular(celular: str) -> str:
    numero = celular_boliviano(celular)
    if numero is None:
        raise DatoInvalido("El celular debe tener 8 dígitos y empezar en 6 o 7")
    return f"{numero}@{DOMINIO_CASERAS}"


def identificador_de_ingreso(texto: str) -> str:
    """Se entra con el correo o, si es una casera, con su celular."""
    numero = celular_boliviano(texto)
    return f"{numero}@{DOMINIO_CASERAS}" if numero else texto


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
    # Código del puesto o tienda del VENDEDOR (un punto de venta del
    # catálogo). Lo asigna el administrador; los otros roles no lo usan.
    codigo_punto_venta: str | None = None
    # None hasta que el repositorio lo guarda por primera vez.
    id: int | None = None
    # Quién y cuándo lo creó, modificó o eliminó. Lo llena el repositorio
    # al leer; no cuenta para comparar dos usuarios.
    auditoria: Auditoria | None = field(default=None, compare=False)

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

    def con_punto_venta(self, codigo: str | None) -> Usuario:
        return replace(self, codigo_punto_venta=codigo)
