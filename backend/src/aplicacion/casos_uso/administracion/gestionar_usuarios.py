"""El administrador gestiona las cuentas: rol, estado, punto de venta del vendedor y contraseña."""
from __future__ import annotations

from src.aplicacion.casos_uso.cuentas.permisos import exigir
from src.aplicacion.puertos.salida import CifradorContrasenas, LectorMercados, RepositorioUsuarios
from src.dominio.excepciones import MercadoNoEncontrado, SinAdministradores, UsuarioNoEncontrado
from src.dominio.modelo import Permiso, Rol, Usuario
from src.dominio.modelo.usuario import validar_contrasena

# Marca para "no tocar este campo" en actualizar(): None es un valor válido
# para el punto de venta (quitárselo a alguien), así que no sirve de marca.
_SIN_CAMBIO = object()


class AdministrarUsuarios:
    def __init__(self, usuarios: RepositorioUsuarios, cifrador: CifradorContrasenas,
                 mercados: LectorMercados):
        self._usuarios = usuarios
        self._cifrador = cifrador
        self._mercados = mercados

    def listar(self, actor: Usuario) -> list[Usuario]:
        exigir(actor, Permiso.GESTIONAR_USUARIOS)
        return sorted(self._usuarios.listar(), key=lambda u: u.id or 0)

    def actualizar(self, actor: Usuario, id_usuario: int, rol: Rol | None = None,
                   activo: bool | None = None, punto_venta=_SIN_CAMBIO) -> Usuario:
        exigir(actor, Permiso.GESTIONAR_USUARIOS)
        usuario = self._obtener(id_usuario)
        nuevo = usuario
        if rol is not None:
            nuevo = nuevo.con_rol(rol)
        if activo is not None:
            nuevo = nuevo.con_activo(activo)
        if punto_venta is not _SIN_CAMBIO:
            if punto_venta is not None and self._mercados.obtener(punto_venta) is None:
                raise MercadoNoEncontrado(punto_venta)
            nuevo = nuevo.con_punto_venta(punto_venta)
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
