"""Conexión a la base de datos y creación del esquema."""
from __future__ import annotations

import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.infraestructura.adaptadores.salida.persistencia.tablas import (
    INDICE_CLAVE_NATURAL, NOMBRE_INDICE_CLAVE_NATURAL, metadata,
)

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


# Columnas agregadas después de que la base ya existía. create_all crea
# tablas nuevas pero no toca las existentes, así que se completan a mano.
# Es una migración mínima; si el esquema sigue creciendo, toca Alembic.
_COLUMNAS_AGREGADAS = {
    "producto": {
        "unidad_base": "VARCHAR(8) NOT NULL DEFAULT 'kg'",
    },
    "mercado": {
        "macrodistrito": "VARCHAR(64) NOT NULL DEFAULT ''",
        "codigo_padre": "VARCHAR(64) NULL REFERENCES mercado(codigo)",
    },
    "observacion_precio": {
        "ambito": "VARCHAR(16) NOT NULL DEFAULT 'punto_venta'",
        "cantidad": "FLOAT NOT NULL DEFAULT 1.0",
        # Marcadores explícitos para lo histórico: no se sabe, y se dice.
        "variedad": "VARCHAR(64) NOT NULL DEFAULT 'desconocida'",
        "fecha_observacion": "DATE NULL",
        "tipo_precio": "VARCHAR(16) NOT NULL DEFAULT 'desconocido'",
        "evidencia": "VARCHAR(512) NULL",
        "ultima_captura_en": "TIMESTAMP NULL",
        "revisa_a": "INTEGER NULL REFERENCES observacion_precio(id)",
    },
}

# Rellenos que se pueden hacer con honestidad sobre filas históricas. El
# ámbito se deduce de la fuente (el SIIP siempre publica por ciudad). La
# fecha de observación se recupera SOLO donde el propio dato la trae (el
# periodo diario del SIIP tiene día); donde no, queda NULL. Nunca se
# rellena con capturada_en.
_AMBITO_POR_FUENTE = (
    "UPDATE observacion_precio SET ambito = 'ciudad' "
    "WHERE fuente IN ('siip_diario', 'siip_ipc') AND ambito <> 'ciudad'"
)
_RELLENOS_HISTORICOS = {
    "sqlite": [
        _AMBITO_POR_FUENTE,
        "UPDATE observacion_precio SET fecha_observacion = "
        "date(printf('%04d-%02d-%02d', anio, mes, dia)) "
        "WHERE fecha_observacion IS NULL AND mes IS NOT NULL AND dia IS NOT NULL",
    ],
    "postgresql": [
        _AMBITO_POR_FUENTE,
        "UPDATE observacion_precio SET fecha_observacion = make_date(anio, mes, dia) "
        "WHERE fecha_observacion IS NULL AND mes IS NOT NULL AND dia IS NOT NULL",
    ],
}


def crear_esquema(motor: Engine) -> None:
    """Crea las tablas y columnas que falten. Es idempotente."""
    metadata.create_all(motor)
    inspector = inspect(motor)
    with motor.begin() as conexion:
        for tabla, columnas in _COLUMNAS_AGREGADAS.items():
            existentes = {c["name"] for c in inspector.get_columns(tabla)}
            for nombre, definicion in columnas.items():
                if nombre not in existentes:
                    conexion.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {definicion}"))
                    log.info("Columna %s.%s agregada", tabla, nombre)
        for sentencia in _RELLENOS_HISTORICOS.get(motor.dialect.name, []):
            rellenadas = conexion.execute(text(sentencia)).rowcount
            if rellenadas:
                log.info("Filas históricas completadas: %s", rellenadas)
    log.info("Esquema verificado")


def asegurar_indice_clave_natural(motor: Engine) -> None:
    """
    Crea el índice único del hecho observado. Idempotente. Va aparte de
    crear_esquema porque sobre una tabla con duplicados históricos falla:
    primero se limpia (script de reparación), después se crea.
    """
    with motor.begin() as conexion:
        conexion.execute(text(INDICE_CLAVE_NATURAL))
    log.info("Índice %s verificado", NOMBRE_INDICE_CLAVE_NATURAL)


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
