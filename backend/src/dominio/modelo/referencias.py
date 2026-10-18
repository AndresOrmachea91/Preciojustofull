"""
Los catálogos de referencia descritos para las personas: qué es cada rol,
cada permiso y cada fuente de precios.

El dominio decide qué roles, permisos y fuentes existen (usuario.py,
observacion.py); acá está cómo se explican. La persistencia los copia a sus
tablas y la API los muestra al administrador: los dos leen de este lugar.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.dominio.modelo.observacion import Fuente
from src.dominio.modelo.usuario import PERMISOS_POR_ROL, Permiso, Rol

NOMBRE_Y_DESCRIPCION_ROL: dict[Rol, tuple[str, str]] = {
    Rol.USUARIO: ("Usuario", "Consulta precios y el mapa, arma listas de compras y reporta precios."),
    Rol.VENDEDOR: ("Vendedor", "Lo anterior, y publica los precios de su puesto o tienda."),
    Rol.ADMINISTRADOR: ("Administrador", "Gestiona cuentas, catálogo de mercados y productos, y valida reportes."),
}

DESCRIPCION_PERMISO: dict[Permiso, str] = {
    Permiso.REPORTAR_PRECIO: "Reportar un precio visto en un mercado (queda pendiente de revisión).",
    Permiso.GESTIONAR_LISTAS: "Crear, editar, borrar y cotizar listas de compras propias.",
    Permiso.PUBLICAR_PRECIO_PROPIO: "Publicar el precio de su propio puesto, marcado como declarado.",
    Permiso.GESTIONAR_USUARIOS: "Crear cuentas, cambiar rol y estado, asignar puesto, eliminar (lógico).",
    Permiso.GESTIONAR_CATALOGO: "Registrar y editar mercados, tiendas y productos.",
    Permiso.VALIDAR_REPORTES: "Aprobar o rechazar los reportes de precio.",
    Permiso.VER_AUDITORIA: "Ver quién creó, modificó o eliminó cada registro.",
    Permiso.IMPORTAR_CAMPO: "Cargar la planilla CSV del levantamiento de campo (fuente campo).",
    Permiso.VER_SALUD: "Ver el estado del sistema: recolección, respaldos y cobertura de los datos.",
}

_URL_SIIP = "https://siip.produccion.gob.bo"

# (nombre, descripción, la recoge el sistema solo, dirección)
DESCRIPCION_FUENTE: dict[Fuente, tuple[str, str, bool, str | None]] = {
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


@dataclass(frozen=True, slots=True)
class PermisoDescrito:
    codigo: str
    descripcion: str


@dataclass(frozen=True, slots=True)
class RolDescrito:
    codigo: str
    nombre: str
    descripcion: str
    permisos: tuple[PermisoDescrito, ...]


@dataclass(frozen=True, slots=True)
class FuenteDescrita:
    codigo: str
    nombre: str
    descripcion: str
    confianza_base: str
    deriva_de: str | None
    automatica: bool
    url: str | None


def roles_descritos() -> list[RolDescrito]:
    return [
        RolDescrito(
            codigo=rol.value, nombre=nombre, descripcion=descripcion,
            permisos=tuple(PermisoDescrito(p.value, DESCRIPCION_PERMISO[p])
                           for p in Permiso if p in PERMISOS_POR_ROL[rol]),
        )
        for rol, (nombre, descripcion) in NOMBRE_Y_DESCRIPCION_ROL.items()
    ]


def fuentes_descritas() -> list[FuenteDescrita]:
    return [
        FuenteDescrita(
            codigo=f.value, nombre=nombre, descripcion=descripcion,
            confianza_base=f.confianza_base.name.lower(),
            deriva_de=f.deriva_de.value if f.deriva_de else None,
            automatica=automatica, url=url,
        )
        for f, (nombre, descripcion, automatica, url) in DESCRIPCION_FUENTE.items()
    ]
