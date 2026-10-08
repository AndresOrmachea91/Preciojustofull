"""
Esquemas de la API: los DTO que viajan por HTTP.

Son distintos de las entidades del dominio a propósito. Si el dominio
cambia, la API no se rompe sola; y si el contrato de la API cambia, el
dominio no se entera.
"""
from __future__ import annotations
from datetime import date, datetime
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
    # mayorista o minorista. Obligatorio: dos números de niveles distintos
    # no se pueden mostrar como si compitieran.
    nivel_precio: Literal["mayorista", "minorista"]
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
    macrodistrito: str
    # Código del mercado que lo contiene, si es un sector de otro.
    codigo_padre: str | None
    nivel_precio: Literal["mayorista", "minorista"]
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



class ReporteRevisionSalida(BaseModel):
    id: int
    codigo_producto: str
    codigo_mercado: str
    monto: float
    unidad: str
    id_autor: int
    creado_en: datetime
    estado: Literal["pendiente", "aprobado", "rechazado"]
    id_revisor: int | None = None
    revisado_en: datetime | None = None
    motivo_rechazo: str | None = None


class RechazoEntrada(BaseModel):
    motivo: str = Field(min_length=3, max_length=500)


# --- cuentas y sesiones ----------------------------------------------------

RolTexto = Literal["usuario", "vendedor", "administrador"]


class UsuarioSalida(BaseModel):
    # Nunca lleva el hash de la contraseña: este DTO es justamente el filtro.
    id: int
    correo: str
    nombre: str
    rol: RolTexto
    activo: bool
    creado_en: datetime
    permisos: list[str]
    # Solo para vendedores: su puesto o tienda.
    codigo_punto_venta: str | None = None


class RegistroEntrada(BaseModel):
    correo: str = Field(max_length=255)
    nombre: str = Field(default="", max_length=255)
    contrasena: str = Field(min_length=1, max_length=128)


class CrearUsuarioEntrada(RegistroEntrada):
    rol: RolTexto = "usuario"


class IngresoEntrada(BaseModel):
    correo: str = Field(max_length=255)
    contrasena: str = Field(max_length=128)


class SesionSalida(BaseModel):
    token: str
    tipo: Literal["bearer"] = "bearer"
    usuario: UsuarioSalida


class ActualizarUsuarioEntrada(BaseModel):
    rol: RolTexto | None = None
    activo: bool | None = None
    # Mandarlo en null le quita el puesto; no mandarlo lo deja como está.
    codigo_punto_venta: str | None = None


class ContrasenaEntrada(BaseModel):
    contrasena: str = Field(min_length=1, max_length=128)
