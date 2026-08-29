"""
Adaptador de la fuente SIIP — precios diarios mayoristas.

Implementa el puerto FuentePrecios. Devuelve HTML (una tabla), no JSON.
El núcleo no sabe nada de eso: recibe Observaciones y punto.
"""
from __future__ import annotations
import re
import logging
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from src.adaptadores.salida.fuentes.cliente_resiliente import ClienteResiliente
from src.dominio.modelo import Fuente, NivelPrecio, Observacion
from src.dominio.valor import Dinero, Periodo, Unidad

log = logging.getLogger(__name__)

URL = "https://siip.produccion.gob.bo/repSIIP2/resultadoSispamDiario.php"
MESES = {
    "ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SEP": 9, "SET": 9, "OCT": 10, "NOV": 11, "DIC": 12,
}


def numero_boliviano(texto: str) -> float | None:
    """'1.310,42' -> 1310.42. Punto de miles, coma decimal."""
    if not texto:
        return None
    t = re.sub(r"[^\d,.\-]", "", str(texto).strip())
    if not t:
        return None
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        v = float(t)
    except ValueError:
        return None
    return v if v > 0 else None


class FuenteSiipDiario:
    """Adaptador del puerto FuentePrecios."""

    def __init__(self, cliente: ClienteResiliente | None = None, departamento: int = 2):
        self._cliente = cliente or ClienteResiliente()
        self._departamento = departamento   # 2 = La Paz

    @property
    def nombre(self) -> str:
        return "SIIP diario mayorista"

    def esta_disponible(self) -> bool:
        return not self._cliente.cortacircuito_abierto

    def recolectar(self, codigo_producto: str) -> list[Observacion]:
        params = {
            "DatosGen": 1,
            "producto": codigo_producto,
            f"d{self._departamento}": self._departamento,
        }
        respuesta = self._cliente.pedir(URL, params=params)
        return self._parsear(respuesta.text, codigo_producto)

    # -- parseo (detalle del adaptador, nunca del dominio) ---------------

    def _parsear(self, html: str, codigo_producto: str) -> list[Observacion]:
        sopa = BeautifulSoup(html, "html.parser")
        tabla = sopa.find("table")
        if tabla is None:
            log.error("La respuesta del SIIP no trae tabla")
            return []

        filas = tabla.find_all("tr")
        encabezados, inicio = self._encabezados(filas)
        if not encabezados:
            return []

        ancho = max(len(e) for e in encabezados)
        encabezados = [[""] * (ancho - len(e)) + e for e in encabezados]
        periodos = self._mapear_periodos(encabezados, ancho)

        ahora = datetime.now(timezone.utc)
        salida: list[Observacion] = []
        for fila in filas[inicio:]:
            celdas = [c.get_text(" ", strip=True) for c in fila.find_all(["td", "th"])]
            if len(celdas) < 3:
                continue
            ciudad = celdas[0].strip()
            unidad = celdas[1].strip()
            if not ciudad or ciudad.lower().startswith("promedio"):
                continue   # el promedio se recalcula, no se importa

            for col, (anio, mes, dia) in periodos.items():
                if col >= len(celdas) or anio is None:
                    continue
                valor = numero_boliviano(celdas[col])
                if valor is None:
                    continue
                try:
                    precio = Dinero(valor, Unidad(unidad))
                except ValueError:
                    continue
                salida.append(
                    Observacion(
                        fuente=Fuente.SIIP_DIARIO,
                        nivel=NivelPrecio.MAYORISTA,
                        codigo_producto=codigo_producto,
                        codigo_mercado=ciudad.lower().replace(" ", "_"),
                        periodo=Periodo(anio, mes, dia),
                        precio=precio,
                        capturada_en=ahora,
                    )
                )
        return salida

    def _encabezados(self, filas):
        encabezados, inicio = [], 0
        for i, fila in enumerate(filas[:5]):
            celdas = self._expandir(fila)
            if not self._es_encabezado(celdas):
                inicio = i
                break
            encabezados.append(celdas)
            inicio = i + 1
        return encabezados, inicio

    @staticmethod
    def _expandir(fila):
        salida = []
        for c in fila.find_all(["th", "td"]):
            texto = c.get_text(" ", strip=True)
            try:
                span = int(c.get("colspan", 1))
            except (TypeError, ValueError):
                span = 1
            salida.extend([texto] * max(span, 1))
        return salida

    @staticmethod
    def _es_encabezado(celdas) -> bool:
        if not celdas:
            return False
        texto = " ".join(celdas).upper()
        if any(p in texto for p in ("CIUDAD", "UNIDAD", "DEPARTAMENTO", "MEDIDA")):
            return True
        if any(re.search(rf"\b{m}\b", texto) for m in MESES):
            return True
        cuerpo = [c.strip() for c in celdas[2:] if c.strip()]
        return bool(cuerpo) and all(re.fullmatch(r"20\d{2}", c) for c in cuerpo)

    @staticmethod
    def _mapear_periodos(encabezados, ancho):
        """
        Las últimas columnas son DÍAS del mes más reciente, rotuladas solo
        con el número. Sin esto se pierde toda la granularidad diaria, que
        es justamente la que deja ver el efecto de un bloqueo.
        """
        periodos, anio_actual, mes_actual = {}, None, None
        for col in range(ancho):
            etiquetas = [e[col] if col < len(e) else "" for e in encabezados]
            texto = " ".join(t for t in etiquetas if t).upper()
            ultima = (etiquetas[-1] or "").strip()

            anio = None
            m = re.search(r"(20\d{2})", texto)
            if m:
                anio = int(m.group(1))
                anio_actual = anio

            mes = None
            for abrev, num in MESES.items():
                if re.search(rf"\b{abrev}\b", texto):
                    mes = mes_actual = num
                    break

            dia = None
            if re.fullmatch(r"\d{1,2}", ultima) and 1 <= int(ultima) <= 31:
                dia = int(ultima)
                mes = mes or mes_actual

            if anio or mes or dia:
                periodos[col] = (anio or anio_actual, mes or mes_actual, dia)
        return periodos

