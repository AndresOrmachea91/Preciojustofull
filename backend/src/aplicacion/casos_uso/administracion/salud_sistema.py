"""
Panel de salud (C132): ¿está vivo el sistema y se puede confiar en sus datos?

Junta en una pantalla lo que antes había que ir a mirar a mano: si la
recolección del SIIP corrió y trajo datos nuevos, si el último respaldo se
pudo restaurar de verdad (un respaldo que nunca se probó no es respaldo),
y qué parte de los pares mercado-producto tiene un precio OBSERVADO
reciente, que es lo que separa una medición de una estimación.

Cada punto sale con un estado: "bien", "revisar" o "sin_datos". Las
reglas viven acá, no en la pantalla.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from src.aplicacion.casos_uso.cuentas.permisos import exigir
from src.aplicacion.puertos.salida import LectorRespaldos, LectorSalud
from src.dominio.modelo import DatosDeFuente, EstadoRespaldo, Permiso, UltimaRecoleccion, Usuario

VENTANA_COBERTURA_DIAS = 30
# El recolector corre una vez al día: más de 36 h sin éxito es una falla.
RECOLECCION_VIEJA = timedelta(hours=36)
RESPALDO_VIEJO = timedelta(hours=36)


@dataclass(frozen=True, slots=True)
class Punto:
    nombre: str
    estado: str          # "bien" | "revisar" | "sin_datos"
    detalle: str


@dataclass(slots=True)
class SaludSistema:
    puntos: list[Punto] = field(default_factory=list)
    fuentes: list[DatosDeFuente] = field(default_factory=list)
    recolecciones: list[UltimaRecoleccion] = field(default_factory=list)
    respaldo: EstadoRespaldo | None = None
    cobertura_observada: float | None = None
    ventana_dias: int = VENTANA_COBERTURA_DIAS

    @property
    def estado_general(self) -> str:
        estados = {p.estado for p in self.puntos}
        return "revisar" if "revisar" in estados else ("bien" if estados == {"bien"} else "sin_datos")


class VerSaludSistema:
    def __init__(self, salud: LectorSalud, respaldos: LectorRespaldos):
        self._salud = salud
        self._respaldos = respaldos

    def ejecutar(self, actor: Usuario, hoy: date, ahora: datetime | None = None) -> SaludSistema:
        exigir(actor, Permiso.VER_SALUD)
        ahora = ahora or datetime.now(timezone.utc)
        datos = self._salud.leer(hoy - timedelta(days=VENTANA_COBERTURA_DIAS))
        respaldo = self._respaldos.ultimo()
        cobertura = datos.pares_observados / datos.pares_posibles if datos.pares_posibles else None
        return SaludSistema(
            puntos=[
                _recoleccion(datos.recolecciones, ahora),
                _respaldo(respaldo, ahora),
                _cobertura(datos.pares_observados, datos.pares_posibles),
            ],
            fuentes=datos.fuentes,
            recolecciones=datos.recolecciones,
            respaldo=respaldo,
            cobertura_observada=None if cobertura is None else round(cobertura, 4),
        )


def _recoleccion(recolecciones: list[UltimaRecoleccion], ahora: datetime) -> Punto:
    if not recolecciones:
        return Punto("Recolección del SIIP", "sin_datos", "Todavía no hay intentos registrados.")
    malas = [r for r in recolecciones if not r.exito or ahora - r.ocurrido_en > RECOLECCION_VIEJA]
    nuevos = sum(r.hechos_nuevos_24h for r in recolecciones)
    if malas:
        nombres = ", ".join(r.fuente for r in malas)
        return Punto("Recolección del SIIP", "revisar",
                     f"Sin un intento exitoso en las últimas 36 h: {nombres}.")
    return Punto("Recolección del SIIP", "bien",
                 f"Todas las fuentes respondieron; {nuevos} precios nuevos en 24 h.")


def _respaldo(r: EstadoRespaldo | None, ahora: datetime) -> Punto:
    if r is None or r.fecha is None:
        return Punto("Respaldo de la base", "sin_datos", "No hay registro de respaldos en esta máquina.")
    if not r.verificado:
        return Punto("Respaldo de la base", "revisar",
                     f"El último respaldo no se pudo restaurar de prueba: {r.detalle or 'sin detalle'}.")
    if ahora - r.fecha > RESPALDO_VIEJO:
        return Punto("Respaldo de la base", "revisar", "El último respaldo verificado tiene más de 36 h.")
    return Punto("Respaldo de la base", "bien",
                 f"Restaurado de prueba con {r.filas_observaciones} observaciones.")


def _cobertura(observados: int, posibles: int) -> Punto:
    if not posibles:
        return Punto("Precios observados", "sin_datos", "El catálogo está vacío.")
    parte = observados / posibles
    texto = (f"{observados} de {posibles} pares mercado-producto ({parte:.0%}) tienen un precio "
             f"observado en {VENTANA_COBERTURA_DIAS} días; el resto se estima.")
    # Bajo 5 % casi todo es estimado: es honesto, pero hay que salir a medir.
    return Punto("Precios observados", "bien" if parte >= 0.05 else "revisar", texto)
