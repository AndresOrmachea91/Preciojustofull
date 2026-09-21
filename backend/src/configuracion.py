"""Configuración de la aplicación. Vive en el borde, no en el dominio."""
from pathlib import Path

from pydantic_settings import BaseSettings

# backend/.env, sin importar desde qué carpeta se arranque el proceso. Con la
# ruta relativa ".env" el archivo solo se encontraba si el cwd era backend/,
# y en una demo nadie quiere descubrir eso a las apuradas.
ARCHIVO_ENV = Path(__file__).resolve().parents[1] / ".env"


class Configuracion(BaseSettings):
    app_nombre: str = "PrecioJusto"
    app_entorno: str = "desarrollo"
    base_datos_url: str = ""
    cors_origenes: str = "http://localhost:5173,http://127.0.0.1:5173"

    class Config:
        env_file = str(ARCHIVO_ENV)
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def origenes(self) -> list[str]:
        return [o.strip() for o in self.cors_origenes.split(",") if o.strip()]


config = Configuracion()
