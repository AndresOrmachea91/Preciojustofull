"""
Usuarios y reportes en memoria: el mismo puerto que el adaptador de
SQLAlchemy, para levantar la API y correr las pruebas sin base de datos.
"""
from __future__ import annotations

from dataclasses import replace

from src.dominio.modelo import EstadoReporte, Reporte, Rol, Usuario


class UsuariosEnMemoria:
    def __init__(self):
        self._datos: dict[int, Usuario] = {}
        self._siguiente = 1

    def obtener(self, id_usuario: int) -> Usuario | None:
        return self._datos.get(id_usuario)

    def obtener_por_correo(self, correo: str) -> Usuario | None:
        return next((u for u in self._datos.values() if u.correo == correo), None)

    def listar(self) -> list[Usuario]:
        return sorted(self._datos.values(), key=lambda u: u.id)

    def guardar(self, usuario: Usuario) -> Usuario:
        if usuario.id is None:
            usuario = replace(usuario, id=self._siguiente)
            self._siguiente += 1
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
