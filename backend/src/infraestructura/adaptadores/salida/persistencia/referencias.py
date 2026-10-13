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
from src.infraestructura.adaptadores.salida.persistencia.tablas import (
    FuenteTabla, PermisoTabla, RolPermisoTabla, RolTabla,
)

_ROLES = {
    Rol.USUARIO: ("Usuario", "Consulta precios y el mapa, arma listas de compras y reporta precios."),
    Rol.VENDEDOR: ("Vendedor", "Lo anterior, y publica los precios de su puesto o tienda."),
    Rol.ADMINISTRADOR: ("Administrador", "Gestiona cuentas, catálogo de mercados y productos, y valida reportes."),
}

_PERMISOS = {
    Permiso.REPORTAR_PRECIO: "Reportar un precio visto en un mercado (queda pendiente de revisión).",
    Permiso.GESTIONAR_LISTAS: "Crear, editar, borrar y cotizar listas de compras propias.",
    Permiso.PUBLICAR_PRECIO_PROPIO: "Publicar el precio de su propio puesto, marcado como declarado.",
    Permiso.GESTIONAR_USUARIOS: "Crear cuentas, cambiar rol y estado, asignar puesto, eliminar (lógico).",
    Permiso.GESTIONAR_CATALOGO: "Registrar y editar mercados, tiendas y productos.",
    Permiso.VALIDAR_REPORTES: "Aprobar o rechazar los reportes de precio.",
    Permiso.VER_AUDITORIA: "Ver quién creó, modificó o eliminó cada registro.",
}

_URL_SIIP = "https://siip.produccion.gob.bo"
_FUENTES = {
    Fuente.SIIP_IPC: ("SIIP - precios al consumidor (IPC)",
                      "Precio promedio mensual al consumidor final por ciudad, del Sistema Integrado "
                      "de Información Productiva (Ministerio de Desarrollo Productivo).", True, _URL_SIIP),
    Fuente.SIIP_DIARIO: ("SIIP - precios diarios mayoristas",
                         "Precio mayorista diario por ciudad del mismo SIIP.", True, _URL_SIIP),
    Fuente.PRENSA: ("Prensa", "Diarios que reproducen el boletín del SIIP: no es evidencia nueva.", False, None),
    Fuente.MEDIOS: ("Medios propios", "Reportes audiovisuales propios de un medio.", False, None),
    Fuente.CIUDADANO: ("Reporte ciudadano",
                       "Precio que reporta un usuario; entra al motor cuando el administrador lo aprueba.",
                       False, None),
    Fuente.CAMPO: ("Levantamiento de campo", "Cotización verificada en el puesto con la ficha de campo.",
                   False, None),
    Fuente.VENDEDOR: ("Declarado por el vendedor", "Precio que el vendedor publica sobre su propio puesto.",
                      False, None),
}


def sincronizar_referencias(s: Session) -> None:
    for rol, (nombre, descripcion) in _ROLES.items():
        s.merge(RolTabla(codigo=rol.value, nombre=nombre, descripcion=descripcion, eliminado=False))
    for permiso, descripcion in _PERMISOS.items():
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
    for fuente in sorted(_FUENTES, key=lambda f: f.deriva_de is not None):
        nombre, descripcion, automatica, url = _FUENTES[fuente]
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
