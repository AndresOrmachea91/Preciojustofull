"""
Esquema de la base de datos.

Vive en los ADAPTADORES, no en el dominio. Las entidades del dominio no
saben que existe una base de datos: estas tablas son un detalle de cómo se
guardan, y podrían cambiar sin tocar el núcleo.

El esquema se mantiene portable a propósito (sin tipos propios de
PostgreSQL) para que las pruebas de contrato puedan correrlo sobre SQLite
en la integración continua, sin levantar un servidor.
"""
from __future__ import annotations

from sqlalchemy import (
    Column, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, Index,
    MetaData, Table,
)
from sqlalchemy.orm import declarative_base

metadata = MetaData()
Base = declarative_base(metadata=metadata)


class ProductoTabla(Base):
    __tablename__ = "producto"

    codigo = Column(String(64), primary_key=True)
    nombre = Column(String(255), nullable=False)
    categoria = Column(String(32), nullable=False, default="otro")
    dias_conservacion = Column(Integer, nullable=False, default=30)
    zona_origen = Column(String(128), nullable=True)
    unidad_base = Column(String(8), nullable=False, default="kg")


class MercadoTabla(Base):
    __tablename__ = "mercado"

    codigo = Column(String(64), primary_key=True)
    nombre = Column(String(255), nullable=False)
    tipo = Column(String(32), nullable=False, default="mercado")
    zona = Column(String(128), nullable=False, default="")
    macrodistrito = Column(String(64), nullable=False, default="")
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    # Cuánto se aparta este punto de venta de la referencia de la ciudad.
    # Se aprende del levantamiento de campo.
    factor_mercado = Column(Float, nullable=False, default=1.0)
    # Autorreferencia: el sector de un mercado apunta al mercado. Nullable
    # porque la mayoría de los puntos de venta no tiene padre.
    codigo_padre = Column(String(64), ForeignKey("mercado.codigo"), nullable=True)


class ObservacionTabla(Base):
    """
    Una observación es INMUTABLE: se guarda lo que dijo la fuente, con su
    unidad original, y nunca se corrige. El precio consolidado se deriva
    de acá y se puede recalcular con otra configuración del motor de
    fusión — que es lo que permite demostrar que fusionar aporta algo.
    """

    __tablename__ = "observacion_precio"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fuente = Column(String(32), nullable=False)
    nivel = Column(String(16), nullable=False)
    codigo_producto = Column(String(64), nullable=False)
    codigo_mercado = Column(String(64), nullable=False)

    anio = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=True)
    dia = Column(Integer, nullable=True)

    # El par original, siempre. precio_canonico es derivado y puede ser
    # NULL: NULL significa "no convertible", no "no calculado".
    precio_monto = Column(Float, nullable=False)
    unidad_texto = Column(String(64), nullable=False)
    cantidad = Column(Float, nullable=False, default=1.0)
    precio_canonico = Column(Float, nullable=True)
    unidad_canonica = Column(String(8), nullable=True)

    variedad = Column(String(64), nullable=False, default="desconocida")
    # Cuándo se observó según el DATO. NULL = no se sabe; nunca se rellena
    # con capturada_en.
    fecha_observacion = Column(Date, nullable=True)
    tipo_precio = Column(String(16), nullable=False, default="desconocido")
    evidencia = Column(String(512), nullable=True)

    reputacion_informante = Column(Float, nullable=False, default=1.0)
    # "punto_venta" si se midió en un local; "ciudad" si la fuente publica
    # un valor para toda la ciudad (SIIP). Lo segundo estima, no mide.
    ambito = Column(String(16), nullable=False, default="punto_venta")
    capturada_en = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        # Impide duplicar la misma afirmación de la misma fuente. Es lo que
        # hace que el recolector se pueda correr tres veces al día sin
        # ensuciar la serie.
        UniqueConstraint(
            "fuente", "codigo_producto", "codigo_mercado", "anio", "mes", "dia",
            name="uq_observacion_unica",
        ),
        Index("ix_obs_consulta", "codigo_producto", "codigo_mercado", "anio", "mes"),
        Index("ix_obs_nivel", "nivel", "anio", "mes"),
    )


class IntentoFuenteTabla(Base):
    """
    Registro de cada llamada a cada fuente y su desenlace.

    De esta tabla sale la métrica de disponibilidad efectiva del dato, que
    es uno de los resultados de la tesis: disponibilidad de la fuente
    original frente a disponibilidad del sistema, y la diferencia entre
    ambas.
    """

    __tablename__ = "intento_fuente"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fuente = Column(String(64), nullable=False)
    url = Column(String(512), nullable=True)
    exito = Column(Integer, nullable=False)
    duracion_ms = Column(Integer, nullable=True)
    detalle = Column(String(512), nullable=True)
    ocurrido_en = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_intento_fuente", "fuente", "ocurrido_en"),)
