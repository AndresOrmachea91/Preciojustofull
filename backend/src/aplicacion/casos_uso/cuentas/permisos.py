"""
La única puerta de los permisos en la capa de aplicación.

Cada caso de uso que hace algo restringido llama a `exigir` antes de
actuar. La matriz (qué rol puede qué) es una regla del dominio y vive en
dominio/modelo/usuario.py; acá solo se aplica.
"""
from __future__ import annotations

from src.dominio.excepciones import PermisoDenegado
from src.dominio.modelo import Permiso, Usuario


def exigir(actor: Usuario, permiso: Permiso) -> None:
    if not actor.puede(permiso):
        raise PermisoDenegado(permiso.value)
