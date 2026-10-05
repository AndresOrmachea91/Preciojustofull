"""
Cuentas, sesiones y administración de usuarios.

Los permisos se verifican ACÁ, no en la API: la app móvil y la línea de
comandos son otros adaptadores sobre los mismos casos de uso, y tienen que
aplicar exactamente la misma regla sin copiarla.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.aplicacion.puertos.salida import CifradorContrasenas, EmisorTokens, RepositorioUsuarios
from src.dominio.excepciones import (
    CorreoYaRegistrado, CredencialesInvalidas, PermisoDenegado, SinAdministradores,
    UsuarioNoEncontrado,
)
from src.dominio.modelo import Permiso, Rol, Usuario
from src.dominio.modelo.usuario import normalizar_correo, validar_contrasena


def exigir(actor: Usuario, permiso: Permiso) -> None:
    if not actor.puede(permiso):
        raise PermisoDenegado(permiso.value)


@dataclass(frozen=True, slots=True)
class Sesion:
    token: str
    usuario: Usuario


class RegistrarUsuario:
    """
    Alta de cuentas. El registro público SIEMPRE crea un usuario común:
    nadie se nombra recolector ni administrador a sí mismo. Las otras
    cuentas las crea un administrador, o el sistema desde la consola.
    """

    def __init__(self, usuarios: RepositorioUsuarios, cifrador: CifradorContrasenas):
        self._usuarios = usuarios
        self._cifrador = cifrador

    def registrarse(self, correo: str, nombre: str, contrasena: str) -> Usuario:
        return self._crear(correo, nombre, contrasena, Rol.USUARIO)

    def crear(self, actor: Usuario, correo: str, nombre: str, contrasena: str, rol: Rol) -> Usuario:
        exigir(actor, Permiso.GESTIONAR_USUARIOS)
        return self._crear(correo, nombre, contrasena, rol)

    def crear_como_sistema(self, correo: str, nombre: str, contrasena: str, rol: Rol) -> Usuario:
        """Para la consola del servidor: así nace el primer administrador."""
        return self._crear(correo, nombre, contrasena, rol)

    def _crear(self, correo: str, nombre: str, contrasena: str, rol: Rol) -> Usuario:
        correo = normalizar_correo(correo)
        validar_contrasena(contrasena)
        if self._usuarios.obtener_por_correo(correo) is not None:
            raise CorreoYaRegistrado(correo)
        return self._usuarios.guardar(Usuario(
            correo=correo,
            nombre=nombre.strip() or correo.split("@")[0],
            rol=rol,
            hash_contrasena=self._cifrador.cifrar(contrasena),
            creado_en=datetime.now(timezone.utc),
        ))


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


class AdministrarUsuarios:
    def __init__(self, usuarios: RepositorioUsuarios, cifrador: CifradorContrasenas):
        self._usuarios = usuarios
        self._cifrador = cifrador

    def listar(self, actor: Usuario) -> list[Usuario]:
        exigir(actor, Permiso.GESTIONAR_USUARIOS)
        return sorted(self._usuarios.listar(), key=lambda u: u.id or 0)

    def actualizar(self, actor: Usuario, id_usuario: int, rol: Rol | None = None,
                   activo: bool | None = None) -> Usuario:
        exigir(actor, Permiso.GESTIONAR_USUARIOS)
        usuario = self._obtener(id_usuario)
        nuevo = usuario
        if rol is not None:
            nuevo = nuevo.con_rol(rol)
        if activo is not None:
            nuevo = nuevo.con_activo(activo)
        # Quitarle el rol o desactivar al último administrador dejaría el
        # sistema sin nadie que pueda revertirlo desde la aplicación.
        if usuario.es_administrador and not nuevo.es_administrador:
            if self._usuarios.contar_administradores_activos() <= 1:
                raise SinAdministradores()
        return self._usuarios.guardar(nuevo)

    def restablecer_contrasena(self, actor: Usuario, id_usuario: int, contrasena: str) -> Usuario:
        exigir(actor, Permiso.GESTIONAR_USUARIOS)
        validar_contrasena(contrasena)
        usuario = self._obtener(id_usuario)
        return self._usuarios.guardar(usuario.con_hash(self._cifrador.cifrar(contrasena)))

    def _obtener(self, id_usuario: int) -> Usuario:
        usuario = self._usuarios.obtener(id_usuario)
        if usuario is None:
            raise UsuarioNoEncontrado(id_usuario)
        return usuario
