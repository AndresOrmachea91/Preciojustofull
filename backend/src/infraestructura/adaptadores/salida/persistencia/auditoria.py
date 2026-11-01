"""
/bd/auditoria: los 5 campos de Auditable de todas las tablas, en una sola
consulta de lectura.

No hay una tabla de logs (decisión del 8 de octubre): la auditoría vive en
cada fila. Para verla junta, se pide a cada tabla sus filas cambiadas más
recientemente y se unen. Cada tabla aporta una clave legible y una
descripción corta para que el administrador sepa de qué fila se trata.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from src.dominio.modelo import Auditoria, RegistroAuditado
from src.infraestructura.adaptadores.salida.persistencia.sesion import sesion_de

# tabla → (clave, descripción), como expresiones SQL que sirven en
# PostgreSQL y en SQLite (las pruebas corren sobre SQLite).
_COMO_SE_LEE: dict[str, tuple[str, str]] = {
    "usuario": ("correo", "nombre || ' (' || rol || ')'"),
    "vendedor": ("CAST(id_usuario AS TEXT)", "'puesto: ' || COALESCE(codigo_punto_venta, 'sin asignar')"),
    "rol": ("codigo", "nombre"),
    "permiso": ("codigo", "descripcion"),
    "rol_permiso": ("codigo_rol || ' / ' || codigo_permiso", "'permiso del rol'"),
    "fuente": ("codigo", "nombre"),
    "producto": ("codigo", "nombre"),
    "mercado": ("codigo", "nombre"),
    "observacion_precio": (
        "CAST(id AS TEXT)",
        "codigo_producto || ' · ' || fuente || ' · Bs ' || CAST(precio_monto AS TEXT) || ' ' || unidad_texto",
    ),
    "reporte_precio": ("CAST(id AS TEXT)", "codigo_producto || ' en ' || codigo_mercado || ' · ' || estado"),
    "lista_compras": ("CAST(id AS TEXT)", "nombre"),
    "item_lista_compras": (
        "CAST(id AS TEXT)",
        "codigo_producto || ' × ' || CAST(cantidad AS TEXT) || ' ' || presentacion",
    ),
    "corrida_fuente": (
        "CAST(id AS TEXT)",
        "fuente || ' · ' || codigo_producto || ' · ' || CAST(hechos_nuevos AS TEXT) || ' nuevos'",
    ),
    "intento_fuente": ("CAST(id AS TEXT)", "fuente || CASE WHEN exito = 1 THEN ' · respondió' ELSE ' · falló' END"),
    "puesto": ("codigo_mercado || ' / ' || numero", "'puesto ' || numero || ' ' || nombre"),
    "oferta": (
        "CAST(id AS TEXT)",
        "codigo_producto || ' en ' || codigo_mercado || ' · Bs ' || CAST(monto AS TEXT) || ' ' || presentacion "
        "|| ' · ' || estado",
    ),
    "confirmacion_oferta": (
        "CAST(id AS TEXT)",
        "'oferta ' || CAST(id_oferta AS TEXT) || CASE WHEN la_vio_asi THEN ' · la vio así' ELSE ' · no estaba así' END",
    ),
    "inventario_puesto": (
        "CAST(id_puesto AS TEXT) || ' / ' || codigo_producto",
        "codigo_producto || ' · Bs ' || CAST(monto AS TEXT) || ' por ' || presentacion || ' · ' || disponibilidad",
    ),
}


def _con_zona(momento) -> datetime | None:
    # SQLite devuelve texto o fechas sin zona; todo se guarda en UTC.
    if momento is None:
        return None
    if isinstance(momento, str):
        momento = datetime.fromisoformat(momento)
    return momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)


def _consulta(tabla: str, n: int) -> str:
    clave, descripcion = _COMO_SE_LEE[tabla]
    return (
        f"SELECT * FROM (SELECT '{tabla}' AS tabla, {clave} AS clave, {descripcion} AS descripcion, "
        f"creado_en, creado_por, modificado_en, modificado_por, eliminado FROM {tabla} "
        f"ORDER BY COALESCE(modificado_en, creado_en) DESC LIMIT {int(n)}) AS {tabla}_reciente"
    )


class AuditoriaPostgres:
    def __init__(self, fabrica: sessionmaker[Session]):
        self._fabrica = fabrica

    def tablas(self) -> list[str]:
        return list(_COMO_SE_LEE)

    def recientes(self, tabla: str | None, limite: int) -> list[RegistroAuditado]:
        # Los nombres de tabla salen de _COMO_SE_LEE, nunca de lo que llega
        # por la API: así no hay forma de inyectar SQL.
        elegidas = [tabla] if tabla in _COMO_SE_LEE else list(_COMO_SE_LEE)
        sql = " UNION ALL ".join(_consulta(t, limite) for t in elegidas)
        with sesion_de(self._fabrica) as s:
            filas = s.execute(text(sql)).all()
        return [
            RegistroAuditado(
                tabla=f.tabla, clave=str(f.clave), descripcion=f.descripcion or "",
                auditoria=Auditoria(
                    creado_en=_con_zona(f.creado_en), creado_por=f.creado_por,
                    modificado_en=_con_zona(f.modificado_en), modificado_por=f.modificado_por,
                    eliminado=bool(f.eliminado),
                ),
            )
            for f in filas
        ]
