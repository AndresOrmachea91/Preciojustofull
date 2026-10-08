"""Ingreso y verificación de la sesión en cada petición."""
from __future__ import annotations

from dataclasses import dataclass

from src.aplicacion.puertos.salida import CifradorContrasenas, EmisorTokens, RepositorioUsuarios
from src.dominio.excepciones import CredencialesInvalidas
from src.dominio.modelo import Usuario
from src.dominio.modelo.usuario import normalizar_correo


@dataclass(frozen=True, slots=True)
class Sesion:
    token: str
    usuario: Usuario


class IniciarSesion:
    def __init__(self, usuarios: RepositorioUsuarios, cifrador: CifradorContrasenas,
                 tokens: EmisorTokens):
        self._usuarios = usuarios
        self._cifrador = cifrador
        self._tokens = tokens

    def ejecutar(self, correo: str, contrasena: str) -> Sesion:
        try:
            correo = normalizar_correo(correo)
        except Exception:
            raise CredencialesInvalidas()
        usuario = self._usuarios.obtener_por_correo(correo)
        # Se verifica la contraseña aunque la cuenta esté desactivada, y el
        # error es el mismo en los tres casos: no se filtra qué falló.
        if usuario is None or not self._cifrador.verificar(contrasena, usuario.hash_contrasena):
            raise CredencialesInvalidas()
        if not usuario.activo:
            raise CredencialesInvalidas()
        return Sesion(self._tokens.emitir(usuario), usuario)


class ResolverSesion:
    """
    Del token al usuario, consultando la base en cada petición: si un
    administrador desactiva una cuenta o le cambia el rol, el cambio rige
    en la petición siguiente, sin esperar a que venza el token.
    """

    def __init__(self, usuarios: RepositorioUsuarios, tokens: EmisorTokens):
        self._usuarios = usuarios
        self._tokens = tokens

    def ejecutar(self, token: str) -> Usuario | None:
        id_usuario = self._tokens.leer(token)
        if id_usuario is None:
            return None
        usuario = self._usuarios.obtener(id_usuario)
        if usuario is None or not usuario.activo:
            return None
        return usuario
