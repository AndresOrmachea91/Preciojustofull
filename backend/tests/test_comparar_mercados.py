"""
Prueba de un caso de uso COMPLETO sin base de datos y sin red.

Esta es la demostración práctica de la arquitectura hexagonal: el caso de
uso se ejecuta enchufándole repositorios en memoria en lugar de los reales,
porque depende de puertos y no de implementaciones.
"""
import pytest

from src.aplicacion.casos_uso.calcular_canasta import CalcularCanastaCasoUso
from src.aplicacion.casos_uso.comparar_mercados import CompararMercadosCasoUso
from src.aplicacion.puertos.entrada import ItemCanasta
from src.dominio.excepciones import ProductoNoEncontrado


def test_los_mercados_salen_del_mas_barato_al_mas_caro(repositorios):
    productos, mercados, observaciones = repositorios
    caso = CompararMercadosCasoUso(productos, mercados, observaciones)

    resultado = caso.ejecutar("tomate")

    assert len(resultado) >= 2
    centros = [r.precio.rango.centro for r in resultado]
    assert centros == sorted(centros)


def test_el_minimarket_sale_mas_caro_que_el_mercado(repositorios):
    productos, mercados, observaciones = repositorios
    caso = CompararMercadosCasoUso(productos, mercados, observaciones)

    resultado = caso.ejecutar("tomate")
    por_codigo = {r.codigo_mercado: r.precio.rango.centro for r in resultado}

    assert por_codigo["minimarket_sopocachi"] > por_codigo["rodriguez"]


def test_filtra_por_zona(repositorios):
    productos, mercados, observaciones = repositorios
    caso = CompararMercadosCasoUso(productos, mercados, observaciones)

    resultado = caso.ejecutar("tomate", zona="Centro")

    assert all(r.zona == "Centro" for r in resultado)


def test_producto_inexistente_falla_con_error_de_dominio(repositorios):
    productos, mercados, observaciones = repositorios
    caso = CompararMercadosCasoUso(productos, mercados, observaciones)

    with pytest.raises(ProductoNoEncontrado):
        caso.ejecutar("no_existe")


def test_la_canasta_ordena_por_cobertura_y_luego_por_precio(repositorios):
    _, mercados, observaciones = repositorios
    caso = CalcularCanastaCasoUso(mercados, observaciones)

    resultado = caso.ejecutar([
        ItemCanasta("tomate", 2.0),
        ItemCanasta("papa", 1.0),
        ItemCanasta("arroz", 1.0),
    ])

    assert resultado
    assert resultado[0].cobertura >= resultado[-1].cobertura
    assert resultado[0].productos_pedidos == 3

