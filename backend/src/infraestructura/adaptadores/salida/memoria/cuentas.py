"""
Usuarios y reportes en memoria: el mismo puerto que el adaptador de
SQLAlchemy, para levantar la API y correr las pruebas sin base de datos.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from src.dominio.modelo import Auditoria, EstadoReporte, Reporte, Rol, Usuario
from src.infraestructura.adaptadores.salida.persistencia.auditable import actor_actual


def _modificada(auditoria: Auditoria, **cambios) -> Auditoria:
    return replace(auditoria, modificado_en=datetime.now(timezone.utc),
                   modificado_por=actor_actual.get(), **cambios)


class UsuariosEnMemoria:
    def __init__(self):
        self._datos: dict[int, Usuario] = {}
        # Lo eliminado se aparta, no se borra: igual que la columna eliminado.
        self._eliminados: dict[int, Usuario] = {}
        self._siguiente = 1

    def obtener(self, id_usuario: int) -> Usuario | None:
        return self._datos.get(id_usuario)

    def obtener_por_correo(self, correo: str) -> Usuario | None:
        return next((u for u in self._datos.values() if u.correo == correo), None)

    def listar(self, incluir_eliminados: bool = False) -> list[Usuario]:
        todos = [*self._datos.values(), *(self._eliminados.values() if incluir_eliminados else [])]
        return sorted(todos, key=lambda u: u.id)

    def eliminar(self, id_usuario: int) -> None:
        usuario = self._datos.pop(id_usuario, None)
        if usuario is not None:
            self._eliminados[id_usuario] = replace(usuario, auditoria=_modificada(usuario.auditoria, eliminado=True))

    def guardar(self, usuario: Usuario) -> Usuario:
        # La auditoría la pone el repositorio, igual que Auditable en la base.
        anterior = self._datos.get(usuario.id) if usuario.id is not None else None
        if anterior is None:
            usuario = replace(usuario, id=self._siguiente,
                              auditoria=Auditoria(usuario.creado_en, actor_actual.get()))
            self._siguiente += 1
        else:
            usuario = replace(usuario, auditoria=_modificada(anterior.auditoria))
        self._datos[usuario.id] = usuario
        return usuario

    def contar_administradores_activos(self) -> int:
        return sum(1 for u in self._datos.values() if u.activo and u.rol is Rol.ADMINISTRADOR)


class ReportesEnMemoria:
    def __init__(self):
        self._datos: dict[int, Reporte] = {}
        self._siguiente = 1

    def obtener(self, id_reporte: int) -> Reporte | None:
        return self._datos.get(id_reporte)

    def listar(self, estado: EstadoReporte | None = None) -> list[Reporte]:
        todos = sorted(self._datos.values(), key=lambda r: r.creado_en)
        return todos if estado is None else [r for r in todos if r.estado is estado]

    def listar_de_autor(self, id_autor: int) -> list[Reporte]:
        propios = [r for r in self._datos.values() if r.id_autor == id_autor]
        return sorted(propios, key=lambda r: (r.creado_en, r.id), reverse=True)

    def guardar(self, reporte: Reporte) -> Reporte:
        if reporte.id is None:
            reporte = replace(reporte, id=self._siguiente)
            self._siguiente += 1
        self._datos[reporte.id] = reporte
        return reporte
