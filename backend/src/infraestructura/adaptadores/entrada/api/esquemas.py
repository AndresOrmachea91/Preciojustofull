"""
Esquemas de la API: los DTO que viajan por HTTP.

Son distintos de las entidades del dominio a propósito. Si el dominio
cambia, la API no se rompe sola; y si el contrato de la API cambia, el
dominio no se entera.
"""
from __future__ import annotations
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class RangoSalida(BaseModel):
    minimo: float
    maximo: float
    centro: float


class PrecioSalida(BaseModel):
    codigo_producto: str
    codigo_mercado: str
    periodo: str
    rango: RangoSalida
    unidad: str
    confianza: str
    # Los tres son OBLIGATORIOS, sin valor por defecto: un precio sin
    # procedencia no se puede construir, ni por descuido.
    procedencia: Literal["observado", "estimado"]
    observaciones_usadas: int = Field(ge=1)
    fecha_observacion_mas_reciente: date | None
    conflictos: list[str] = Field(default_factory=list)


class PrecioEnMercadoSalida(BaseModel):
    codigo_mercado: str
    nombre_mercado: str
    tipo: str
    zona: str
    precio: PrecioSalida


class ProductoSalida(BaseModel):
    codigo: str
    nombre: str
    categoria: str
    es_perecedero: bool


class MercadoSalida(BaseModel):
    codigo: str
    nombre: str
    tipo: str
    zona: str
    latitud: float | None = None
    longitud: float | None = None
    publica_rango: bool


class ItemCanastaEntrada(BaseModel):
    codigo_producto: str
    cantidad: float = Field(default=1.0, gt=0)


class CanastaEntrada(BaseModel):
    items: list[ItemCanastaEntrada] = Field(min_length=1)
    zona: str | None = None


class CanastaSalida(BaseModel):
    codigo_mercado: str
    nombre_mercado: str
    zona: str
    costo_total: float
    productos_cubiertos: int
    productos_pedidos: int
    cobertura: float
    faltantes: list[str] = Field(default_factory=list)


class ReporteEntrada(BaseModel):
    codigo_producto: str
    codigo_mercado: str
    monto: float = Field(gt=0)
    unidad: str


class ReporteSalida(BaseModel):
    aceptado: bool
    mensaje: str

