"""Conexión a la base de datos y creación del esquema."""
from __future__ import annotations

import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.infraestructura.adaptadores.salida.persistencia.tablas import (
    INDICE_CLAVE_NATURAL, NOMBRE_INDICE_CLAVE_NATURAL, NOMBRE_INDICE_CLAVE_NATURAL_ANTERIOR, metadata,
)
from src.infraestructura.adaptadores.salida.persistencia.auditable import COLUMNAS_AUDITORIA, como_actor
from src.infraestructura.adaptadores.salida.persistencia.referencias import sincronizar_referencias

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
        "presentaciones": "VARCHAR(128) NULL",
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
        "ultima_captura_en": "TIMESTAMP WITH TIME ZONE NULL",
        "revisa_a": "INTEGER NULL REFERENCES observacion_precio(id)",
        "ciudad": "VARCHAR(64) NULL",
        "informante": "VARCHAR(64) NULL",
        "puesto": "VARCHAR(16) NULL",
    },
    "puesto": {
        "foto": "VARCHAR(80) NULL",
    },
    "oferta": {
        "combo": "VARCHAR(40) NULL",
    },
}

# Las 5 columnas de Auditable, para las tablas que existían antes de la
# auditoría. Las filas viejas quedan "creadas por sistema"; su fecha de
# creación se corrige abajo con la fecha real que cada tabla ya tenía.
_TABLAS_AUDITADAS = (
    "producto", "mercado", "observacion_precio", "corrida_fuente", "intento_fuente",
    "usuario", "reporte_precio", "lista_compras", "item_lista_compras",
    "rol", "permiso", "rol_permiso", "fuente", "vendedor",
)


def _definicion_auditoria(columna: str, dialecto: str) -> str:
    # SQLite no acepta CURRENT_TIMESTAMP como valor por defecto en un ALTER;
    # solo importa en bases SQLite viejas, que en la práctica no existen.
    creado = "CURRENT_TIMESTAMP" if dialecto == "postgresql" else "'1970-01-01 00:00:00'"
    return {
        "creado_en": f"TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT {creado}",
        "creado_por": "VARCHAR(255) NOT NULL DEFAULT 'sistema'",
        "modificado_en": "TIMESTAMP WITH TIME ZONE NULL",
        "modificado_por": "VARCHAR(255) NULL",
        "eliminado": "BOOLEAN NOT NULL DEFAULT FALSE",
    }[columna]


# Recién agregada la auditoría, la fecha de creación honesta de una fila
# histórica es la que la tabla ya guardaba, no el momento de la migración.
_FECHA_REAL_DE_CREACION = {
    "observacion_precio": "capturada_en",
    "corrida_fuente": "ocurrido_en",
    "intento_fuente": "ocurrido_en",
}

# Índice parcial: una cuenta eliminada lógicamente libera su correo.
_CORREO_UNICO_VIGENTE = (
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_usuario_correo_vigente ON usuario (correo) WHERE NOT eliminado"
)

# Un número de puesto es único dentro de su mercado, entre los vigentes:
# un puesto dado de baja libera su número. Y un vendedor tiene un solo puesto.
_PUESTO_UNICO_VIGENTE = (
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_puesto_numero_vigente ON puesto (codigo_mercado, numero) "
    "WHERE NOT eliminado"
)
_PUESTO_UNO_POR_VENDEDOR = (
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_puesto_vendedor_vigente ON puesto (id_vendedor) "
    "WHERE NOT eliminado AND id_vendedor IS NOT NULL"
)

# Un producto aparece una sola vez en el inventario vigente de un puesto.
_INVENTARIO_UNICO_VIGENTE = (
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_inventario_vigente ON inventario_puesto (id_puesto, codigo_producto) "
    "WHERE NOT eliminado"
)

# informante se agregó con ALTER: el índice que declara la tabla solo nace
# con create_all en una base nueva, así que en una que ya existía se crea acá.
_INDICE_INFORMANTE = (
    "CREATE INDEX IF NOT EXISTS ix_observacion_precio_informante ON observacion_precio (informante)"
)

