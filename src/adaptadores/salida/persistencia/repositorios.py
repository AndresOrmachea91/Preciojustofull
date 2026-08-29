"""
Adaptador de persistencia sobre SQLAlchemy.

Implementa los mismos tres puertos que el adaptador en memoria:
RepositorioProductos, RepositorioMercados y RepositorioObservaciones.

Que existan dos adaptadores intercambiables para el mismo puerto es el
argumento central de la arquitectura, y no es una afirmación: hay una
prueba de contrato (`tests/test_contrato_repositorios.py`) que corre el
mismo conjunto de casos contra los dos.

La traducción entre filas y entidades del dominio vive acá. El dominio no
sabe que existe SQLAlchemy.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as insert_pg
from sqlalchemy.dialects.sqlite import insert as insert_sqlite
from sqlalchemy.orm import Session, sessionmaker

from src.adaptadores.salida.persistencia.sesion import sesion_de
from src.adaptadores.salida.persistencia.tablas import (
    IntentoFuenteTabla, MercadoTabla, ObservacionTabla, ProductoTabla,
)
from src.dominio.modelo import (
    Categoria, Fuente, Mercado, NivelPrecio, Observacion, Producto, TipoPuntoVenta,
)
from src.dominio.valor import Dinero, Periodo, Unidad

log = logging.getLogger(__name__)


# --- traducción entre filas y entidades ---------------------------------

def _a_producto(f: ProductoTabla) -> Producto:
    return Producto(
        codigo=f.codigo,
        nombre=f.nombre,
        categoria=Categoria(f.categoria),
        dias_conservacion=f.dias_conservacion,
        zona_origen=f.zona_origen,
    )


def _a_mercado(f: MercadoTabla) -> Mercado:
    return Mercado(
        codigo=f.codigo,
        nombre=f.nombre,
        tipo=TipoPuntoVenta(f.tipo),
        zona=f.zona,
        latitud=f.latitud,
        longitud=f.longitud,
        factor_mercado=f.factor_mercado,
    )


def _a_observacion(f: ObservacionTabla) -> Observacion:
    return Observacion(
        fuente=Fuente(f.fuente),
        nivel=NivelPrecio(f.nivel),
        codigo_producto=f.codigo_producto,
        codigo_mercado=f.codigo_mercado,
        periodo=Periodo(f.anio, f.mes, f.dia),
        precio=Dinero(f.precio_monto, Unidad(f.unidad_texto)),
        capturada_en=f.capturada_en,
        reputacion_informante=f.reputacion_informante,
    )


def _de_observacion(o: Observacion) -> dict:
    canonico, canonica = None, None
    if o.precio.unidad.es_conocida():
        canonico, unidad = o.precio.por_unidad_canonica()
        canonica = unidad.value
    return {
        "fuente": o.fuente.value,
        "nivel": o.nivel.value,
        "codigo_producto": o.codigo_producto,
        "codigo_mercado": o.codigo_mercado,
        "anio": o.periodo.anio,
        "mes": o.periodo.mes,
        "dia": o.periodo.dia,
        "precio_monto": o.precio.monto,
        "unidad_texto": o.precio.unidad.texto,
        "precio_canonico": canonico,
        "unidad_canonica": canonica,
        "reputacion_informante": o.reputacion_informante,
        "capturada_en": o.capturada_en,
    }


# --- repositorios --------------------------------------------------------

class _Base:
    def __init__(self, fabrica: sessionmaker[Session]):
        self._fabrica = fabrica


class ProductosPostgres(_Base):
    def obtener(self, codigo: str) -> Producto | None:
        with sesion_de(self._fabrica) as s:
            fila = s.get(ProductoTabla, codigo)
            return _a_producto(fila) if fila else None

    def listar(self) -> list[Producto]:
        with sesion_de(self._fabrica) as s:
            filas = s.scalars(select(ProductoTabla).order_by(ProductoTabla.nombre)).all()
            return [_a_producto(f) for f in filas]

    def guardar(self, producto: Producto) -> None:
        with sesion_de(self._fabrica) as s:
            fila = s.get(ProductoTabla, producto.codigo)
            if fila is None:
                fila = ProductoTabla(codigo=producto.codigo)
                s.add(fila)
            fila.nombre = producto.nombre
            fila.categoria = producto.categoria.value
            fila.dias_conservacion = producto.dias_conservacion
            fila.zona_origen = producto.zona_origen


class MercadosPostgres(_Base):
    def obtener(self, codigo: str) -> Mercado | None:
        with sesion_de(self._fabrica) as s:
            fila = s.get(MercadoTabla, codigo)
            return _a_mercado(fila) if fila else None

    def listar(self, zona: str | None = None) -> list[Mercado]:
        with sesion_de(self._fabrica) as s:
            consulta = select(MercadoTabla).order_by(MercadoTabla.nombre)
            if zona:
                consulta = consulta.where(MercadoTabla.zona.ilike(zona))
            return [_a_mercado(f) for f in s.scalars(consulta).all()]

    def guardar(self, mercado: Mercado) -> None:
        with sesion_de(self._fabrica) as s:
            fila = s.get(MercadoTabla, mercado.codigo)
            if fila is None:
                fila = MercadoTabla(codigo=mercado.codigo)
                s.add(fila)
            fila.nombre = mercado.nombre
            fila.tipo = mercado.tipo.value
            fila.zona = mercado.zona
            fila.latitud = mercado.latitud
            fila.longitud = mercado.longitud
            fila.factor_mercado = mercado.factor_mercado


class ObservacionesPostgres(_Base):
    def buscar(
        self,
        codigo_producto: str,
        codigo_mercado: str | None = None,
        periodo: Periodo | None = None,
    ) -> list[Observacion]:
        with sesion_de(self._fabrica) as s:
            consulta = select(ObservacionTabla).where(
                ObservacionTabla.codigo_producto == codigo_producto
            )
            if codigo_mercado:
                consulta = consulta.where(ObservacionTabla.codigo_mercado == codigo_mercado)
            if periodo:
                consulta = consulta.where(ObservacionTabla.anio == periodo.anio)
                if periodo.mes is not None:
                    consulta = consulta.where(ObservacionTabla.mes == periodo.mes)
                if periodo.dia is not None:
                    consulta = consulta.where(ObservacionTabla.dia == periodo.dia)
            return [_a_observacion(f) for f in s.scalars(consulta).all()]

    def guardar_varias(self, observaciones: list[Observacion]) -> int:
        """
        Inserta ignorando duplicados. Devuelve cuántas filas NUEVAS entraron.

        Que sea idempotente es lo que permite correr el recolector tres
        veces al día sin duplicar la serie: si el dato ya estaba, no pasa
        nada.
        """
        if not observaciones:
            return 0

        filas = [_de_observacion(o) for o in observaciones]
        with sesion_de(self._fabrica) as s:
            dialecto = s.get_bind().dialect.name
            insert = insert_pg if dialecto == "postgresql" else insert_sqlite
            sentencia = insert(ObservacionTabla).values(filas).on_conflict_do_nothing(
                index_elements=[
                    "fuente", "codigo_producto", "codigo_mercado", "anio", "mes", "dia",
                ]
            )
            resultado = s.execute(sentencia)
            nuevas = resultado.rowcount if resultado.rowcount is not None else 0
        return max(nuevas, 0)

    def registrar_intento(
        self, fuente: str, url: str | None, exito: bool, duracion_ms: int, detalle: str
    ) -> None:
        from datetime import datetime, timezone

        with sesion_de(self._fabrica) as s:
            s.add(IntentoFuenteTabla(
                fuente=fuente, url=(url or "")[:512], exito=1 if exito else 0,
                duracion_ms=duracion_ms, detalle=(detalle or "")[:512],
                ocurrido_en=datetime.now(timezone.utc),
            ))

    def disponibilidad(self) -> list[dict]:
        """Insumo de la métrica de disponibilidad efectiva del dato."""
        from sqlalchemy import func

        with sesion_de(self._fabrica) as s:
            filas = s.execute(
                select(
                    IntentoFuenteTabla.fuente,
                    func.count().label("intentos"),
                    func.sum(IntentoFuenteTabla.exito).label("exitosos"),
                    func.avg(IntentoFuenteTabla.duracion_ms).label("ms_promedio"),
                ).group_by(IntentoFuenteTabla.fuente)
            ).all()

        return [
            {
                "fuente": f.fuente,
                "intentos": f.intentos,
                "exitosos": int(f.exitosos or 0),
                "porcentaje": round(100.0 * (f.exitosos or 0) / f.intentos, 1) if f.intentos else 0.0,
                "ms_promedio": round(f.ms_promedio or 0),
            }
            for f in filas
        ]
