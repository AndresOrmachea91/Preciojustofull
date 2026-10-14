"""
Sincroniza los catálogos de referencia (rol, permiso, rol_permiso, fuente)
con el dominio. Es idempotente y corre en cada arranque desde crear_esquema.

El dominio es la fuente de verdad: si a una fila le cambiaron la
descripción, se corrige; si el dominio dejó de tener un valor, la fila se
marca eliminada (nunca se borra, por auditoría).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.dominio.modelo import Fuente, PERMISOS_POR_ROL, Permiso, Rol
from src.dominio.modelo.referencias import (
    DESCRIPCION_FUENTE, DESCRIPCION_PERMISO, NOMBRE_Y_DESCRIPCION_ROL,
)
from src.infraestructura.adaptadores.salida.persistencia.tablas import (
    FuenteTabla, PermisoTabla, RolPermisoTabla, RolTabla,
)

def sincronizar_referencias(s: Session) -> None:
    for rol, (nombre, descripcion) in NOMBRE_Y_DESCRIPCION_ROL.items():
        s.merge(RolTabla(codigo=rol.value, nombre=nombre, descripcion=descripcion, eliminado=False))
    for permiso, descripcion in DESCRIPCION_PERMISO.items():
        s.merge(PermisoTabla(codigo=permiso.value, descripcion=descripcion, eliminado=False))
    s.flush()

    vigentes = {(r.value, p.value) for r, permisos in PERMISOS_POR_ROL.items() for p in permisos}
    for fila in s.query(RolPermisoTabla):
        par = (fila.codigo_rol, fila.codigo_permiso)
        if fila.eliminado == (par in vigentes):
            fila.eliminado = par not in vigentes
        vigentes.discard(par)
    for codigo_rol, codigo_permiso in vigentes:
        s.add(RolPermisoTabla(codigo_rol=codigo_rol, codigo_permiso=codigo_permiso))

    # Primero las fuentes sin derivación: deriva_de apunta a otra fila.
    for fuente in sorted(DESCRIPCION_FUENTE, key=lambda f: f.deriva_de is not None):
        nombre, descripcion, automatica, url = DESCRIPCION_FUENTE[fuente]
        s.merge(FuenteTabla(
            codigo=fuente.value, nombre=nombre, descripcion=descripcion,
            confianza_base=fuente.confianza_base.name.lower(),
            deriva_de=fuente.deriva_de.value if fuente.deriva_de else None,
            automatica=automatica, url=url, eliminado=False,
        ))
        s.flush()

    for tabla, codigos in ((RolTabla, {r.value for r in Rol}), (PermisoTabla, {p.value for p in Permiso}),
                           (FuenteTabla, {f.value for f in Fuente})):
        for fila in s.query(tabla).filter(tabla.codigo.not_in(codigos), tabla.eliminado.is_(False)):
            fila.eliminado = True
