"""
A4230 y A5020: qué conviene medir primero y cuánto se mueve cada precio.

Lo que se prueba es la regla que la tesis tiene que poder defender: se
mide primero lo que nadie midió, lo vencido y lo que más se mueve, y la
ronda se reparte por la ciudad en vez de quedarse en un barrio.
"""
from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient

from src.aplicacion.casos_uso.precios.priorizar_verificaciones import (
    LugarPorVisitar, PriorizarVerificaciones, repartir_por_macrodistrito, variacion_mensual,
)
from src.dominio.modelo import Categoria, Fuente, Mercado, NivelPrecio, Observacion, Producto, TipoPuntoVenta
from src.dominio.servicio.motor_fusion import MotorFusion
from src.dominio.valor import Ambito, Dinero, Periodo, Unidad
from src.infraestructura.adaptadores.entrada.api.main import app
from src.infraestructura.adaptadores.salida.memoria.repositorios import (
    MercadosEnMemoria, ObservacionesEnMemoria, ProductosEnMemoria,
)

HOY = date(2026, 10, 20)
CAPTURA = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)

TOMATE = Producto("tomate", "Tomate", Categoria.HORTALIZA, dias_conservacion=5)
ARROZ = Producto("arroz", "Arroz", Categoria.ABARROTE, dias_conservacion=365)
RODRIGUEZ = Mercado("rodriguez", "Mercado Rodríguez", TipoPuntoVenta.MERCADO, "San Pedro", -16.5, -68.13, 1.0,
                    macrodistrito="Cotahuma")
LANZA = Mercado("lanza", "Mercado Lanza", TipoPuntoVenta.MERCADO, "Centro", -16.49, -68.13, 1.0,
                macrodistrito="Centro")
YUNGUYO = Mercado("yunguyo", "Mercado Yungas", TipoPuntoVenta.MERCADO, "Centro", -16.49, -68.12, 1.0,
                  macrodistrito="Centro")
MAYORISTA = Mercado("mayorista", "Mayorista", TipoPuntoVenta.MAYORISTA, "El Alto", -16.5, -68.16, 1.0,
                    macrodistrito="Max Paredes")


def ciudad(producto: str, anio: int, mes: int, monto: float) -> Observacion:
    return Observacion(
        fuente=Fuente.SIIP_IPC, nivel=NivelPrecio.MINORISTA, codigo_producto=producto, codigo_mercado=None,
        ciudad="la_paz", ambito=Ambito.CIUDAD, periodo=Periodo(anio, mes), precio=Dinero(monto, Unidad("KILO")),
        capturada_en=CAPTURA,
    )


def en_lugar(producto: str, mercado: str, dias_atras: int, monto: float = 8.0) -> Observacion:
    fecha = HOY - timedelta(days=dias_atras)
    return Observacion(
        fuente=Fuente.CAMPO, nivel=NivelPrecio.MINORISTA, codigo_producto=producto, codigo_mercado=mercado,
        periodo=Periodo(fecha.year, fecha.month, fecha.day), precio=Dinero(monto, Unidad("KILO")),
        capturada_en=CAPTURA, fecha_observacion=fecha,
    )


def serie(producto: str, montos: list[float]) -> list[Observacion]:
    return [ciudad(producto, 2026, mes, monto) for mes, monto in enumerate(montos, start=1)]


def plan(observaciones, mercados=(RODRIGUEZ, LANZA, MAYORISTA)):
    caso = PriorizarVerificaciones(
        ProductosEnMemoria([TOMATE, ARROZ]), MercadosEnMemoria(list(mercados)),
        ObservacionesEnMemoria(observaciones), MotorFusion(), reloj=lambda: HOY,
    )
    return caso.ejecutar()


def test_cuanto_se_mueve_un_precio_es_el_cambio_mensual_tipico():
    v = variacion_mensual(TOMATE, serie("tomate", [10, 11, 9.9, 9.9]))
    # +10 %, -10 %, 0 %: típico 6,67 %, mayor subida 10 %, mayor bajada -10 %.
    assert v is not None
    assert v.meses == 4
    assert round(v.cambio_mensual, 4) == 0.0667
    assert v.mayor_subida == 0.1
    assert v.mayor_bajada == -0.1
    assert v.nivel == "minorista"


def test_con_menos_de_tres_meses_no_se_dice_cuanto_varia():
    assert variacion_mensual(TOMATE, serie("tomate", [10, 12])) is None


def test_lo_que_mas_se_mueve_va_primero_si_nadie_lo_midio():
    datos = serie("tomate", [10, 13, 9, 12, 8]) + serie("arroz", [8, 8.1, 8, 8.1, 8])
    resultado = plan(datos)
    assert [p.producto.codigo for p in resultado.productos] == ["tomate", "arroz"]
    tomate = resultado.productos[0]
    assert tomate.lugares_sin_dato == 2          # el mayorista no cuenta: la ronda mide consumo final
    assert "nadie lo midió todavía en ningún lugar" in tomate.motivos
    assert any("de un mes a otro" in m for m in tomate.motivos)
    assert [v.producto.codigo for v in resultado.variaciones] == ["tomate", "arroz"]


def test_lo_medido_hace_poco_baja_la_prioridad_y_lo_vencido_no():
    datos = serie("tomate", [10, 13, 9, 12, 8]) + serie("arroz", [8, 8.1, 8, 8.1, 8])
    al_dia = plan(datos + [en_lugar("tomate", "rodriguez", 1), en_lugar("tomate", "lanza", 2)])
    tomate = next(p for p in al_dia.productos if p.producto.codigo == "tomate")
    assert tomate.lugares_al_dia == 2 and tomate.puntaje == 0

    # Un tomate de hace 10 días ya caducó (dura 5): cuenta como dato vencido.
    vencido = plan(datos + [en_lugar("tomate", "rodriguez", 10)])
    tomate = next(p for p in vencido.productos if p.producto.codigo == "tomate")
    assert tomate.lugares_con_dato_viejo == 1
    assert tomate.puntaje > 0
    assert "dato vencido en 1 lugar" in tomate.motivos


def test_un_producto_sin_serie_no_queda_escondido_al_final():
    resultado = plan(serie("tomate", [10, 13, 9, 12, 8]))
    arroz = next(p for p in resultado.productos if p.producto.codigo == "arroz")
    assert arroz.puntaje > 0
    assert "sin serie de la ciudad: no se sabe cuánto varía" in arroz.motivos


def test_la_ronda_se_reparte_por_macrodistrito():
    lugares = [LugarPorVisitar(m, 0, 2) for m in (LANZA, YUNGUYO, RODRIGUEZ)]
    orden = [x.mercado.codigo for x in repartir_por_macrodistrito(lugares)]
    # Lanza y Yungas están en el Centro: entre ellos va el Rodríguez, de Cotahuma.
    assert orden == ["lanza", "rodriguez", "yunguyo"]


def test_el_lugar_menos_cubierto_va_primero():
    datos = serie("tomate", [10, 13, 9, 12, 8]) + [en_lugar("tomate", "rodriguez", 1)]
    resultado = plan(datos)
    assert [x.mercado.codigo for x in resultado.lugares] == ["lanza", "rodriguez"]
    assert resultado.lugares[1].productos_al_dia == 1


def test_la_api_publica_el_plan():
    cliente = TestClient(app)
    respuesta = cliente.get("/api/v1/verificaciones")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert {"fecha", "productos", "lugares", "variaciones"} <= set(cuerpo)
