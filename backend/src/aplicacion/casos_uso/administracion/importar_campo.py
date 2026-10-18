"""
El administrador carga las cotizaciones del levantamiento de campo (C127).

Cada fila de la planilla es una observación con fuente CAMPO: alguien fue
al puesto y anotó el precio. Es el lado "observado" contra el que se mide
el estimador (backtest), así que entra con las mismas reglas que todo lo
demás y nada se corrige a ojo:

- el mercado y el producto tienen que existir en el catálogo;
- la presentación tiene que ser de la unidad del producto (la papa no se
  vende por litro);
- la fecha no puede ser futura ni anterior a 2020;
- cada fila mala se informa con su número y su motivo, y no frena a las
  buenas. Con `solo_revisar` no se guarda nada: sirve para ver antes.

Quién midió queda como informante ("campo:ana"), así la regla de una voz
por informante también vale en campo: diez filas de la misma persona en
el mismo puesto son una medición. Con la columna `puesto` (A4200), cada
puesto que visitó es una voz aparte ("campo:ana:puesto:14"): son vendedores
distintos, y el puesto queda anotado para la ficha del mercado. El sector
se indica en la columna mercado con el código del sector (rodriguez_cubierto).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from src.aplicacion.casos_uso.cuentas.permisos import exigir
from src.aplicacion.puertos.salida import EscritorObservaciones, LectorMercados, LectorProductos
from src.dominio.excepciones import DatoInvalido
from src.dominio.modelo import Fuente, Observacion, Permiso, Presentacion, Usuario
from src.dominio.modelo.puesto import normalizar_numero
from src.dominio.valor import VARIEDAD_DESCONOCIDA, Dinero, Periodo, TipoPrecio, Unidad

COLUMNAS_OBLIGATORIAS = ("fecha", "mercado", "producto", "monto", "presentacion")
COLUMNAS_OPCIONALES = ("cantidad", "variedad", "observador", "tipo", "puesto")
MAXIMO_FILAS = 2000
_PRIMERA_FECHA = date(2020, 1, 1)


@dataclass(frozen=True, slots=True)
class FilaRechazada:
    fila: int
    motivo: str


@dataclass(slots=True)
class ResultadoImportacion:
    leidas: int = 0
    validas: int = 0
    guardadas: int = 0
    rechazadas: list[FilaRechazada] = field(default_factory=list)


class ImportarCotizacionesCampo:
    def __init__(self, productos: LectorProductos, mercados: LectorMercados,
                 observaciones: EscritorObservaciones):
        self._productos = productos
        self._mercados = mercados
        self._observaciones = observaciones

    def ejecutar(self, actor: Usuario, filas: list[dict[str, str]], hoy: date,
                 solo_revisar: bool = False, archivo: str = "planilla") -> ResultadoImportacion:
        exigir(actor, Permiso.IMPORTAR_CAMPO)
        resultado = ResultadoImportacion(leidas=len(filas))
        if len(filas) > MAXIMO_FILAS:
            resultado.rechazadas.append(FilaRechazada(0, f"La planilla pasa de {MAXIMO_FILAS} filas: divídala"))
            return resultado
        validas: list[Observacion] = []
        ahora = datetime.now(timezone.utc)
        # La fila 1 es el encabezado: la primera de datos es la 2, como la ve
        # quien abre la planilla.
        for numero, fila in enumerate(filas, start=2):
            try:
                validas.append(self._observacion(actor, fila, hoy, ahora, f"campo:{archivo}:fila{numero}"))
            except ValueError as error:
                resultado.rechazadas.append(FilaRechazada(numero, str(error)))
        resultado.validas = len(validas)
        if validas and not solo_revisar:
            resultado.guardadas = self._observaciones.guardar_varias(validas)
        return resultado

    def _observacion(self, actor: Usuario, fila: dict[str, str], hoy: date, ahora: datetime,
                     evidencia: str) -> Observacion:
        valor = {k: (fila.get(k) or "").strip() for k in COLUMNAS_OBLIGATORIAS + COLUMNAS_OPCIONALES}
        faltan = [k for k in COLUMNAS_OBLIGATORIAS if not valor[k]]
        if faltan:
            raise ValueError(f"Falta {', '.join(faltan)}")

        try:
            fecha = date.fromisoformat(valor["fecha"])
        except ValueError:
            raise ValueError(f"Fecha {valor['fecha']!r} no es AAAA-MM-DD") from None
        if fecha > hoy:
            raise ValueError(f"La fecha {fecha} es futura")
        if fecha < _PRIMERA_FECHA:
            raise ValueError(f"La fecha {fecha} es anterior a 2020")

        mercado = self._mercados.obtener(valor["mercado"])
        if mercado is None:
            raise ValueError(f"No existe el mercado {valor['mercado']!r}")
        producto = self._productos.obtener(valor["producto"])
        if producto is None:
            raise ValueError(f"No existe el producto {valor['producto']!r}")

        try:
            presentacion = Presentacion(valor["presentacion"].lower())
        except ValueError:
            raise ValueError(f"Presentación {valor['presentacion']!r} desconocida") from None
        if presentacion.unidad_base is not producto.unidad_base:
            raise ValueError(f"{producto.nombre} no se vende por {presentacion.value}")

        monto = _numero(valor["monto"], "monto")
        cantidad = _numero(valor["cantidad"], "cantidad") if valor["cantidad"] else 1.0
        if monto <= 0 or cantidad <= 0:
            raise ValueError("El monto y la cantidad tienen que ser mayores a cero")
        try:
            tipo = TipoPrecio(valor["tipo"].lower()) if valor["tipo"] else TipoPrecio.COTIZADO
        except ValueError:
            raise ValueError(f"Tipo {valor['tipo']!r}: use anunciado, cotizado o pagado") from None

        observador = valor["observador"].lower() or f"usuario-{actor.id}"
        puesto = None
        if valor["puesto"]:
            try:
                puesto = normalizar_numero(valor["puesto"])
            except DatoInvalido as error:
                raise ValueError(str(error)) from None
        return Observacion(
            fuente=Fuente.CAMPO,
            nivel=mercado.nivel_precio,
            codigo_producto=producto.codigo,
            codigo_mercado=mercado.codigo,
            periodo=Periodo(fecha.year, fecha.month, fecha.day),
            precio=Dinero(monto, Unidad(presentacion.value.upper())),
            capturada_en=ahora,
            cantidad=cantidad,
            variedad=valor["variedad"].lower() or VARIEDAD_DESCONOCIDA,
            fecha_observacion=fecha,
            tipo_precio=tipo,
            evidencia=evidencia,
            informante=f"campo:{observador}" + (f":puesto:{puesto}" if puesto else ""),
            puesto=puesto,
        )


def _numero(texto: str, nombre: str) -> float:
    try:
        # En Bolivia la coma es el separador decimal: "8,50" es 8.5.
        return float(texto.replace(",", "."))
    except ValueError:
        raise ValueError(f"El {nombre} {texto!r} no es un número") from None
