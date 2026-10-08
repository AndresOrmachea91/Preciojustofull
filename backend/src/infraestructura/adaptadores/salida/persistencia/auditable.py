"""
Auditoría: las 5 columnas que TODAS las tablas heredan.

Es el equivalente en SQLAlchemy de esto en Spring Boot / JPA:

    @MappedSuperclass
    public abstract class Auditable {
        @Column(updatable = false) private LocalDateTime fechaCreacion;
        @Column(updatable = false) private String creadoPor;
        private LocalDateTime fechaModificacion;
        private String modificadoPor;
        private boolean eliminado;
        @PrePersist void antesDeCrear() { ... }
        @PreUpdate  void antesDeModificar() { ... }
    }
    public class Usuario extends Auditable { ... }

Acá:
    - `Auditable` es un *mixin* declarativo: no es una tabla, sus columnas se
      copian a cada tabla que lo hereda (`class UsuarioTabla(Base, Auditable)`).
    - `default=` cumple el papel de @PrePersist y `onupdate=` el de
      @PreUpdate. A diferencia de un evento del ORM, también se aplican a los
      INSERT/UPDATE masivos (el recolector guarda miles de filas así).
    - `creado_en` y `creado_por` no se pueden cambiar después de creados: lo
      vigila el evento `before_update` de abajo (el `updatable = false` de JPA).
    - `eliminado` es el borrado LÓGICO: una fila auditada no se borra nunca;
      los repositorios simplemente no la devuelven.

¿Quién es "el usuario" en cada cambio? `actor_actual`, una ContextVar: lo
mismo que el SecurityContextHolder que lee AuditorAware en Spring. La API la
llena con el correo de la sesión en cada petición; los comandos de consola
con su nombre ("recolector-automatico", "siembra"); por defecto, "sistema".

Por qué columnas en cada tabla y no una tabla única de logs: una tabla de
logs aparte se puede alterar sin tocar el dato, crece sin control y es un
blanco atractivo; las columnas viajan con la fila, en la misma transacción.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, String, event, inspect
from sqlalchemy.orm import declarative_mixin

actor_actual: ContextVar[str] = ContextVar("actor_actual", default="sistema")

COLUMNAS_AUDITORIA = ("creado_en", "creado_por", "modificado_en", "modificado_por", "eliminado")
_INMUTABLES = ("creado_en", "creado_por")


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _actor() -> str:
    return actor_actual.get()


@contextmanager
def como_actor(nombre: str):
    """Todo lo que se guarde dentro del bloque queda a nombre de `nombre`."""
    marca = actor_actual.set(nombre)
    try:
        yield
    finally:
        actor_actual.reset(marca)


@declarative_mixin
class Auditable:
    creado_en = Column(DateTime(timezone=True), nullable=False, default=_ahora)
    creado_por = Column(String(255), nullable=False, default=_actor)
    modificado_en = Column(DateTime(timezone=True), nullable=True, onupdate=_ahora)
    modificado_por = Column(String(255), nullable=True, onupdate=_actor)
    eliminado = Column(Boolean, nullable=False, default=False)


@event.listens_for(Auditable, "before_update", propagate=True)
def _creacion_inmutable(_mapper, _conexion, fila) -> None:
    estado = inspect(fila)
    for campo in _INMUTABLES:
        historia = estado.attrs[campo].history
        if historia.deleted and historia.added and historia.deleted[0] is not None:
            raise ValueError(f"{campo} no se puede modificar: es parte de la auditoría")
