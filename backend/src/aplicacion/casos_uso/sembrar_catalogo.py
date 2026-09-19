"""
Caso de uso: llevar el catálogo de puntos de venta al repositorio.

Recibe entidades ya construidas. No sabe de dónde salieron: hoy de un CSV,
mañana de un formulario o de un volcado del municipio. Abrir el archivo es
trabajo del adaptador.
"""
from __future__ import annotations
from dataclasses import dataclass, field, replace

from src.aplicacion.puertos.salida import RepositorioMercados
from src.dominio.modelo import Mercado
from src.dominio.servicio.jerarquia import ordenar_padres_primero, validar_jerarquia


@dataclass(frozen=True, slots=True)
class ResumenSiembra:
    insertados: list[str] = field(default_factory=list)
    actualizados: list[str] = field(default_factory=list)
    sin_cambios: list[str] = field(default_factory=list)
    simulado: bool = False

    @property
    def total(self) -> int:
        return len(self.insertados) + len(self.actualizados) + len(self.sin_cambios)


class SembrarCatalogo:
    """
    Es IDEMPOTENTE: correrlo dos veces deja el repositorio igual que
    correrlo una. No borra ni recarga: las observaciones ya apuntan a estos
    códigos y borrarlos las dejaría huérfanas. Inserta lo que falta y
    actualiza lo que cambió, comparando entidad contra entidad.
    """

    def __init__(self, mercados: RepositorioMercados):
        self._mercados = mercados

    def ejecutar(self, puntos: list[Mercado], simular: bool = False) -> ResumenSiembra:
        validar_jerarquia(puntos)
        resumen = ResumenSiembra(simulado=simular)

        # Padres primero: un repositorio con clave foránea rechazaría al
        # hijo cuyo padre todavía no existe.
        for punto in ordenar_padres_primero(puntos):
            existente = self._mercados.obtener(punto.codigo)
            if existente is None:
                resumen.insertados.append(punto.codigo)
            else:
                punto = self._conservar_lo_aprendido(punto, existente)
                if existente == punto:
                    resumen.sin_cambios.append(punto.codigo)
                    continue
                resumen.actualizados.append(punto.codigo)
            if not simular:
                self._mercados.guardar(punto)
        return resumen

    @staticmethod
    def _conservar_lo_aprendido(punto: Mercado, existente: Mercado) -> Mercado:
        """
        El catálogo describe el lugar, no su comportamiento de precios. El
        factor_mercado se aprende del levantamiento de campo y no viene en
        el catálogo: re-sembrar no debe pisarlo con el valor por defecto.
        """
        return replace(punto, factor_mercado=existente.factor_mercado)
