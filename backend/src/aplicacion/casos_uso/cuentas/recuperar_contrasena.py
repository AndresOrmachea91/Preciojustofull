"""
Recuperar la contraseña por un enlace al correo (decisión 15 del 8 de octubre).

1. La persona pide el enlace con su correo. La respuesta es siempre la
   misma, exista o no la cuenta: decir "ese correo no está" le enseña a un
   atacante qué correos hay.
2. El enlace vence en minutos y sirve UNA vez: lleva una huella de la
   contraseña actual, así que deja de valer apenas se cambia.
"""
from __future__ import annotations

import logging

from src.aplicacion.puertos.salida import (
    CifradorContrasenas, EnlacesRecuperacion, EnviadorCorreo, RepositorioUsuarios,
)
from src.dominio.excepciones import CorreoInvalido, EnlaceInvalido
from src.dominio.modelo import Usuario
from src.dominio.modelo.usuario import normalizar_correo, validar_contrasena

log = logging.getLogger(__name__)

ASUNTO = "PrecioJusto: elija una contraseña nueva"


class RecuperarContrasena:
    def __init__(self, usuarios: RepositorioUsuarios, enlaces: EnlacesRecuperacion,
                 correo: EnviadorCorreo, cifrador: CifradorContrasenas, url_publica: str,
                 minutos_validez: int = 30):
        self._usuarios = usuarios
        self._enlaces = enlaces
        self._correo = correo
        self._cifrador = cifrador
        self._url = url_publica.rstrip("/")
        self._minutos = minutos_validez

    def solicitar(self, correo: str) -> None:
        """No devuelve nada a propósito: la respuesta no revela si la cuenta existe."""
        try:
            usuario = self._usuarios.obtener_por_correo(normalizar_correo(correo))
        except CorreoInvalido:
            return
        if usuario is None or not usuario.activo:
            return
        enlace = f"{self._url}/#/restablecer?token={self._enlaces.emitir(usuario)}"
        try:
            self._correo.enviar(usuario.correo, ASUNTO, _texto(usuario, enlace, self._minutos))
        except Exception:  # noqa: BLE001 - un correo caído no debe delatar que la cuenta existe
            log.exception("No se pudo enviar el correo de recuperación")

    def restablecer(self, enlace: str, contrasena: str) -> Usuario:
        validar_contrasena(contrasena)
        id_usuario = self._enlaces.id_de(enlace)
        usuario = self._usuarios.obtener(id_usuario) if id_usuario is not None else None
        if usuario is None or not usuario.activo or not self._enlaces.vigente_para(enlace, usuario):
            raise EnlaceInvalido()
        return self._usuarios.guardar(usuario.con_hash(self._cifrador.cifrar(contrasena)))


def _texto(usuario: Usuario, enlace: str, minutos: int) -> str:
    return (
        f"Hola, {usuario.nombre}:\n\n"
        f"Alguien pidió cambiar la contraseña de su cuenta de PrecioJusto. Para elegir una nueva, abra:\n\n"
        f"{enlace}\n\n"
        f"El enlace vale {minutos} minutos y sirve una sola vez. Si no lo pidió usted, ignore este correo: "
        f"su contraseña no cambia.\n"
    )
