"""
"¿Lo viste así?" (C133): un comprador confirma o desmiente una oferta en
un toque.

- Una respuesta por persona y oferta: si cambia de opinión, vale la última.
- El casero no puede confirmar su propia oferta.
- Dos desmentidos de personas DISTINTAS la pausan (en revisión) hasta que
  un administrador la mire. No se borra: si era verdad, se reactiva.

La confirmación no entra al motor de fusión, igual que la oferta: es sobre
una rebaja que eligió el casero, no sobre el precio del mercado.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from src.aplicacion.casos_uso.cuentas.permisos import exigir
from src.aplicacion.puertos.salida import RepositorioOfertas
from src.dominio.excepciones import OfertaNoEncontrada, OfertaNoPermitida
from src.dominio.modelo import Confirmacion, Permiso, Usuario
from src.dominio.modelo.oferta import hay_que_pausar


@dataclass(frozen=True, slots=True)
class ResultadoConfirmacion:
    confirmaron: int
    desmintieron: int
    pausada: bool


class ConfirmarOferta:
    def __init__(self, ofertas: RepositorioOfertas, ahora: Callable[[], datetime] | None = None):
        self._ofertas = ofertas
        self._ahora = ahora or (lambda: datetime.now(timezone.utc))

    def ejecutar(self, comprador: Usuario, id_oferta: int, la_vio_asi: bool) -> ResultadoConfirmacion:
        exigir(comprador, Permiso.REPORTAR_PRECIO)
        ahora = self._ahora()
        oferta = self._ofertas.obtener(id_oferta)
        if oferta is None or not oferta.vigente(ahora):
            raise OfertaNoEncontrada(id_oferta)
        if oferta.id_vendedor == comprador.id:
            raise OfertaNoPermitida("No puede confirmar su propia oferta")

        self._ofertas.guardar_confirmacion(Confirmacion(
            id_oferta=id_oferta, id_usuario=comprador.id, la_vio_asi=la_vio_asi, creado_en=ahora,
        ))
        dichas = self._ofertas.confirmaciones([id_oferta]).get(id_oferta, [])
        pausada = hay_que_pausar(dichas)
        if pausada:
            self._ofertas.guardar(oferta.a_revision())
        return ResultadoConfirmacion(
            confirmaron=sum(c.la_vio_asi for c in dichas),
            desmintieron=sum(not c.la_vio_asi for c in dichas),
            pausada=pausada,
        )