# Cambios que SQLite no sabe hacer con ALTER (soltar un NOT NULL). En
# SQLite las tablas nuevas ya nacen bien desde create_all; en PostgreSQL
# hace falta decirlo. Se ejecuta antes de los rellenos.
_AJUSTES_POR_DIALECTO = {
    "postgresql": [
        "ALTER TABLE observacion_precio ALTER COLUMN codigo_mercado DROP NOT NULL",
        "ALTER TABLE observacion_precio DROP CONSTRAINT IF EXISTS uq_observacion_unica",
        # Una version anterior de esta migracion creo la columna sin zona
        # horaria; capturada_en la tiene. Se iguala, leyendo lo guardado como UTC.
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'observacion_precio' AND column_name = 'ultima_captura_en' "
        "AND data_type = 'timestamp without time zone') THEN "
        "ALTER TABLE observacion_precio ALTER COLUMN ultima_captura_en TYPE timestamp with time zone "
        "USING ultima_captura_en AT TIME ZONE 'UTC'; END IF; END $$",
        # El correo era único en toda la tabla; ahora solo entre los vigentes.
        "ALTER TABLE usuario DROP CONSTRAINT IF EXISTS usuario_correo_key",
        _CORREO_UNICO_VIGENTE,
        _PUESTO_UNICO_VIGENTE,
        _PUESTO_UNO_POR_VENDEDOR,
        _INDICE_INFORMANTE,
        _INVENTARIO_UNICO_VIGENTE,
    ],
    "sqlite": [_CORREO_UNICO_VIGENTE, _PUESTO_UNICO_VIGENTE, _PUESTO_UNO_POR_VENDEDOR, _INDICE_INFORMANTE,
               _INVENTARIO_UNICO_VIGENTE],
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
# Una voz por informante: quién afirmó cada observación histórica se lee
# de su evidencia. El vendedor dejó "vendedor:ID"; el reporte aprobado,
# "reporte:ID", cuyo autor está en reporte_precio. Lo que no trae
# evidencia de una persona queda NULL: no se adivina.
_INFORMANTE_VENDEDOR = (
    "UPDATE observacion_precio SET informante = 'usuario:' || substr(evidencia, 10) "
    "WHERE informante IS NULL AND fuente = 'vendedor' AND evidencia LIKE 'vendedor:%'"
)
_INFORMANTE_REPORTE = (
    "UPDATE observacion_precio SET informante = ("
    "SELECT 'usuario:' || CAST(r.id_autor AS VARCHAR) FROM reporte_precio r "
    "WHERE 'reporte:' || CAST(r.id AS VARCHAR) = observacion_precio.evidencia) "
    "WHERE informante IS NULL AND evidencia LIKE 'reporte:%'"
)
# Decisión 26 (1 de noviembre): el sistema es de mercados y caseros. Las
# cadenas (supermercados, minimarkets, tiendas y el mayorista Makro) se dan
# de baja LÓGICA: la fila y sus observaciones quedan, y se pueden reactivar.
CADENAS_FUERA_DE_ALCANCE = ("makro_centro",)
_CADENAS_FUERA = (
    "UPDATE mercado SET eliminado = TRUE, modificado_por = 'decision-26', modificado_en = CURRENT_TIMESTAMP "
    "WHERE NOT eliminado AND (tipo IN ('supermercado', 'minimarket', 'tienda') "
    f"OR codigo IN ({', '.join(repr(c) for c in CADENAS_FUERA_DE_ALCANCE)}))"
)

# El rol "recolector" pasó a llamarse "vendedor" (decisión del 8 de octubre).
_ROL_RENOMBRADO = "UPDATE usuario SET rol = 'vendedor' WHERE rol = 'recolector'"

_RELLENOS_HISTORICOS = {
    "sqlite": [
        _CADENAS_FUERA,
        _ROL_RENOMBRADO,
        _AMBITO_POR_FUENTE,
        _INFORMANTE_VENDEDOR,
        _INFORMANTE_REPORTE,
        "UPDATE observacion_precio SET fecha_observacion = "
        "date(printf('%04d-%02d-%02d', anio, mes, dia)) "
        "WHERE fecha_observacion IS NULL AND mes IS NOT NULL AND dia IS NOT NULL",
    ],
    "postgresql": [
        _CADENAS_FUERA,
        _ROL_RENOMBRADO,
        _AMBITO_POR_FUENTE,
        _INFORMANTE_VENDEDOR,
        _INFORMANTE_REPORTE,
        "UPDATE observacion_precio SET fecha_observacion = make_date(anio, mes, dia) "
        "WHERE fecha_observacion IS NULL AND mes IS NOT NULL AND dia IS NOT NULL",
    ],
}


# El puesto del vendedor estuvo primero en usuario.codigo_punto_venta; ahora
# vive en la tabla vendedor. Se copia una vez y la columna vieja se quita.
_PUESTO_A_VENDEDOR = (
    "INSERT INTO vendedor (id_usuario, codigo_punto_venta, creado_en, creado_por, eliminado) "
    "SELECT u.id, u.codigo_punto_venta, CURRENT_TIMESTAMP, 'migracion', u.eliminado FROM usuario u "
    "WHERE (u.codigo_punto_venta IS NOT NULL OR u.rol = 'vendedor') "
    "AND NOT EXISTS (SELECT 1 FROM vendedor v WHERE v.id_usuario = u.id)"
)

# Claves foráneas hacia los catálogos en una base que ya existía (create_all
# solo las pone al crear la tabla). Van después de sincronizar los catálogos
# y de renombrar el rol viejo, para que ninguna fila quede huérfana.
_RELACIONES_POSTGRES = [
    ("usuario", "fk_usuario_rol", "FOREIGN KEY (rol) REFERENCES rol(codigo)"),
    ("observacion_precio", "fk_observacion_fuente", "FOREIGN KEY (fuente) REFERENCES fuente(codigo)"),
]


def _migrar_a_catalogos(motor: Engine) -> None:
    """Va en su propia transacción, después de la migración de columnas y rellenos."""
    with como_actor("sistema"), Session(motor) as s:
        sincronizar_referencias(s)
        s.commit()
    columnas = {c["name"] for c in inspect(motor).get_columns("usuario")}
    with motor.begin() as conexion:
        if "codigo_punto_venta" in columnas:
            conexion.execute(text(_PUESTO_A_VENDEDOR))
            conexion.execute(text("ALTER TABLE usuario DROP COLUMN codigo_punto_venta"))
            log.info("Puesto de los vendedores movido a la tabla vendedor")
        if motor.dialect.name != "postgresql":
            return
        for tabla, nombre, definicion in _RELACIONES_POSTGRES:
            conexion.execute(text(
                f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = '{nombre}') "
                f"THEN ALTER TABLE {tabla} ADD CONSTRAINT {nombre} {definicion}; END IF; END $$"
            ))


