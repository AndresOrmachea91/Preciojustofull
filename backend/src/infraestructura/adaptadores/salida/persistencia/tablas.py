"""
Esquema de la base de datos.

TODAS las tablas heredan de Auditable (auditable.py): creado_en, creado_por,
modificado_en, modificado_por y eliminado (borrado lógico).

Vive en los ADAPTADORES, no en el dominio. Las entidades del dominio no
saben que existe una base de datos: estas tablas son un detalle de cómo se
guardan, y podrían cambiar sin tocar el núcleo.

El esquema se mantiene portable a propósito (sin tipos propios de
PostgreSQL) para que las pruebas de contrato puedan correrlo sobre SQLite
en la integración continua, sin levantar un servidor.
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Index, MetaData, Table,
)
from sqlalchemy.orm import declarative_base, relationship

from src.infraestructura.adaptadores.salida.persistencia.auditable import Auditable

metadata = MetaData()
Base = declarative_base(metadata=metadata)


# --- Catálogos de referencia ------------------------------------------------
# Reflejan en la base los catálogos del dominio (Rol, Permiso, la matriz de
# permisos y Fuente) para que se puedan consultar y para que las demás
# tablas los referencien con claves foráneas. La regla sigue en el dominio:
# referencias.py los sincroniza al arrancar, así que editarlos a mano no
# cambia lo que el sistema permite.

class RolTabla(Base, Auditable):
    __tablename__ = "rol"

    codigo = Column(String(16), primary_key=True)
    nombre = Column(String(64), nullable=False)
    descripcion = Column(String(255), nullable=False)


class PermisoTabla(Base, Auditable):
    __tablename__ = "permiso"

    codigo = Column(String(32), primary_key=True)
    descripcion = Column(String(255), nullable=False)


class RolPermisoTabla(Base, Auditable):
    """Qué puede hacer cada rol: la matriz PERMISOS_POR_ROL, una fila por par."""

    __tablename__ = "rol_permiso"

    codigo_rol = Column(String(16), ForeignKey("rol.codigo"), primary_key=True)
    codigo_permiso = Column(String(32), ForeignKey("permiso.codigo"), primary_key=True)


class FuenteTabla(Base, Auditable):
    """De dónde sale un precio: SIIP IPC, SIIP diario, vendedor, ciudadano, campo..."""

    __tablename__ = "fuente"

    codigo = Column(String(32), primary_key=True)
    nombre = Column(String(128), nullable=False)
    descripcion = Column(String(512), nullable=False)
    confianza_base = Column(String(16), nullable=False)
    # Si copia a otra fuente (un diario que reproduce el boletín del SIIP).
    deriva_de = Column(String(32), ForeignKey("fuente.codigo"), nullable=True)
    automatica = Column(Boolean, nullable=False, default=False)
    url = Column(String(255), nullable=True)


class ProductoTabla(Base, Auditable):
    __tablename__ = "producto"

    codigo = Column(String(64), primary_key=True)
    nombre = Column(String(255), nullable=False)
    categoria = Column(String(32), nullable=False, default="otro")
    dias_conservacion = Column(Integer, nullable=False, default=30)
    zona_origen = Column(String(128), nullable=True)
    unidad_base = Column(String(8), nullable=False, default="kg")
    # "kilo,libra,arroba,quintal". NULL = todas las compatibles con la unidad base.
    presentaciones = Column(String(128), nullable=True)


class MercadoTabla(Base, Auditable):
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


class ObservacionTabla(Base, Auditable):
    """
    Una observación es INMUTABLE: se guarda lo que dijo la fuente, con su
    unidad original, y nunca se corrige. El precio consolidado se deriva
    de acá y se puede recalcular con otra configuración del motor de
    fusión — que es lo que permite demostrar que fusionar aporta algo.
    """

    __tablename__ = "observacion_precio"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fuente = Column(String(32), ForeignKey("fuente.codigo"), nullable=False)
    nivel = Column(String(16), nullable=False)
    codigo_producto = Column(String(64), nullable=False)
    # Uno de los dos: punto de venta (ámbito punto_venta) o ciudad (ámbito
    # ciudad). La ciudad no es un mercado y no comparte columna.
    codigo_mercado = Column(String(64), nullable=True)
    ciudad = Column(String(64), nullable=True)

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
    # Quién lo afirmó ("usuario:12"); NULL si no es una persona conocida.
    # El motor junta por acá: una voz por informante.
    informante = Column(String(64), nullable=True, index=True)
    # Número del puesto dentro del mercado ("14"), si se sabe.
    puesto = Column(String(16), nullable=True)
    # "punto_venta" si se midió en un local; "ciudad" si la fuente publica
    # un valor para toda la ciudad (SIIP). Lo segundo estima, no mide.
    ambito = Column(String(16), nullable=False, default="punto_venta")
    # Cuándo lo supimos por PRIMERA vez. No se pisa al volver a verlo.
    capturada_en = Column(DateTime(timezone=True), nullable=False)
    # Cuándo lo volvimos a ver por última vez. Es un campo aparte a
    # propósito: registrar que se volvió a ver no es pisar cuándo se supo.
    ultima_captura_en = Column(DateTime(timezone=True), nullable=True)
    # Si la fuente volvió a publicar el mismo hecho con OTRO valor, la fila
    # nueva apunta a la anterior. No es un duplicado: es una revisión, y se
    # conservan las dos con su captura.
    revisa_a = Column(Integer, ForeignKey("observacion_precio.id"), nullable=True)

    __table_args__ = (
        # La unicidad del HECHO observado la da el índice de expresión
        # INDICE_CLAVE_NATURAL (abajo), que se crea aparte: una restricción
        # de columnas con mes/dia nulos no sirve, porque en PostgreSQL dos
        # NULL nunca son iguales y las filas mensuales pasaban siempre.
        Index("ix_obs_consulta", "codigo_producto", "codigo_mercado", "anio", "mes"),
        Index("ix_obs_nivel", "nivel", "anio", "mes"),
    )


# Columnas de la clave natural de un hecho observado, en el orden de
# Observacion.clave_natural. El índice lleva además precio_monto: el mismo
# hecho con otro valor es una revisión y tiene que poder convivir.
CLAVE_NATURAL = (
    "fuente", "nivel", "codigo_producto", "ambito", "codigo_mercado", "ciudad",
    "anio", "mes", "dia", "unidad_texto", "cantidad", "informante", "puesto",
)
# v2: con informante y puesto (C133). El índice anterior se reemplaza al
# arrancar (sesion.py): como la clave nueva es más fina, no puede chocar.
NOMBRE_INDICE_CLAVE_NATURAL = "uq_hecho_observado_v2"
NOMBRE_INDICE_CLAVE_NATURAL_ANTERIOR = "uq_hecho_observado"
# Índice de expresión, portable entre SQLite y PostgreSQL: coalesce vuelve
# comparables los NULL de mes y dia. Se crea con asegurar_indice_clave_natural,
# nunca desde create_all, porque sobre una tabla con duplicados falla y
# primero hay que limpiar.
INDICE_CLAVE_NATURAL = (
    f"CREATE UNIQUE INDEX IF NOT EXISTS {NOMBRE_INDICE_CLAVE_NATURAL} ON observacion_precio "
    "(fuente, nivel, codigo_producto, ambito, coalesce(codigo_mercado, ''), coalesce(ciudad, ''), "
    "anio, coalesce(mes, 0), coalesce(dia, 0), unidad_texto, cantidad, "
    "coalesce(informante, ''), coalesce(puesto, ''), precio_monto)"
)


class CorridaFuenteTabla(Base, Auditable):
    """
    Qué trajo cada corrida del recolector, por fuente y producto: cuántos
    hechos vio y cuántos eran NUEVOS.

    Es la otra mitad de la métrica. intento_fuente mide si el portal
    responde; esta tabla mide si el dato avanza. Una corrida con 200 hechos
    vistos y 0 nuevos es una corrida fallida a efectos de la tesis, aunque
    el servidor haya devuelto 200 veintidós días seguidos.
    """

    __tablename__ = "corrida_fuente"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fuente = Column(String(64), nullable=False)
    codigo_producto = Column(String(64), nullable=False)
    hechos_vistos = Column(Integer, nullable=False)
    hechos_nuevos = Column(Integer, nullable=False)
    ocurrido_en = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_corrida_fuente", "fuente", "ocurrido_en"),)


class IntentoFuenteTabla(Base, Auditable):
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


class UsuarioTabla(Base, Auditable):
    """Cuentas del sistema. La contraseña nunca se guarda: solo su hash."""

    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Se guarda ya normalizado (minúsculas, sin espacios). Es único solo
    # entre las cuentas vigentes (índice parcial uq_usuario_correo_vigente, en sesion.py): una cuenta
    # eliminada lógicamente no le impide a esa persona registrarse de nuevo.
    correo = Column(String(255), nullable=False)
    nombre = Column(String(255), nullable=False)
    rol = Column(String(16), ForeignKey("rol.codigo"), nullable=False, default="usuario")
    hash_contrasena = Column(String(255), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    # Los datos propios del vendedor van en su tabla (herencia: un vendedor
    # ES un usuario con algo más). Se lee junto con el usuario.
    vendedor = relationship("VendedorTabla", uselist=False, lazy="joined")


class VendedorTabla(Base, Auditable):
    """
    Lo que un vendedor tiene además de su cuenta: el puesto o tienda donde
    publica. Herencia por tabla unida (el JOINED de JPA): la clave primaria
    es también la clave foránea al usuario. Tiene fila quien es vendedor o
    tiene un puesto asignado.
    """

    __tablename__ = "vendedor"

    id_usuario = Column(Integer, ForeignKey("usuario.id"), primary_key=True)
    codigo_punto_venta = Column(String(64), ForeignKey("mercado.codigo"), nullable=True)


class ReporteTabla(Base, Auditable):
    """
    Reportes de precio a la espera de revisión. No se borran nunca: el
    rechazado queda con su motivo, porque de este historial sale la
    reputación de quien reporta.
    """

    __tablename__ = "reporte_precio"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo_producto = Column(String(64), nullable=False)
    codigo_mercado = Column(String(64), nullable=False)
    monto = Column(Float, nullable=False)
    unidad = Column(String(64), nullable=False)
    id_autor = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    estado = Column(String(16), nullable=False, default="pendiente")
    id_revisor = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    revisado_en = Column(DateTime(timezone=True), nullable=True)
    motivo_rechazo = Column(String(512), nullable=True)

    __table_args__ = (Index("ix_reporte_estado", "estado", "creado_en"),)



class ListaComprasTabla(Base, Auditable):
    """Listas de compras de cada usuario."""

    __tablename__ = "lista_compras"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    nombre = Column(String(120), nullable=False)

    __table_args__ = (Index("ix_lista_usuario", "id_usuario"),)


class ItemListaTabla(Base, Auditable):
    """Un renglón de una lista: producto, cantidad y presentación (2 arrobas de papa)."""

    __tablename__ = "item_lista_compras"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_lista = Column(Integer, ForeignKey("lista_compras.id"), nullable=False)
    codigo_producto = Column(String(64), nullable=False)
    cantidad = Column(Float, nullable=False)
    presentacion = Column(String(16), nullable=False)

    __table_args__ = (Index("ix_item_lista", "id_lista"),)


# --- puestos y ofertas de los caseros (C133) ------------------------------------

class PuestoTabla(Base, Auditable):
    """
    Un puesto dentro de un mercado: número, nombre, rubros y dueño. Se
    identifica por (mercado, número), como lo dice la gente: "el 14 del
    Rodríguez". Único solo entre los vigentes (índice parcial en sesion.py).
    """

    __tablename__ = "puesto"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo_mercado = Column(String(64), ForeignKey("mercado.codigo"), nullable=False)
    numero = Column(String(16), nullable=False)
    nombre = Column(String(80), nullable=False, default="")
    # "hortaliza,fruta": categorías del catálogo.
    rubros = Column(String(128), nullable=False, default="")
    referencia = Column(String(160), nullable=False, default="")
    id_vendedor = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    # Nombre del archivo de la foto (C137); la imagen vive en el almacén de fotos, no en la base.
    foto = Column(String(80), nullable=True)

    __table_args__ = (Index("ix_puesto_mercado", "codigo_mercado"),)


class InventarioPuestoTabla(Base, Auditable):
    """
    Qué vende un puesto, a cuánto y si le queda (C137). Una fila por puesto
    y producto, única entre las vigentes (índice parcial en sesion.py): si
    el casero deja de venderlo, se marca eliminado y la historia queda.
    """

    __tablename__ = "inventario_puesto"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_puesto = Column(Integer, ForeignKey("puesto.id"), nullable=False)
    codigo_producto = Column(String(64), ForeignKey("producto.codigo"), nullable=False)
    monto = Column(Float, nullable=False)
    presentacion = Column(String(16), nullable=False)
    # hay, poco o agotado.
    disponibilidad = Column(String(12), nullable=False, default="hay")
    actualizado_en = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_inventario_puesto", "id_puesto"),)


class OfertaTabla(Base, Auditable):
    """
    La oferta que declara un casero. NO es una observación y el motor de
    fusión no la lee: una rebaja la elige el vendedor y no debe mover la
    referencia del mercado. Vence sola (hasta); no se borra nunca.
    """

    __tablename__ = "oferta"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_vendedor = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    codigo_mercado = Column(String(64), ForeignKey("mercado.codigo"), nullable=False)
    numero_puesto = Column(String(16), nullable=True)
    codigo_producto = Column(String(64), ForeignKey("producto.codigo"), nullable=False)
    monto = Column(Float, nullable=False)
    presentacion = Column(String(16), nullable=False)
    # Bs por unidad base: con esto se compara contra el sistema.
    precio_por_unidad_base = Column(Float, nullable=False)
    desde = Column(DateTime(timezone=True), nullable=False)
    hasta = Column(DateTime(timezone=True), nullable=False)
    nota = Column(String(80), nullable=False, default="")
    estado = Column(String(16), nullable=False, default="activa")
    # C145: el nombre del combo al que pertenece (NULL si es suelta).
    combo = Column(String(40), nullable=True)

    __table_args__ = (
        Index("ix_oferta_vigencia", "estado", "hasta"),
        Index("ix_oferta_vendedor", "id_vendedor"),
    )


class ConfirmacionOfertaTabla(Base, Auditable):
    """
    "¿Lo viste así?": un comprador confirma o desmiente una oferta. Una
    fila por persona y oferta; si cambia de opinión se actualiza la misma
    (y la auditoría guarda cuándo).
    """

    __tablename__ = "confirmacion_oferta"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_oferta = Column(Integer, ForeignKey("oferta.id"), nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    la_vio_asi = Column(Boolean, nullable=False)

    __table_args__ = (Index("ix_confirmacion_oferta", "id_oferta", "id_usuario", unique=True),)
