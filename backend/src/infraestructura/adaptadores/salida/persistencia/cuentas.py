"""
Persistencia de usuarios y reportes sobre SQLAlchemy.

Implementa RepositorioUsuarios y RepositorioReportes. Se verifica con la
misma prueba de contrato que el adaptador en memoria
(`tests/test_contrato_cuentas.py`).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from src.infraestructura.adaptadores.salida.persistencia.sesion import sesion_de
from src.infraestructura.adaptadores.salida.persistencia.tablas import ReporteTabla, UsuarioTabla
from src.dominio.modelo import Auditoria, EstadoReporte, Reporte, Rol, Usuario


def _con_zona(momento: datetime | None) -> datetime | None:
    # SQLite devuelve las fechas sin zona horaria aunque la columna la
    # declare; PostgreSQL sí la conserva. Se guardan siempre en UTC.
    if momento is not None and momento.tzinfo is None:
        return momento.replace(tzinfo=timezone.utc)
    return momento


def _a_usuario(f: UsuarioTabla) -> Usuario:
    return Usuario(
        id=f.id,
        correo=f.correo,
        nombre=f.nombre,
        rol=Rol(f.rol),
        hash_contrasena=f.hash_contrasena,
        activo=bool(f.activo),
        creado_en=_con_zona(f.creado_en),
        codigo_punto_venta=f.codigo_punto_venta,
        auditoria=Auditoria(
            creado_en=_con_zona(f.creado_en),
            creado_por=f.creado_por,
            modificado_en=_con_zona(f.modificado_en),
            modificado_por=f.modificado_por,
            eliminado=bool(f.eliminado),
        ),
    )


def _a_reporte(f: ReporteTabla) -> Reporte:
    return Reporte(
        id=f.id,
        codigo_producto=f.codigo_producto,
        codigo_mercado=f.codigo_mercado,
        monto=f.monto,
        unidad=f.unidad,
        id_autor=f.id_autor,
        creado_en=_con_zona(f.creado_en),
        estado=EstadoReporte(f.estado),
        id_revisor=f.id_revisor,
        revisado_en=_con_zona(f.revisado_en),
        motivo_rechazo=f.motivo_rechazo,
    )


class _Base:
    def __init__(self, fabrica: sessionmaker[Session]):
        self._fabrica = fabrica


class UsuariosPostgres(_Base):
    def obtener(self, id_usuario: int) -> Usuario | None:
        with sesion_de(self._fabrica) as s:
            fila = s.get(UsuarioTabla, id_usuario)
            return _a_usuario(fila) if fila is not None and not fila.eliminado else None

    def obtener_por_correo(self, correo: str) -> Usuario | None:
        with sesion_de(self._fabrica) as s:
            fila = s.scalars(select(UsuarioTabla).where(
                UsuarioTabla.correo == correo, UsuarioTabla.eliminado.is_(False))).first()
            return _a_usuario(fila) if fila else None

    def listar(self, incluir_eliminados: bool = False) -> list[Usuario]:
        consulta = select(UsuarioTabla).order_by(UsuarioTabla.id)
        if not incluir_eliminados:
            consulta = consulta.where(UsuarioTabla.eliminado.is_(False))
        with sesion_de(self._fabrica) as s:
            return [_a_usuario(f) for f in s.scalars(consulta)]

    def eliminar(self, id_usuario: int) -> None:
        # Nunca un DELETE: se marca, y modificado_por/en dicen quién y cuándo.
        with sesion_de(self._fabrica) as s:
            fila = s.get(UsuarioTabla, id_usuario)
            if fila is not None:
                fila.eliminado = True

    def guardar(self, usuario: Usuario) -> Usuario:
        with sesion_de(self._fabrica) as s:
            fila = s.get(UsuarioTabla, usuario.id) if usuario.id is not None else None
            if fila is not None and fila.eliminado:
                fila = None
            if fila is None:
                fila = UsuarioTabla(creado_en=usuario.creado_en)
                s.add(fila)
            fila.correo = usuario.correo
            fila.nombre = usuario.nombre
            fila.rol = usuario.rol.value
            fila.hash_contrasena = usuario.hash_contrasena
            fila.activo = usuario.activo
            fila.codigo_punto_venta = usuario.codigo_punto_venta
            s.flush()
            return _a_usuario(fila)

    def contar_administradores_activos(self) -> int:
        with sesion_de(self._fabrica) as s:
            return s.scalar(
                select(func.count()).select_from(UsuarioTabla).where(
                    UsuarioTabla.rol == Rol.ADMINISTRADOR.value, UsuarioTabla.activo.is_(True),
                    UsuarioTabla.eliminado.is_(False),
                )
            ) or 0


class ReportesPostgres(_Base):
    def obtener(self, id_reporte: int) -> Reporte | None:
        with sesion_de(self._fabrica) as s:
            fila = s.get(ReporteTabla, id_reporte)
            return _a_reporte(fila) if fila is not None and not fila.eliminado else None

    def listar(self, estado: EstadoReporte | None = None) -> list[Reporte]:
        consulta = select(ReporteTabla).where(ReporteTabla.eliminado.is_(False)).order_by(ReporteTabla.creado_en)
        if estado is not None:
            consulta = consulta.where(ReporteTabla.estado == estado.value)
        with sesion_de(self._fabrica) as s:
            return [_a_reporte(f) for f in s.scalars(consulta)]

    def listar_de_autor(self, id_autor: int) -> list[Reporte]:
        consulta = (
            select(ReporteTabla)
            .where(ReporteTabla.id_autor == id_autor, ReporteTabla.eliminado.is_(False))
            .order_by(ReporteTabla.creado_en.desc(), ReporteTabla.id.desc())
        )
        with sesion_de(self._fabrica) as s:
            return [_a_reporte(f) for f in s.scalars(consulta)]

    def guardar(self, reporte: Reporte) -> Reporte:
        with sesion_de(self._fabrica) as s:
            fila = s.get(ReporteTabla, reporte.id) if reporte.id is not None else None
            if fila is None:
                # La fecha de creación se fija UNA vez: es auditoría y no se modifica.
                fila = ReporteTabla(creado_en=reporte.creado_en)
                s.add(fila)
            fila.codigo_producto = reporte.codigo_producto
            fila.codigo_mercado = reporte.codigo_mercado
            fila.monto = reporte.monto
            fila.unidad = reporte.unidad
            fila.id_autor = reporte.id_autor
            fila.estado = reporte.estado.value
            fila.id_revisor = reporte.id_revisor
            fila.revisado_en = reporte.revisado_en
            fila.motivo_rechazo = reporte.motivo_rechazo
            s.flush()
            return _a_reporte(fila)