def crear_esquema(motor: Engine) -> None:
    """Crea las tablas y columnas que falten. Es idempotente."""
    metadata.create_all(motor)
    inspector = inspect(motor)
    dialecto = motor.dialect.name
    with motor.begin() as conexion:
        for tabla, columnas in _COLUMNAS_AGREGADAS.items():
            existentes = {c["name"] for c in inspector.get_columns(tabla)}
            for nombre, definicion in columnas.items():
                if nombre not in existentes:
                    conexion.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {definicion}"))
                    log.info("Columna %s.%s agregada", tabla, nombre)
        for tabla in _TABLAS_AUDITADAS:
            existentes = {c["name"] for c in inspector.get_columns(tabla)}
            faltantes = [c for c in COLUMNAS_AUDITORIA if c not in existentes]
            for nombre in faltantes:
                conexion.execute(text(
                    f"ALTER TABLE {tabla} ADD COLUMN {nombre} {_definicion_auditoria(nombre, dialecto)}"
                ))
            if faltantes:
                log.info("Auditoría agregada a %s: %s", tabla, ", ".join(faltantes))
            if "creado_en" in faltantes and tabla in _FECHA_REAL_DE_CREACION:
                conexion.execute(text(
                    f"UPDATE {tabla} SET creado_en = {_FECHA_REAL_DE_CREACION[tabla]}"
                ))
        for sentencia in _AJUSTES_POR_DIALECTO.get(motor.dialect.name, []):
            conexion.execute(text(sentencia))
        for sentencia in _RELLENOS_HISTORICOS.get(motor.dialect.name, []):
            rellenadas = conexion.execute(text(sentencia)).rowcount
            if rellenadas:
                log.info("Filas históricas completadas: %s", rellenadas)
    _migrar_a_catalogos(motor)
    _actualizar_indice_clave_natural(motor)
    log.info("Esquema verificado")


def _actualizar_indice_clave_natural(motor: Engine) -> None:
    """
    Si la base tiene el índice de la clave natural ANTERIOR (sin informante
    ni puesto), se cambia por el nuevo. Es seguro hacerlo al arrancar: la
    clave nueva es más fina, así que lo que era único antes lo sigue
    siendo. Si no hay ninguno, no se crea acá (ver asegurar_indice_clave_natural).
    """
    # Se pregunta al catálogo de la base y no al inspector: el índice es de
    # expresiones (coalesce) y no todos los dialectos lo reflejan.
    catalogo = (
        "SELECT 1 FROM pg_indexes WHERE indexname = :n" if motor.dialect.name == "postgresql"
        else "SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = :n"
    )
    with motor.begin() as conexion:
        if conexion.execute(text(catalogo), {"n": NOMBRE_INDICE_CLAVE_NATURAL_ANTERIOR}).first() is None:
            return
        conexion.execute(text(INDICE_CLAVE_NATURAL))
        conexion.execute(text(f"DROP INDEX IF EXISTS {NOMBRE_INDICE_CLAVE_NATURAL_ANTERIOR}"))
    log.info("Índice de la clave natural actualizado a %s", NOMBRE_INDICE_CLAVE_NATURAL)


def asegurar_indice_clave_natural(motor: Engine) -> None:
    """
    Crea el índice único del hecho observado. Idempotente. Va aparte de
    crear_esquema porque sobre una tabla con duplicados históricos falla:
    primero se limpia (script de reparación), después se crea.
    """
    with motor.begin() as conexion:
        conexion.execute(text(INDICE_CLAVE_NATURAL))
        conexion.execute(text(f"DROP INDEX IF EXISTS {NOMBRE_INDICE_CLAVE_NATURAL_ANTERIOR}"))
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
