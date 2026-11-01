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
    # Procedencia en detalle: voces independientes por fuente, el factor
    # del local si es estimado y por qué el rango es más ancho.
    voces: dict[str, int] = Field(default_factory=dict)
    factor_mercado: float | None = None
    antiguedad_dias: int | None = None
    motivos_rango: list[str] = Field(default_factory=list)


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
    costo_minimo: float = 0.0
    costo_maximo: float = 0.0


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


class PuntoHistorialSalida(BaseModel):
    periodo: str          # "2026-09"
    nivel: Literal["minorista", "mayorista"]
    precio: float
    observaciones: int


class HistorialSalida(BaseModel):
    """El precio de referencia de la ciudad mes a mes, por unidad base del producto."""
    codigo_producto: str
    unidad: str
    puntos: list[PuntoHistorialSalida]


class RecuperarEntrada(BaseModel):
    correo: str = Field(max_length=255)


class RestablecerEntrada(BaseModel):
    token: str = Field(max_length=2000)
    contrasena: str = Field(max_length=128)


class RegistroAuditadoSalida(BaseModel):
    """Una fila de cualquier tabla, con sus 5 campos de auditoría."""
    tabla: str
    clave: str
    descripcion: str
    accion: Literal["creado", "modificado", "eliminado"]
    ultimo_cambio: datetime
    auditoria: AuditoriaSalida


class PermisoSalida(BaseModel):
    codigo: str
    descripcion: str


class RolSalida(BaseModel):
    codigo: str
    nombre: str
    descripcion: str
    permisos: list[PermisoSalida]


class FuenteSalida(BaseModel):
    codigo: str
    nombre: str
    descripcion: str
    confianza_base: str
    deriva_de: str | None
    automatica: bool
    url: str | None


class ReferenciasSalida(BaseModel):
    roles: list[RolSalida]
    fuentes: list[FuenteSalida]


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
    # El casero se registra solo como vendedor (decisión 27). Nunca administrador.
    quiere_vender: bool = False


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

TipoPuntoVentaTexto = Literal["mercado", "distribuidor", "mayorista", "minimarket", "tienda", "supermercado"]
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


# --- campo, confiabilidad y salud (C127, C130, C132) --------------------------

class ImportarCampoEntrada(BaseModel):
    # El texto de la planilla, tal cual (la web lo lee del archivo elegido).
    csv: str = Field(min_length=1, max_length=2_000_000)
    archivo: str = Field(default="planilla", max_length=120)
    solo_revisar: bool = False


class FilaRechazadaSalida(BaseModel):
    fila: int
    motivo: str


class ImportarCampoSalida(BaseModel):
    leidas: int
    validas: int
    guardadas: int
    rechazadas: list[FilaRechazadaSalida]
    solo_revisar: bool


class ResumenProductoSalida(BaseModel):
    codigo_producto: str
    nombre_producto: str
    casos: int
    error_medio: float
    cobertura: float


class CasoEvaluadoSalida(BaseModel):
    codigo_producto: str
    nombre_producto: str
    codigo_mercado: str
    nombre_mercado: str
    periodo: str
    observado: float
    estimado: float
    estimado_minimo: float
    estimado_maximo: float
    sin_factor: float
    error: float
    dentro_del_rango: bool
    voces: dict[str, int]


class EvaluacionSalida(BaseModel):
    casos: int
    error_medio: float | None
    sesgo: float | None
    cobertura: float | None
    error_medio_sin_factor: float | None
    el_factor_ayuda: bool | None
    mercados: int
    productos: int
    por_producto: list[ResumenProductoSalida]
    detalle: list[CasoEvaluadoSalida]
    calculado_en: datetime


class PuntoSaludSalida(BaseModel):
    nombre: str
    estado: Literal["bien", "revisar", "sin_datos"]
    detalle: str


class FuenteSaludSalida(BaseModel):
    fuente: str
    observaciones: int
    ultima_captura: datetime | None


class RecoleccionSalida(BaseModel):
    fuente: str
    ocurrido_en: datetime
    exito: bool
    detalle: str | None
    hechos_nuevos_24h: int


class RespaldoSalida(BaseModel):
    fecha: datetime | None
    archivo: str | None
    tamano_bytes: int | None
    verificado: bool
    filas_observaciones: int | None
    detalle: str | None


class SaludSalida(BaseModel):
    estado_general: Literal["bien", "revisar", "sin_datos"]
    puntos: list[PuntoSaludSalida]
    fuentes: list[FuenteSaludSalida]
    recolecciones: list[RecoleccionSalida]
    respaldo: RespaldoSalida | None
    cobertura_observada: float | None
    ventana_dias: int


# --- puestos, ofertas y ficha del mercado (C133, C134) ---------------------------

class PuestoEntrada(BaseModel):
    numero: str = Field(min_length=1, max_length=16)
    nombre: str = Field(default="", max_length=80)
    rubros: list[str] = Field(default_factory=list, max_length=8)
    referencia: str = Field(default="", max_length=160)
    # El mercado lo elige el casero (decisión 26). Sin él, el que ya tenía.
    codigo_mercado: str | None = Field(default=None, max_length=64)


