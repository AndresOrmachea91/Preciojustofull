"""
El administrador consulta la auditoría: quién creó, modificó o eliminó cada
registro y cuándo. Solo lectura: los 5 campos los escribe la persistencia
(Auditable), nunca una persona.
"""
from __future__ import annotations

from src.aplicacion.casos_uso.cuentas.permisos import exigir
from src.aplicacion.puertos.salida import LectorAuditoria
from src.dominio.excepciones import DatoInvalido
from src.dominio.modelo import Permiso, RegistroAuditado, Usuario
from src.dominio.modelo.referencias import FuenteDescrita, RolDescrito, fuentes_descritas, roles_descritos

LIMITE_MAXIMO = 200


class VerAuditoria:
    def __init__(self, lector: LectorAuditoria):
        self._lector = lector

    def tablas(self, actor: Usuario) -> list[str]:
        exigir(actor, Permiso.VER_AUDITORIA)
        return self._lector.tablas()

    def recientes(self, actor: Usuario, tabla: str | None = None, limite: int = 50) -> list[RegistroAuditado]:
        exigir(actor, Permiso.VER_AUDITORIA)
        if tabla is not None and tabla not in self._lector.tablas():
            raise DatoInvalido(f"No existe la tabla {tabla}")
        limite = max(1, min(limite, LIMITE_MAXIMO))
        return sorted(self._lector.recientes(tabla, limite), key=lambda r: r.ultimo_cambio, reverse=True)[:limite]


class ConsultarReferencias:
    """Qué roles hay, qué puede cada uno y de dónde salen los precios. Lo decide el dominio."""

    def roles(self, actor: Usuario) -> list[RolDescrito]:
        exigir(actor, Permiso.VER_AUDITORIA)
        return roles_descritos()

    def fuentes(self, actor: Usuario) -> list[FuenteDescrita]:
        exigir(actor, Permiso.VER_AUDITORIA)
        return fuentes_descritas()
