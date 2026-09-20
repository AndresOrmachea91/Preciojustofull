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

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from src.infraestructura.adaptadores.salida.persistencia.sesion import sesion_de
from src.infraestructura.adaptadores.salida.persistencia.tablas import (
    CorridaFuenteTabla, IntentoFuenteTabla, MercadoTabla, ObservacionTabla, ProductoTabla,
)
from src.dominio.modelo import (
    Categoria, Fuente, Mercado, NivelPrecio, Observacion, Producto, TipoPuntoVenta,
)
from src.dominio.valor import (
    VARIEDAD_DESCONOCIDA, Ambito, Dinero, Periodo, TipoPrecio, Unidad, UnidadCanonica,
)

log = logging.getLogger(__name__)


# --- traducción entre filas y entidades ---------------------------------

def _a_producto(f: ProductoTabla) -> Producto:
    return Producto(
        codigo=f.codigo,
        nombre=f.nombre,
        categoria=Categoria(f.categoria),
        dias_conservacion=f.dias_conservacion,
        zona_origen=f.zona_origen,
        unidad_base=UnidadCanonica(f.unidad_base or "kg"),
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
        macrodistrito=f.macrodistrito or "",
        codigo_padre=f.codigo_padre,
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
        ambito=Ambito(f.ambito or "punto_venta"),
        cantidad=f.cantidad if f.cantidad else 1.0,
        variedad=f.variedad or VARIEDAD_DESCONOCIDA,
        fecha_observacion=f.fecha_observacion,
        tipo_precio=TipoPrecio(f.tipo_precio or "desconocido"),
        evidencia=f.evidencia,
    )


def _de_observacion(o: Observacion) -> dict:
    canonico, canonica = None, None
    if o.es_convertible:
        canonico = o.precio_canonico()
        canonica = o.unidad_canonica.value
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
        "cantidad": o.cantidad,
        "precio_canonico": canonico,
        "unidad_canonica": canonica,
        "variedad": o.variedad,
        "fecha_observacion": o.fecha_observacion,
        "tipo_precio": o.tipo_precio.value,
        "evidencia": o.evidencia,
        "reputacion_informante": o.reputacion_informante,
        "ambito": o.ambito.value,
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
            fila.unidad_base = producto.unidad_base.value


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
            fila.macrodistrito = mercado.macrodistrito
            fila.codigo_padre = mercado.codigo_padre


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
        Upsert por clave natural. Devuelve cuántos hechos NUEVOS entraron.

        - El mismo hecho con el mismo valor: no se inserta. Se anota que se
          volvió a ver (ultima_captura_en); la primera captura no se pisa.
        - El mismo hecho con OTRO valor: no es duplicado, es una revisión
          de la fuente. Se inserta apuntando a la fila anterior (revisa_a)
          y se conservan las dos con su captura.
        - Un hecho desconocido: se inserta.

        Se resuelve en Python y no con ON CONFLICT porque la tercera regla
        no se puede expresar ahí, y porque así funciona igual en SQLite y
        en PostgreSQL. Una sola consulta trae lo ya conocido de los
        productos del lote; no hay una consulta por observación.
        """
        if not observaciones:
            return 0

        ahora = datetime.now(timezone.utc)
        with sesion_de(self._fabrica) as s:
            conocidas = self._hechos_conocidos(s, observaciones)
            vistas: list[int] = []
            nuevas: list[dict] = []
            en_lote: set[tuple] = set()
            for o in observaciones:
                clave, monto = o.clave_natural, o.precio.monto
                if (clave, monto) in en_lote:
                    continue   # repetida dentro del mismo lote
                en_lote.add((clave, monto))
                previa = conocidas.get(clave)
                if previa is not None and previa[1] == monto:
                    vistas.append(previa[0])
                    continue
                fila = _de_observacion(o)
                fila["capturada_en"] = o.capturada_en
                fila["ultima_captura_en"] = o.capturada_en
                fila["revisa_a"] = previa[0] if previa is not None else None
                nuevas.append(fila)
            if nuevas:
                s.execute(ObservacionTabla.__table__.insert(), nuevas)
            if vistas:
                s.execute(
                    update(ObservacionTabla)
                    .where(ObservacionTabla.id.in_(vistas))
                    .values(ultima_captura_en=ahora)
                )
        return len(nuevas)

    @staticmethod
    def _hechos_conocidos(s: Session, observaciones: list[Observacion]) -> dict[tuple, tuple[int, float]]:
        """clave natural -> (id, monto) de la fila MÁS RECIENTE conocida de cada hecho."""
        productos = {o.codigo_producto for o in observaciones}
        fuentes = {o.fuente.value for o in observaciones}
        filas = s.execute(
            select(ObservacionTabla)
            .where(ObservacionTabla.codigo_producto.in_(productos))
            .where(ObservacionTabla.fuente.in_(fuentes))
            .order_by(ObservacionTabla.id)
        ).scalars()
        conocidas: dict[tuple, tuple[int, float]] = {}
        for f in filas:
            clave = (
                f.fuente, f.nivel, f.codigo_producto, f.ambito, f.codigo_mercado,
                f.anio, f.mes, f.dia, f.unidad_texto, f.cantidad if f.cantidad else 1.0,
            )
            conocidas[clave] = (f.id, f.precio_monto)   # la última por id gana
        return conocidas

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

    def registrar_corrida(self, fuente: str, codigo_producto: str, vistos: int, nuevos: int) -> None:
        with sesion_de(self._fabrica) as s:
            s.add(CorridaFuenteTabla(
                fuente=fuente, codigo_producto=codigo_producto,
                hechos_vistos=vistos, hechos_nuevos=nuevos,
                ocurrido_en=datetime.now(timezone.utc),
            ))

    def avance_del_dato(self) -> list[dict]:
        """
        Por fuente: cuántas corridas hubo, cuántas trajeron al menos un
        hecho nuevo, cuántos hechos nuevos en total y cuándo fue la última
        vez que entró uno. Esto es lo que mide si el dato avanza.
        """
        from sqlalchemy import case, func

        with sesion_de(self._fabrica) as s:
            filas = s.execute(
                select(
                    CorridaFuenteTabla.fuente,
                    func.count().label("corridas"),
                    func.sum(case((CorridaFuenteTabla.hechos_nuevos > 0, 1), else_=0)).label("con_dato_nuevo"),
                    func.sum(CorridaFuenteTabla.hechos_vistos).label("vistos"),
                    func.sum(CorridaFuenteTabla.hechos_nuevos).label("nuevos"),
                    func.max(case((CorridaFuenteTabla.hechos_nuevos > 0, CorridaFuenteTabla.ocurrido_en))).label("ultimo_nuevo"),
                ).group_by(CorridaFuenteTabla.fuente)
            ).all()
        return [
            {
                "fuente": f.fuente,
                "corridas": f.corridas,
                "con_dato_nuevo": int(f.con_dato_nuevo or 0),
                "porcentaje": round(100.0 * (f.con_dato_nuevo or 0) / f.corridas, 1) if f.corridas else 0.0,
                "vistos": int(f.vistos or 0),
                "nuevos": int(f.nuevos or 0),
                "ultimo_nuevo": f.ultimo_nuevo,
            }
            for f in filas
        ]

    def disponibilidad(self) -> list[dict]:
        """Insumo de la métrica de disponibilidad de la FUENTE (respuesta HTTP)."""
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
