"""
Repositorios en memoria.

No son un juguete: son un adaptador de primera clase del mismo puerto que
el repositorio de PostgreSQL. Permiten correr la API y las pruebas sin
base de datos, y son la demostración práctica de que el núcleo no depende
de la infraestructura.
"""
from __future__ import annotations
from datetime import datetime, timezone

from src.dominio.modelo import (
    Categoria, Fuente, Mercado, NivelPrecio, Observacion, Producto, TipoPuntoVenta,
)
from src.dominio.valor import Dinero, Periodo, Unidad


class ProductosEnMemoria:
    def __init__(self, productos: list[Producto] | None = None):
        self._datos = {p.codigo: p for p in (productos or [])}

    def obtener(self, codigo: str) -> Producto | None:
        return self._datos.get(codigo)

    def listar(self) -> list[Producto]:
        return list(self._datos.values())

    def guardar(self, producto: Producto) -> None:
        self._datos[producto.codigo] = producto


class MercadosEnMemoria:
    def __init__(self, mercados: list[Mercado] | None = None):
        self._datos = {m.codigo: m for m in (mercados or [])}

    def obtener(self, codigo: str) -> Mercado | None:
        return self._datos.get(codigo)

    def listar(self, zona: str | None = None) -> list[Mercado]:
        todos = list(self._datos.values())
        if zona is None:
            return todos
        return [m for m in todos if m.zona.lower() == zona.lower()]

    def guardar(self, mercado: Mercado) -> None:
        self._datos[mercado.codigo] = mercado


class ObservacionesEnMemoria:
    def __init__(self, observaciones: list[Observacion] | None = None):
        self._datos: list[Observacion] = list(observaciones or [])

    def buscar(
        self,
        codigo_producto: str,
        codigo_mercado: str | None = None,
        periodo: Periodo | None = None,
    ) -> list[Observacion]:
        salida = [o for o in self._datos if o.codigo_producto == codigo_producto]
        if codigo_mercado:
            salida = [o for o in salida if o.codigo_mercado == codigo_mercado]
        if periodo:
            salida = [o for o in salida if o.periodo == periodo]
        return salida

    def guardar_varias(self, observaciones: list[Observacion]) -> int:
        self._datos.extend(observaciones)
        return len(observaciones)


# --- datos de ejemplo para levantar la API sin base de datos --------------

def datos_de_ejemplo():
    hoy = datetime.now(timezone.utc)
    periodo = Periodo(hoy.year, hoy.month, hoy.day)

    productos = [
        Producto("tomate", "Tomate", Categoria.HORTALIZA, dias_conservacion=5, zona_origen="Valles"),
        Producto("papa", "Papa holandesa", Categoria.TUBERCULO, dias_conservacion=60, zona_origen="Altiplano"),
        Producto("arroz", "Arroz de primera", Categoria.ABARROTE, dias_conservacion=365, zona_origen="Santa Cruz"),
    ]
    mercados = [
        Mercado("rodriguez", "Mercado Rodríguez", TipoPuntoVenta.MERCADO, "San Pedro", -16.4998, -68.1385, 1.00),
        Mercado("lanza", "Mercado Lanza", TipoPuntoVenta.MERCADO, "Centro", -16.4957, -68.1360, 1.06),
        Mercado("villafatima", "Mercado Villa Fátima", TipoPuntoVenta.MERCADO, "Villa Fátima", -16.4816, -68.1194, 0.97),
        Mercado("minimarket_sopocachi", "Minimarket Sopocachi", TipoPuntoVenta.MINIMARKET, "Sopocachi", -16.5100, -68.1300, 1.22),
    ]

    def obs(prod, merc, monto, unidad, fuente, reput=1.0):
        return Observacion(
            fuente=fuente, nivel=NivelPrecio.MINORISTA,
            codigo_producto=prod, codigo_mercado=merc, periodo=periodo,
            precio=Dinero(monto, Unidad(unidad)), capturada_en=hoy,
            reputacion_informante=reput,
        )

    observaciones = [
        obs("tomate", "rodriguez", 6.50, "LIBRA", Fuente.CAMPO),
        obs("tomate", "rodriguez", 7.00, "LIBRA", Fuente.CIUDADANO, 0.7),
        obs("tomate", "lanza", 7.50, "LIBRA", Fuente.CIUDADANO, 0.8),
        obs("tomate", "villafatima", 6.00, "LIBRA", Fuente.MEDIOS),
        obs("tomate", "minimarket_sopocachi", 9.00, "LIBRA", Fuente.CAMPO),
        obs("papa", "rodriguez", 80.0, "ARROBA", Fuente.SIIP_DIARIO),
        obs("papa", "lanza", 85.0, "ARROBA", Fuente.CIUDADANO, 0.6),
        obs("papa", "villafatima", 78.0, "ARROBA", Fuente.CAMPO),
        obs("arroz", "rodriguez", 8.20, "KILO", Fuente.SIIP_IPC),
        obs("arroz", "lanza", 8.60, "KILO", Fuente.SIIP_IPC),
        obs("arroz", "minimarket_sopocachi", 10.50, "KILO", Fuente.CAMPO),
    ]
    return (
        ProductosEnMemoria(productos),
        MercadosEnMemoria(mercados),
        ObservacionesEnMemoria(observaciones),
    )

