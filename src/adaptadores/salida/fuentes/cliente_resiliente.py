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
    ):
        self._s = requests.Session()
        self._s.headers.update({"User-Agent": AGENTE})
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
            try:
                r = self._s.request(metodo, url, timeout=self.tiempo_espera, **kwargs)
                self._ultima = time.time()
                if r.status_code == 200 and r.content:
                    self._fallos = 0
                    return r
                ultimo_error = RuntimeError(f"HTTP {r.status_code}")
            except requests.RequestException as e:
                self._ultima = time.time()
                ultimo_error = e

            if intento < self.intentos:
                time.sleep(self.espera_base * (2 ** (intento - 1)))

        self._registrar_fallo()
        raise ultimo_error or RuntimeError("fallo desconocido")

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

