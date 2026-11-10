"""
Puestos, ofertas y confirmaciones sobre SQLAlchemy (C133). Implementan
RepositorioPuestos y RepositorioOfertas.

Las tres tablas son auditadas y nada se borra: una oferta retirada o
vencida queda con su estado, y la confirmación que cambia de opinión se
actualiza en su lugar (la auditoría dice cuándo).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from src.dominio.modelo import (
    ArticuloInventario, Categoria, Confirmacion, Disponibilidad, EstadoOferta, Oferta, Presentacion, Puesto,
)
from src.dominio.modelo.auditoria import Auditoria
from src.dominio.modelo.puesto import orden_de_numero
from src.infraestructura.adaptadores.salida.persistencia.sesion import sesion_de
from src.infraestructura.adaptadores.salida.persistencia.tablas import (
    ConfirmacionOfertaTabla, InventarioPuestoTabla, OfertaTabla, PuestoTabla,
)


def _utc(momento: datetime | None) -> datetime | None:
    # SQLite devuelve las fechas sin zona; todo se guarda en UTC.
    if momento is None:
        return None
    return momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)


def _auditoria(f) -> Auditoria:
    return Auditoria(_utc(f.creado_en), f.creado_por, _utc(f.modificado_en), f.modificado_por, f.eliminado)


def _a_puesto(f: PuestoTabla) -> Puesto:
    return Puesto(
        id=f.id, codigo_mercado=f.codigo_mercado, numero=f.numero, nombre=f.nombre or "",
        rubros=tuple(Categoria(r) for r in (f.rubros or "").split(",") if r),
        referencia=f.referencia or "", id_vendedor=f.id_vendedor, foto=f.foto, auditoria=_auditoria(f),
        celular=f.celular,
    )


def _a_articulo(f: InventarioPuestoTabla) -> ArticuloInventario:
    return ArticuloInventario(
        id=f.id, id_puesto=f.id_puesto, codigo_producto=f.codigo_producto, monto=f.monto,
        presentacion=Presentacion(f.presentacion), disponibilidad=Disponibilidad(f.disponibilidad),
        actualizado_en=_utc(f.actualizado_en), auditoria=_auditoria(f),
    )


def _a_oferta(f: OfertaTabla) -> Oferta:
    return Oferta(
        id=f.id, id_vendedor=f.id_vendedor, codigo_mercado=f.codigo_mercado, numero_puesto=f.numero_puesto,
        codigo_producto=f.codigo_producto, monto=f.monto, presentacion=Presentacion(f.presentacion),
        desde=_utc(f.desde), hasta=_utc(f.hasta), nota=f.nota or "", estado=EstadoOferta(f.estado),
        combo=f.combo, auditoria=_auditoria(f),
    )


class PuestosPostgres:
    def __init__(self, fabrica: sessionmaker[Session]):
        self._fabrica = fabrica

    def del_vendedor(self, id_vendedor: int) -> Puesto | None:
        with sesion_de(self._fabrica) as s:
            fila = s.scalars(select(PuestoTabla).where(
                PuestoTabla.id_vendedor == id_vendedor, PuestoTabla.eliminado.is_(False),
            )).first()
            return _a_puesto(fila) if fila is not None else None

    def del_mercado(self, codigo_mercado: str) -> list[Puesto]:
        with sesion_de(self._fabrica) as s:
            filas = s.scalars(select(PuestoTabla).where(
                PuestoTabla.codigo_mercado == codigo_mercado, PuestoTabla.eliminado.is_(False),
            ).order_by(PuestoTabla.numero))
            return sorted((_a_puesto(f) for f in filas), key=lambda p: orden_de_numero(p.numero))

    def obtener_por_numero(self, codigo_mercado: str, numero: str) -> Puesto | None:
        with sesion_de(self._fabrica) as s:
            fila = s.scalars(select(PuestoTabla).where(
                PuestoTabla.codigo_mercado == codigo_mercado, PuestoTabla.numero == numero,
                PuestoTabla.eliminado.is_(False),
            )).first()
            return _a_puesto(fila) if fila is not None else None

    def guardar(self, puesto: Puesto) -> Puesto:
        with sesion_de(self._fabrica) as s:
            fila = s.get(PuestoTabla, puesto.id) if puesto.id is not None else None
            if fila is None:
                fila = PuestoTabla()
                s.add(fila)
            fila.codigo_mercado = puesto.codigo_mercado
            fila.numero = puesto.numero
            fila.nombre = puesto.nombre
            fila.rubros = ",".join(r.value for r in puesto.rubros)
            fila.referencia = puesto.referencia
            fila.id_vendedor = puesto.id_vendedor
            fila.foto = puesto.foto
            fila.celular = puesto.celular
            s.flush()
            return _a_puesto(fila)

    def contar_por_mercado(self) -> dict[str, int]:
        with sesion_de(self._fabrica) as s:
            filas = s.execute(
                select(PuestoTabla.codigo_mercado, func.count())
                .where(PuestoTabla.eliminado.is_(False))
                .group_by(PuestoTabla.codigo_mercado)
            ).all()
            return {codigo: n for codigo, n in filas}


class OfertasPostgres:
    def __init__(self, fabrica: sessionmaker[Session]):
        self._fabrica = fabrica

    def obtener(self, id_oferta: int) -> Oferta | None:
        with sesion_de(self._fabrica) as s:
            fila = s.get(OfertaTabla, id_oferta)
            return _a_oferta(fila) if fila is not None and not fila.eliminado else None

    def guardar(self, oferta: Oferta) -> Oferta:
        with sesion_de(self._fabrica) as s:
            fila = s.get(OfertaTabla, oferta.id) if oferta.id is not None else None
            if fila is None:
                fila = OfertaTabla()
                s.add(fila)
            fila.id_vendedor = oferta.id_vendedor
            fila.codigo_mercado = oferta.codigo_mercado
            fila.numero_puesto = oferta.numero_puesto
            fila.codigo_producto = oferta.codigo_producto
            fila.monto = oferta.monto
            fila.presentacion = oferta.presentacion.value
            fila.precio_por_unidad_base = oferta.precio_por_unidad_base
            fila.desde = oferta.desde
            fila.hasta = oferta.hasta
            fila.nota = oferta.nota
            fila.estado = oferta.estado.value
            fila.combo = oferta.combo
            s.flush()
            return _a_oferta(fila)

    def del_vendedor(self, id_vendedor: int) -> list[Oferta]:
        with sesion_de(self._fabrica) as s:
            filas = s.scalars(select(OfertaTabla).where(
                OfertaTabla.id_vendedor == id_vendedor, OfertaTabla.eliminado.is_(False),
            ).order_by(OfertaTabla.desde.desc(), OfertaTabla.id.desc()))
            return [_a_oferta(f) for f in filas]

    def vigentes(self, ahora: datetime, codigo_mercado: str | None = None,
                 codigo_producto: str | None = None) -> list[Oferta]:
        with sesion_de(self._fabrica) as s:
            consulta = select(OfertaTabla).where(
                OfertaTabla.estado == EstadoOferta.ACTIVA.value, OfertaTabla.hasta > ahora,
                OfertaTabla.desde <= ahora, OfertaTabla.eliminado.is_(False),
            )
            if codigo_mercado:
                consulta = consulta.where(OfertaTabla.codigo_mercado == codigo_mercado)
            if codigo_producto:
                consulta = consulta.where(OfertaTabla.codigo_producto == codigo_producto)
            return [_a_oferta(f) for f in s.scalars(consulta.order_by(OfertaTabla.id))]

    def en_revision(self) -> list[Oferta]:
        with sesion_de(self._fabrica) as s:
            filas = s.scalars(select(OfertaTabla).where(
                OfertaTabla.estado == EstadoOferta.EN_REVISION.value, OfertaTabla.eliminado.is_(False),
            ).order_by(OfertaTabla.id))
            return [_a_oferta(f) for f in filas]

    def confirmaciones(self, ids_oferta: list[int]) -> dict[int, list[Confirmacion]]:
        if not ids_oferta:
            return {}
        with sesion_de(self._fabrica) as s:
            filas = s.scalars(select(ConfirmacionOfertaTabla).where(
                ConfirmacionOfertaTabla.id_oferta.in_(ids_oferta), ConfirmacionOfertaTabla.eliminado.is_(False),
            ))
            salida: dict[int, list[Confirmacion]] = {}
            for f in filas:
                salida.setdefault(f.id_oferta, []).append(Confirmacion(
                    id_oferta=f.id_oferta, id_usuario=f.id_usuario, la_vio_asi=f.la_vio_asi,
                    creado_en=_utc(f.modificado_en or f.creado_en),
                ))
            return salida

    def guardar_confirmacion(self, confirmacion: Confirmacion) -> None:
        with sesion_de(self._fabrica) as s:
            fila = s.scalars(select(ConfirmacionOfertaTabla).where(
                ConfirmacionOfertaTabla.id_oferta == confirmacion.id_oferta,
                ConfirmacionOfertaTabla.id_usuario == confirmacion.id_usuario,
            )).first()
            if fila is None:
                fila = ConfirmacionOfertaTabla(id_oferta=confirmacion.id_oferta, id_usuario=confirmacion.id_usuario)
                s.add(fila)
            fila.la_vio_asi = confirmacion.la_vio_asi
            fila.eliminado = False


class InventarioPostgres:
    """El inventario de cada puesto (C137). Quitar es borrado lógico."""

    def __init__(self, fabrica: sessionmaker[Session]):
        self._fabrica = fabrica

    def del_puesto(self, id_puesto: int) -> list[ArticuloInventario]:
        return self.de_puestos([id_puesto]).get(id_puesto, [])

    def de_puestos(self, ids_puestos: list[int]) -> dict[int, list[ArticuloInventario]]:
        if not ids_puestos:
            return {}
        with sesion_de(self._fabrica) as s:
            filas = s.scalars(select(InventarioPuestoTabla).where(
                InventarioPuestoTabla.id_puesto.in_(ids_puestos), InventarioPuestoTabla.eliminado.is_(False),
            ))
            salida: dict[int, list[ArticuloInventario]] = {}
            for f in filas:
                salida.setdefault(f.id_puesto, []).append(_a_articulo(f))
            return salida

    def guardar(self, articulo: ArticuloInventario) -> ArticuloInventario:
        with sesion_de(self._fabrica) as s:
            fila = s.scalars(select(InventarioPuestoTabla).where(
                InventarioPuestoTabla.id_puesto == articulo.id_puesto,
                InventarioPuestoTabla.codigo_producto == articulo.codigo_producto,
                InventarioPuestoTabla.eliminado.is_(False),
            )).first()
            if fila is None:
                fila = InventarioPuestoTabla(id_puesto=articulo.id_puesto, codigo_producto=articulo.codigo_producto)
                s.add(fila)
            fila.monto = articulo.monto
            fila.presentacion = articulo.presentacion.value
            fila.disponibilidad = articulo.disponibilidad.value
            fila.actualizado_en = articulo.actualizado_en or datetime.now(timezone.utc)
            s.flush()
            return _a_articulo(fila)

    def quitar(self, id_puesto: int, codigo_producto: str) -> None:
        with sesion_de(self._fabrica) as s:
            for fila in s.scalars(select(InventarioPuestoTabla).where(
                InventarioPuestoTabla.id_puesto == id_puesto,
                InventarioPuestoTabla.codigo_producto == codigo_producto,
                InventarioPuestoTabla.eliminado.is_(False),
            )):
                fila.eliminado = True
