"""
Adaptador de la fuente SIIP — precios promedio al consumidor (IPC).

Mismo puerto que el mayorista, formato completamente distinto: POST con
cuerpo form-encoded y respuesta JSON. Esa es la gracia de los puertos.
"""
from __future__ import annotations
import re
import logging
from datetime import datetime, timezone

from src.infraestructura.adaptadores.salida.fuentes.cliente_resiliente import ClienteResiliente
from src.dominio.modelo import Fuente, Observacion
from src.dominio.valor import Dinero, Periodo, TipoPrecio, Unidad

log = logging.getLogger(__name__)

URL = "https://siip.produccion.gob.bo/repSIIP2/controller/sw/precio/sw_valor_ipc_mensual.php"
MESES = {
    "ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SEP": 9, "SET": 9, "OCT": 10, "NOV": 11, "DIC": 12,
}


class FuenteSiipIpc:
    """Adaptador del puerto FuentePrecios."""

    def __init__(self, cliente: ClienteResiliente | None = None, version: str = "2018"):
        self._cliente = cliente or ClienteResiliente()
        self._cliente.nombre_fuente = self.nombre
        self._version = version

    @property
    def nombre(self) -> str:
        return "SIIP IPC minorista"

    def esta_disponible(self) -> bool:
        return not self._cliente.cortacircuito_abierto

    def catalogo(self) -> list[dict]:
        r = self._cliente.pedir(
            URL, metodo="POST",
            data={"flag": "itemsXDivision", "version": self._version},
        )
        return r.json() or []

    def recolectar(self, codigo_producto: str) -> list[Observacion]:
        r = self._cliente.pedir(
            URL, metodo="POST",
            data={"flag": "itemAniosMes", "version": self._version, "item": codigo_producto},
        )
        return self._parsear(r.json(), codigo_producto)

    def _parsear(self, datos, codigo_producto: str) -> list[Observacion]:
        if not isinstance(datos, dict):
            log.error("Respuesta del IPC inesperada")
            return []

        periodos = []
        for etiqueta in datos.get("eje_x") or []:
            m = re.match(r"([A-ZÁ]{3})[-/](\d{4})", str(etiqueta).upper())
            periodos.append(
                (int(m.group(2)), MESES[m.group(1)]) if m and m.group(1) in MESES else (None, None)
            )

        ahora = datetime.now(timezone.utc)
        salida: list[Observacion] = []
        for fila in datos.get("data") or []:
            ciudad = (fila.get("ciudad") or "").strip()
            unidad_texto = fila.get("unidad") or ""
            if not Unidad(unidad_texto).es_conocida():
                log.warning("Unidad no convertible en %s/%s: %r", codigo_producto, ciudad, unidad_texto)
            # El IPC cotiza una presentación concreta ("Bs 75,87 por 760
            # gramos"). Se conserva el par original con su cantidad; la
            # entidad convierte.
            try:
                cantidad = float(fila.get("cantidad") or 1) or 1.0
            except (TypeError, ValueError):
                cantidad = 1.0

            for i, bruto in enumerate(fila.get("valor") or []):
                if i >= len(periodos):
                    break
                anio, mes = periodos[i]
                if anio is None or not bruto:
                    continue
                try:
                    precio = Dinero(float(bruto), Unidad(unidad_texto))
                except (TypeError, ValueError):
                    continue
                salida.append(
                    Observacion(
                        fuente=Fuente.SIIP_IPC,
                        nivel=Fuente.SIIP_IPC.nivel_fijo,
                        codigo_producto=codigo_producto,
                        # La ciudad va en su campo; no hay punto de venta.
                        codigo_mercado=None,
                        ciudad=ciudad.lower().replace(" ", "_"),
                        periodo=Periodo(anio, mes),
                        precio=precio,
                        capturada_en=ahora,
                        ambito=Fuente.SIIP_IPC.ambito,
                        cantidad=cantidad,
                        # Promedio mensual: el dato no trae un día.
                        fecha_observacion=None,
                        tipo_precio=TipoPrecio.COTIZADO,
                    )
                )
        return salida

