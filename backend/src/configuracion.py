"""Configuración de la aplicación. Vive en el borde, no en el dominio."""
from pydantic_settings import BaseSettings


class Configuracion(BaseSettings):
    app_nombre: str = "PrecioJusto"
    app_entorno: str = "desarrollo"
    base_datos_url: str = ""
    cors_origenes: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def origenes(self) -> list[str]:
        return [o.strip() for o in self.cors_origenes.split(",") if o.strip()]


config = Configuracion()

