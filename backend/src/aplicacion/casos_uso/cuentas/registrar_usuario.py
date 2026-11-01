"""
Alta de cuentas.

El registro público crea un usuario común o, si la persona dice que vende,
un vendedor (decisión 27): el casero se registra solo, elige su mercado y su
puesto, y lo que publique sale marcado como "declarado por el vendedor" (el
motor de fusión lo pesa así y el administrador lo puede retirar). Nadie se
nombra administrador a sí mismo: esas cuentas las crea otro administrador o
la consola del servidor.
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.aplicacion.casos_uso.cuentas.permisos import exigir
from src.aplicacion.puertos.salida import CifradorContrasenas, RepositorioUsuarios
from src.dominio.excepciones import CorreoYaRegistrado
from src.dominio.modelo import Permiso, Rol, Usuario
from src.dominio.modelo.usuario import normalizar_correo, validar_contrasena


class RegistrarUsuario:
    def __init__(self, usuarios: RepositorioUsuarios, cifrador: CifradorContrasenas):
        self._usuarios = usuarios
        self._cifrador = cifrador

    def registrarse(self, correo: str, nombre: str, contrasena: str, quiere_vender: bool = False) -> Usuario:
        return self._crear(correo, nombre, contrasena, Rol.VENDEDOR if quiere_vender else Rol.USUARIO)

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
