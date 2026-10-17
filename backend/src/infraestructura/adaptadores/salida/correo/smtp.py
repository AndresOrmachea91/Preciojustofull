"""
Envío de correo por SMTP. En Docker apunta a Mailpit (un buzón local que
atrapa todo y lo muestra en http://localhost:8025): ningún correo de prueba
sale a internet. En producción, a un servidor SMTP real con usuario y TLS.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

log = logging.getLogger(__name__)


class CorreoSmtp:
    def __init__(self, host: str, puerto: int, remitente: str, usuario: str = "", clave: str = "",
                 tls: bool = False):
        self._host, self._puerto, self._remitente = host, puerto, remitente
        self._usuario, self._clave, self._tls = usuario, clave, tls

    def enviar(self, para: str, asunto: str, texto: str) -> None:
        mensaje = EmailMessage()
        mensaje["From"], mensaje["To"], mensaje["Subject"] = self._remitente, para, asunto
        mensaje.set_content(texto)
        with smtplib.SMTP(self._host, self._puerto, timeout=10) as smtp:
            if self._tls:
                smtp.starttls()
            if self._usuario:
                smtp.login(self._usuario, self._clave)
            smtp.send_message(mensaje)
        log.info("Correo enviado a %s: %s", para, asunto)


class CorreoEnBitacora:
    """Sin SMTP configurado: el correo se escribe en el log (desarrollo) y se guarda para las pruebas."""

    def __init__(self):
        self.enviados: list[tuple[str, str, str]] = []

    def enviar(self, para: str, asunto: str, texto: str) -> None:
        self.enviados.append((para, asunto, texto))
        log.warning("SMTP no configurado; correo para %s:\n%s", para, texto)
