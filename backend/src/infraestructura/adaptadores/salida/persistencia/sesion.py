"""Conexión a la base de datos y creación del esquema."""
from __future__ import annotations

import logging
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.infraestructura.adaptadores.salida.persistencia.tablas import metadata

log = logging.getLogger(__name__)


def normalizar_url(url: str) -> str:
    """
    Los proveedores alojados suelen entregar la cadena con el prefijo
    'postgres://', que SQLAlchemy ya no acepta. Se traduce en silencio para
    que se pueda pegar la cadena tal como la da Neon o Supabase.
    """
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def crear_motor(url: str, eco: bool = False) -> Engine:
    url = normalizar_url(url)
    opciones: dict = {"echo": eco, "future": True}

    if url.startswith("sqlite"):
        opciones["connect_args"] = {"check_same_thread": False}
    else:
        # Las bases gratuitas suelen dormir la conexión: pre_ping evita
        # que la primera consulta del día falle por una conexión muerta.
        opciones.update(pool_pre_ping=True, pool_size=5, max_overflow=5,
                        pool_recycle=300)
    return create_engine(url, **opciones)


def crear_esquema(motor: Engine) -> None:
    """Crea las tablas que falten. Es idempotente."""
    metadata.create_all(motor)
    log.info("Esquema verificado")


def fabrica_sesiones(motor: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=motor, expire_on_commit=False, future=True)


@contextmanager
def sesion_de(fabrica: sessionmaker[Session]):
    """Abre una sesión, confirma si todo salió bien, revierte si no."""
    s = fabrica()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
