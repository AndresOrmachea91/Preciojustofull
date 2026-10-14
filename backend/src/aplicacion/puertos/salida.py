"""
Puertos de SALIDA: lo que el sistema necesita del mundo exterior.

Son interfaces (Protocol). El dominio y la aplicación dependen de ellas;
los adaptadores las implementan. Esta es la inversión de dependencias que
sostiene toda la arquitectura.

Nótese que FuentePrecios es UNA sola interfaz: SIIP mayorista, SIIP IPC,
medios y reportes ciudadanos son cuatro adaptadores del mismo puerto. Por
eso perder una fuente no obliga a tocar nada más.
"""
from __future__ import annotations
from typing import Protocol, runtime_checkable

from src.dominio.modelo import (
    EstadoReporte, Fuente, ListaCompras, Mercado, Observacion, Producto, RegistroAuditado, Reporte, Usuario,
)
from src.dominio.valor import Periodo


# --- catálogo y observaciones: lectura y escritura por separado ----------
# Segregación de interfaces: cada caso de uso declara SOLO lo que usa. Los
# que publican precios (consultar, comparar, canasta) dependen de los
# lectores y no pueden escribir ni por descuido; solo la siembra y la
# validación de reportes reciben un escritor. Los Repositorio* reúnen
# ambos para los adaptadores, que implementan el paquete completo.

@runtime_checkable
class LectorProductos(Protocol):
    def obtener(self, codigo: str) -> Producto | None: ...
    def listar(self) -> list[Producto]: ...


@runtime_checkable
class EscritorProductos(Protocol):
    def guardar(self, producto: Producto) -> None: ...
    def eliminar(self, codigo: str) -> None:
        """Borrado LÓGICO: la fila queda (auditoría), pero ya no se lista ni se obtiene."""
        ...


@runtime_checkable
class RepositorioProductos(LectorProductos, EscritorProductos, Protocol):
    pass


@runtime_checkable
class LectorMercados(Protocol):
    def obtener(self, codigo: str) -> Mercado | None: ...
    def listar(self, zona: str | None = None) -> list[Mercado]: ...


@runtime_checkable
class EscritorMercados(Protocol):
    def guardar(self, mercado: Mercado) -> None: ...
    def eliminar(self, codigo: str) -> None:
        """Borrado LÓGICO, igual que en productos."""
        ...


@runtime_checkable
class RepositorioMercados(LectorMercados, EscritorMercados, Protocol):
    pass


@runtime_checkable
class LectorObservaciones(Protocol):
    def buscar(
        self,
        codigo_producto: str,
        codigo_mercado: str | None = None,
        periodo: Periodo | None = None,
        ciudad: str | None = None,
    ) -> list[Observacion]: ...


@runtime_checkable
class EscritorObservaciones(Protocol):
    def guardar_varias(self, observaciones: list[Observacion]) -> int: ...


@runtime_checkable
class RepositorioObservaciones(LectorObservaciones, EscritorObservaciones, Protocol):
    pass


@runtime_checkable
class FuentePrecios(Protocol):
    """Un puerto, muchos adaptadores. El núcleo no sabe cuál está usando."""

    @property
    def nombre(self) -> str: ...
    def esta_disponible(self) -> bool: ...
    def recolectar(self, codigo_producto: str) -> list[Observacion]: ...


@runtime_checkable
class ServicioPrediccion(Protocol):
    def predecir(
        self, codigo_producto: str, codigo_mercado: str, dias_adelante: int
    ) -> tuple[float, float]:
        """Devuelve (valor estimado, amplitud del intervalo)."""
        ...



# --- usuarios, sesiones y reportes ---------------------------------------
# Puertos chicos, uno por responsabilidad: quien solo verifica sesiones no
# tiene por qué depender de cómo se cifra una contraseña.

@runtime_checkable
class RepositorioUsuarios(Protocol):
    def obtener(self, id_usuario: int) -> Usuario | None: ...
    def obtener_por_correo(self, correo: str) -> Usuario | None: ...
    def listar(self, incluir_eliminados: bool = False) -> list[Usuario]:
        """Por defecto, solo los vigentes: lo eliminado no se lista."""
        ...
    def guardar(self, usuario: Usuario) -> Usuario:
        """Inserta si no tiene id, actualiza si lo tiene. Devuelve el usuario con id."""
        ...
    def eliminar(self, id_usuario: int) -> None:
        """Eliminado LÓGICO: la fila queda, marcada; ya no se obtiene ni ingresa."""
        ...
    def contar_administradores_activos(self) -> int: ...


@runtime_checkable
class RepositorioReportes(Protocol):
    def obtener(self, id_reporte: int) -> Reporte | None: ...
    def listar(self, estado: EstadoReporte | None = None) -> list[Reporte]: ...
    def guardar(self, reporte: Reporte) -> Reporte: ...


@runtime_checkable
class CifradorContrasenas(Protocol):
    def cifrar(self, contrasena: str) -> str: ...
    def verificar(self, contrasena: str, hash_guardado: str) -> bool: ...


@runtime_checkable
class EmisorTokens(Protocol):
    def emitir(self, usuario: Usuario) -> str: ...
    def leer(self, token: str) -> int | None:
        """Id del usuario del token, o None si es inválido o venció."""
        ...


# --- usuario y vendedor -------------------------------------------------------

@runtime_checkable
class LectorReportesDeAutor(Protocol):
    def listar_de_autor(self, id_autor: int) -> list[Reporte]:
        """Los reportes de una persona, del más nuevo al más viejo."""
        ...


@runtime_checkable
class LectorPublicacionesPuntoVenta(Protocol):
    def publicadas_en(self, codigo_mercado: str, fuente: Fuente) -> list[Observacion]:
        """Lo que una fuente publicó sobre un punto de venta, del más nuevo al más viejo."""
        ...


@runtime_checkable
class RepositorioListas(Protocol):
    def obtener(self, id_lista: int) -> ListaCompras | None: ...
    def listar_de(self, id_usuario: int) -> list[ListaCompras]: ...
    def guardar(self, lista: ListaCompras) -> ListaCompras: ...
    def eliminar(self, id_lista: int) -> None:
        """Borrado LÓGICO, como todo lo auditado."""
        ...


@runtime_checkable
class LectorAuditoria(Protocol):
    """Los 5 campos de auditoría de todas las tablas, para que el administrador los consulte."""

    def tablas(self) -> list[str]: ...

    def recientes(self, tabla: str | None, limite: int) -> list[RegistroAuditado]:
        """Las filas con el cambio más reciente primero; de una tabla o de todas."""
        ...
