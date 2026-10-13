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


class PresentacionSalida(BaseModel):
    codigo: str
    nombre: str
    # Cuántas unidades base trae: un quintal = 46 (kg).
    factor: float


class ProductoSalida(BaseModel):
    codigo: str
    nombre: str
    categoria: str
    es_perecedero: bool
    unidad_base: str = "kg"
    dias_conservacion: int = 30
    presentaciones: list[PresentacionSalida] = Field(default_factory=list)


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
    productos_estimados: int = 0
    nivel_precio: Literal["mayorista", "minorista"] = "minorista"


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


class AuditoriaSalida(BaseModel):
    """Los 5 campos de auditoría tal como los guarda la base."""
    creado_en: datetime
    creado_por: str
    modificado_en: datetime | None = None
    modificado_por: str | None = None
    eliminado: bool


class UsuarioAuditadoSalida(UsuarioSalida):
    """
    El mismo usuario, con su auditoría: el DTO "sobrecargado" que ve solo
    el administrador. Quien consulta su propia cuenta (/auth/yo) recibe
    UsuarioSalida, sin estos campos.
    """
    auditoria: AuditoriaSalida | None = None


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


# --- catálogo (administrador) -----------------------------------------------

TipoPuntoVentaTexto = Literal["mercado", "minimarket", "tienda", "supermercado", "mayorista"]
CategoriaTexto = Literal["hortaliza", "tuberculo", "fruta", "carne", "pescado", "lacteo", "abarrote", "otro"]
UnidadBaseTexto = Literal["kg", "l", "u", "atado"]
PresentacionTexto = Literal["kilo", "libra", "arroba", "quintal", "litro", "unidad", "docena", "maple", "atado"]


class PuntoVentaEntrada(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    tipo: TipoPuntoVentaTexto
    zona: str = Field(default="", max_length=128)
    macrodistrito: str = Field(default="", max_length=64)
    latitud: float | None = None
    longitud: float | None = None
    # Si es un sector de un mercado, el código del mercado.
    codigo_padre: str | None = None


class NuevoPuntoVentaEntrada(PuntoVentaEntrada):
    # Opcional: si no viene, se arma desde el nombre ("Mercado Lanza" -> "mercado_lanza").
    codigo: str | None = Field(default=None, pattern=r"^[a-z0-9_]{2,64}$")


class ProductoEntrada(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    categoria: CategoriaTexto = "otro"
    unidad_base: UnidadBaseTexto = "kg"
    # Vacío = todas las presentaciones compatibles con la unidad base.
    presentaciones: list[PresentacionTexto] = Field(default_factory=list)
    dias_conservacion: int = Field(default=30, ge=1, le=3650)


class NuevoProductoEntrada(ProductoEntrada):
    codigo: str | None = Field(default=None, pattern=r"^[a-z0-9_]{2,64}$")


# --- vendedor -------------------------------------------------------------------

class PublicarPrecioEntrada(BaseModel):
    codigo_producto: str
    monto: float = Field(gt=0, le=100000)
    presentacion: PresentacionTexto


class PrecioPublicadoSalida(BaseModel):
    codigo_producto: str
    nombre_producto: str
    monto: float
    presentacion: str
    # El mismo precio por kilo (o litro, o unidad): con eso se compara.
    precio_por_unidad_base: float
    unidad_base: str
    publicado_en: datetime


# --- usuario: listas de compras -------------------------------------------------

class ItemListaEntrada(BaseModel):
    codigo_producto: str
    cantidad: float = Field(gt=0, le=10000)
    presentacion: PresentacionTexto


class ListaEntrada(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    items: list[ItemListaEntrada] = Field(default_factory=list, max_length=60)


class ItemListaSalida(BaseModel):
    codigo_producto: str
    cantidad: float
    presentacion: str


class ListaSalida(BaseModel):
    id: int
    nombre: str
    items: list[ItemListaSalida]
    creado_en: datetime | None = None
