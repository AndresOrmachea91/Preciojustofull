"""Configuración de la aplicación. Vive en el borde, no en el dominio."""
import logging
import secrets
from pathlib import Path

from pydantic_settings import BaseSettings

log = logging.getLogger(__name__)

# backend/.env, sin importar desde qué carpeta se arranque el proceso. Con la
# ruta relativa ".env" el archivo solo se encontraba si el cwd era backend/,
# y en una demo nadie quiere descubrir eso a las apuradas.
ARCHIVO_ENV = Path(__file__).resolve().parents[1] / ".env"


class Configuracion(BaseSettings):
    app_nombre: str = "PrecioJusto"
    app_entorno: str = "desarrollo"
    base_datos_url: str = ""
    cors_origenes: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Secreto con el que se firman los tokens de sesión. Vacío en
    # desarrollo: se genera uno por proceso y las sesiones se pierden al
    # reiniciar. En producción es obligatorio.
    jwt_secreto: str = ""
    sesion_horas: float = 8.0

    # Primer administrador. Si están las dos y todavía no hay ningún
    # administrador, se crea al arrancar. Después se pueden borrar.
    admin_inicial_correo: str = ""
    admin_inicial_contrasena: str = ""

    # Correo saliente (recuperar contraseña). Sin SMTP_HOST, el correo se
    # escribe en el log. En Docker va a Mailpit; en producción, a un SMTP real.
    smtp_host: str = ""
    smtp_puerto: int = 25
    smtp_remitente: str = "PrecioJusto <no-responder@preciojusto.bo>"
    smtp_usuario: str = ""
    smtp_clave: str = ""
    smtp_tls: bool = False
    # Dónde abre la persona el enlace del correo.
    url_publica: str = "http://localhost:8088"
    # Carpeta de respaldos (montada solo lectura en el contenedor de la
    # app): de ahí el panel de salud lee estado.json, que deja el respaldo.
    respaldos_dir: str = "/respaldos"
    # Dónde se guardan las fotos de los puestos (C137). Vacío: backend/datos/fotos.
    # En Docker es un volumen propio montado en /fotos.
    fotos_dir: str = ""
    # Límite de intentos en ingresar, registro y recuperar (C131).
    limite_intentos_activo: bool = True

    class Config:
        env_file = str(ARCHIVO_ENV)
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def origenes(self) -> list[str]:
        return [o.strip() for o in self.cors_origenes.split(",") if o.strip()]

    @property
    def es_produccion(self) -> bool:
        return self.app_entorno.lower() in ("produccion", "producción", "production")

    def secreto_tokens(self) -> str:
        if self.jwt_secreto:
            return self.jwt_secreto
        if self.es_produccion:
            raise RuntimeError("Falta JWT_SECRETO: en producción las sesiones no pueden firmarse con un secreto improvisado")
        log.warning("Sin JWT_SECRETO: se usa uno aleatorio; las sesiones se pierden al reiniciar")
        return secrets.token_urlsafe(48)


config = Configuracion()
