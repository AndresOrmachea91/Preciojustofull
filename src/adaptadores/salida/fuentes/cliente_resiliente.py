"""
Cliente HTTP con la política de resiliencia del proyecto.

Vive en los adaptadores porque es un detalle de infraestructura: el dominio
no sabe que existe HTTP. Implementa reintentos con retroceso exponencial,
cortacircuito y ritmo respetuoso — necesarios porque los portales del
Estado son intermitentes.
"""
from __future__ import annotations
import time
import logging

import requests

log = logging.getLogger(__name__)

AGENTE = "PrecioJusto/0.1 (proyecto academico; precios publicos)"


class CortacircuitoAbierto(RuntimeError):
    """La fuente falló demasiadas veces seguidas; no se insiste por ahora."""


class ClienteResiliente:
    def __init__(
        self,
        intentos: int = 4,
        espera_base: float = 2.0,
        pausa: float = 1.5,
        tiempo_espera: int = 25,
        fallos_para_abrir: int = 6,
        espera_cortacircuito: int = 900,
        registrar_intento=None,
    ):
        """
        registrar_intento: función (fuente, url, exito, ms, detalle) que se
        invoca en CADA intento crudo contra la fuente, incluidos los que
        fallan y se reintentan.

        Que se registre acá y no en el llamador es lo que hace medible la
        contribución de la arquitectura: la disponibilidad de la fuente
        original se calcula sobre estos intentos crudos, mientras que la
        disponibilidad efectiva del sistema se mide sobre los resultados
        finales. La diferencia entre ambas es el valor que aportan los
        reintentos, el retroceso y la réplica local. Si solo se registrara
        el resultado final, ambas darían siempre lo mismo y la ganancia
        sería invisible.
        """
        self._s = requests.Session()
        self._s.headers.update({"User-Agent": AGENTE})
        self._registrar = registrar_intento
        self.nombre_fuente = "desconocida"
        self.intentos = intentos
        self.espera_base = espera_base
        self.pausa = pausa
        self.tiempo_espera = tiempo_espera
        self.fallos_para_abrir = fallos_para_abrir
        self.espera_cortacircuito = espera_cortacircuito
        self._fallos = 0
        self._abierto_hasta = 0.0
        self._ultima = 0.0

    @property
    def cortacircuito_abierto(self) -> bool:
        return time.time() < self._abierto_hasta

    def pedir(self, url: str, metodo: str = "GET", **kwargs) -> requests.Response:
        if self.cortacircuito_abierto:
            raise CortacircuitoAbierto(url)

        ultimo_error: Exception | None = None
        for intento in range(1, self.intentos + 1):
            self._respetar_ritmo()
            inicio = time.time()
            try:
                r = self._s.request(metodo, url, timeout=self.tiempo_espera, **kwargs)
                self._ultima = time.time()
                ms = int((self._ultima - inicio) * 1000)

                if r.status_code == 200 and r.content:
                    self._anotar(url, True, ms, f"{len(r.content)} bytes")
                    self._fallos = 0
                    return r

                ultimo_error = RuntimeError(f"HTTP {r.status_code}")
                self._anotar(url, False, ms, str(ultimo_error))
            except requests.RequestException as e:
                self._ultima = time.time()
                ms = int((self._ultima - inicio) * 1000)
                ultimo_error = e
                self._anotar(url, False, ms, type(e).__name__)

            if intento < self.intentos:
                time.sleep(self.espera_base * (2 ** (intento - 1)))

        self._registrar_fallo()
        raise ultimo_error or RuntimeError("fallo desconocido")

    def _anotar(self, url: str, exito: bool, ms: int, detalle: str) -> None:
        if not self._registrar:
            return
        try:
            self._registrar(self.nombre_fuente, url, exito, ms, detalle)
        except Exception:
            log.exception("No se pudo registrar el intento")

    def _respetar_ritmo(self):
        transcurrido = time.time() - self._ultima
        if transcurrido < self.pausa:
            time.sleep(self.pausa - transcurrido)

    def _registrar_fallo(self):
        self._fallos += 1
        if self._fallos >= self.fallos_para_abrir:
            self._abierto_hasta = time.time() + self.espera_cortacircuito
            self._fallos = 0
            log.warning("Cortacircuito abierto por %ss", self.espera_cortacircuito)