class DistribuidoraEntrada(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    zona: str = Field(default="", max_length=128)
    macrodistrito: str = Field(default="", max_length=64)
    latitud: float
    longitud: float
    rubros: list[str] = Field(default_factory=list, max_length=8)
    referencia: str = Field(default="", max_length=160)


class FotoEntrada(BaseModel):
    """La foto como data URL ("data:image/jpeg;base64,..."), ya achicada en el celular."""

    imagen: str = Field(min_length=20, max_length=3_500_000)


DisponibilidadTexto = Literal["hay", "poco", "agotado"]


class ArticuloEntrada(BaseModel):
    codigo_producto: str = Field(min_length=1, max_length=64)
    monto: float = Field(gt=0)
    presentacion: str = Field(min_length=1, max_length=16)
    disponibilidad: DisponibilidadTexto = "hay"


class ArticuloSalida(BaseModel):
    codigo_producto: str
    nombre_producto: str
    categoria: str
    monto: float
    presentacion: str
    precio_por_unidad_base: float
    unidad_base: str
    disponibilidad: DisponibilidadTexto
    actualizado_en: datetime | None


class PuestoSalida(BaseModel):
    id: int | None
    codigo_mercado: str
    numero: str
    nombre: str
    rubros: list[str]
    referencia: str
    # False si el número solo aparece en mediciones de campo.
    registrado: bool = True
    # Dirección para pedir la foto (/api/v1/fotos/...), o None si no tiene.
    foto: str | None = None
    # True: es el local de una distribuidora, no un puesto con número.
    es_local: bool = False


class PuestoConInventarioSalida(BaseModel):
    puesto: PuestoSalida
    articulos: list[ArticuloSalida]
    total: int


class PuestosDelMercadoSalida(BaseModel):
    mercado: MercadoSalida
    puestos: list[PuestoConInventarioSalida]


class OfertaEntrada(BaseModel):
    codigo_producto: str
    monto: float = Field(gt=0)
    presentacion: str
    horas: Literal[24, 48, 72] = 48
    nota: str = Field(default="", max_length=80)


class OfertaSalida(BaseModel):
    """Una oferta vigente con su comparación contra el precio del sistema."""
    id: int
    codigo_producto: str
    nombre_producto: str
    unidad_base: str
    codigo_mercado: str
    nombre_mercado: str
    numero_puesto: str | None
    nombre_puesto: str | None
    monto: float
    presentacion: str
    precio_por_unidad_base: float
    desde: datetime
    hasta: datetime
    nota: str
    # Contra qué se mide el ahorro: el precio del sistema en ese mercado,
    # sin la voz del casero, y si es observado o estimado.
    precio_sistema: float
    procedencia_sistema: Literal["observado", "estimado"]
    ahorro_por_unidad: float
    ahorro_relativo: float
    confirmaron: int
    desmintieron: int


class MiOfertaSalida(BaseModel):
    id: int
    codigo_producto: str
    nombre_producto: str
    monto: float
    presentacion: str
    precio_por_unidad_base: float
    desde: datetime
    hasta: datetime
    nota: str
    estado: Literal["activa", "vencida", "en_revision", "retirada"]
    confirmaron: int
    desmintieron: int


class OfertaEnRevisionSalida(BaseModel):
    id: int
    nombre_producto: str
    nombre_mercado: str
    numero_puesto: str | None
    monto: float
    presentacion: str
    hasta: datetime
    nota: str
    confirmaron: int
    desmintieron: int


class ConfirmacionEntrada(BaseModel):
    la_vio_asi: bool


class ConfirmacionSalida(BaseModel):
    confirmaron: int
    desmintieron: int
    pausada: bool


class PrecioDeProductoSalida(BaseModel):
    codigo_producto: str
    nombre_producto: str
    categoria: str
    precio: PrecioSalida
    ciudad: float | None
    diferencia: float | None


class PrecioDelPuestoSalida(BaseModel):
    codigo_producto: str
    nombre_producto: str
    monto: float
    unidad: str
    precio_por_unidad_base: float
    unidad_base: str
    fecha: date | None
    fuente: Literal["vendedor", "campo"]


class PuestoEnFichaSalida(BaseModel):
    puesto: PuestoSalida
    precios: list[PrecioDelPuestoSalida]
    ofertas: list[OfertaSalida]


class FichaMercadoSalida(BaseModel):
    mercado: MercadoSalida
    padre: MercadoSalida | None
    sectores: list[MercadoSalida]
    # Cuánto se aparta este lugar de la ciudad según el campo; 1 = sin medir.
    factor_mercado: float
    precios: list[PrecioDeProductoSalida]
    puestos: list[PuestoEnFichaSalida]
    ofertas: list[OfertaSalida]
    observados: int
    estimados: int
    productos_sin_precio: int
    dato_mas_reciente: date | None


class EntradaDirectorioSalida(BaseModel):
    mercado: MercadoSalida
    puestos: int
    ofertas: int
    sectores: int


# --- qué medir primero y cuánto varía cada producto (A4230, A5020) ----------------

class VariacionProductoSalida(BaseModel):
    producto: ProductoSalida
    cambio_mensual: float
    mayor_subida: float
    mayor_bajada: float
    meses: int
    nivel: str


class PrioridadProductoSalida(BaseModel):
    producto: ProductoSalida
    puntaje: float
    lugares_sin_dato: int
    lugares_con_dato_viejo: int
    lugares_al_dia: int
    cambio_mensual: float | None
    ancho_relativo: float | None
    motivos: list[str]


class LugarPorVisitarSalida(BaseModel):
    mercado: MercadoSalida
    productos_al_dia: int
    productos_total: int


class PlanVerificacionSalida(BaseModel):
    fecha: date
    productos: list[PrioridadProductoSalida]
    lugares: list[LugarPorVisitarSalida]
    variaciones: list[VariacionProductoSalida]
