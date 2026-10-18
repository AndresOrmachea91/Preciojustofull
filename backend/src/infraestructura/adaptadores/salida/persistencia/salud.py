"""
Lectura del estado del sistema para el panel de salud (C132). Solo cuenta
y agrupa: no decide qué está bien. Las consultas sirven en PostgreSQL y en
SQLite (las pruebas corren sobre SQLite).
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from src.dominio.modelo import DatosDeFuente, DatosSalud, UltimaRecoleccion
from src.infraestructura.adaptadores.salida.persistencia.sesion import sesion_de

_POR_FUENTE = (
    "SELECT fuente, COUNT(*) AS n, MAX(capturada_en) AS ultima FROM observacion_precio "
    "WHERE NOT eliminado GROUP BY fuente ORDER BY n DESC"
)
_ULTIMO_INTENTO = (
    "SELECT i.fuente, i.ocurrido_en, i.exito, i.detalle FROM intento_fuente i "
    "JOIN (SELECT fuente, MAX(ocurrido_en) AS m FROM intento_fuente GROUP BY fuente) u "
    "ON u.fuente = i.fuente AND u.m = i.ocurrido_en"
)
_ULTIMO_EXITO = "SELECT fuente, MAX(ocurrido_en) FROM intento_fuente WHERE exito = 1 GROUP BY fuente"
_NUEVOS = "SELECT fuente, COALESCE(SUM(hechos_nuevos), 0) FROM corrida_fuente WHERE ocurrido_en >= :desde GROUP BY fuente"
_PARES_OBSERVADOS = (
    "SELECT COUNT(*) FROM (SELECT DISTINCT codigo_mercado, codigo_producto FROM observacion_precio "
    "WHERE NOT eliminado AND ambito = 'punto_venta' AND codigo_mercado IS NOT NULL "
    "AND (fecha_observacion >= :desde OR (fecha_observacion IS NULL AND capturada_en >= :desde_dt))) t"
)


def _con_zona(valor):
    """SQLite devuelve las fechas sin zona horaria (o como texto); se leen como UTC."""
    if valor is None:
        return None
    if isinstance(valor, str):
        valor = datetime.fromisoformat(valor)
    return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)


class SaludPostgres:
    def __init__(self, fabrica: sessionmaker[Session]):
        self._fabrica = fabrica

    def leer(self, desde: date) -> DatosSalud:
        desde_dt = datetime.combine(desde, time.min, tzinfo=timezone.utc)
        hace_un_dia = datetime.now(timezone.utc) - timedelta(hours=24)
        with sesion_de(self._fabrica) as s:
            fuentes = [DatosDeFuente(f, int(n), _con_zona(u)) for f, n, u in s.execute(text(_POR_FUENTE))]
            exitos = {f: _con_zona(m) for f, m in s.execute(text(_ULTIMO_EXITO))}
            nuevos = {f: int(n) for f, n in s.execute(text(_NUEVOS), {"desde": hace_un_dia})}
            recolecciones = []
            for fuente, ocurrido, exito, detalle in s.execute(text(_ULTIMO_INTENTO)):
                ultimo_exito = exitos.get(fuente)
                recolecciones.append(UltimaRecoleccion(
                    fuente=fuente,
                    # Lo que importa es cuándo trajo datos por última vez.
                    ocurrido_en=ultimo_exito or _con_zona(ocurrido),
                    exito=ultimo_exito is not None,
                    detalle=None if exito else detalle,
                    hechos_nuevos_24h=nuevos.get(fuente, 0),
                ))
            observados = s.execute(text(_PARES_OBSERVADOS), {"desde": desde, "desde_dt": desde_dt}).scalar() or 0
            mercados = s.execute(text("SELECT COUNT(*) FROM mercado WHERE NOT eliminado")).scalar() or 0
            productos = s.execute(text("SELECT COUNT(*) FROM producto WHERE NOT eliminado")).scalar() or 0
        return DatosSalud(
            fuentes=fuentes,
            recolecciones=sorted(recolecciones, key=lambda r: r.fuente),
            pares_observados=int(observados),
            pares_posibles=int(mercados) * int(productos),
        )
