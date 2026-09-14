"""
Pruebas del motor de fusión.

Ni una sola dependencia de infraestructura: no hay base de datos, no hay
red, no hay FastAPI. Se prueban reglas de negocio puras. Eso es posible
únicamente porque el dominio no depende de nada.
"""
import pytest

from src.dominio.excepciones import SinObservaciones
from src.dominio.modelo import Fuente
from src.dominio.servicio.motor_fusion import MotorFusion
from src.dominio.valor import NivelConfianza


def test_una_sola_fuente_conserva_su_confianza(hacer_observacion):
    motor = MotorFusion()
    resultado = motor.consolidar([hacer_observacion(10.0, fuente=Fuente.CIUDADANO, reputacion=0.5)])
    assert resultado.observaciones_usadas == 1
    assert resultado.confianza is NivelConfianza.BAJO


def test_el_dato_de_campo_manda_sobre_el_reporte_ciudadano(hacer_observacion):
    """
    Un precio verificado en campo y otro reportado sin historial: el
    consolidado tiene que quedar más cerca del verificado.
    """
    motor = MotorFusion()
    resultado = motor.consolidar([
        hacer_observacion(10.0, fuente=Fuente.CAMPO, reputacion=1.0),
        hacer_observacion(20.0, fuente=Fuente.CIUDADANO, reputacion=0.3),
    ])
    assert resultado.rango.centro < 15.0
    assert resultado.confianza is NivelConfianza.VERIFICADO


def test_se_registra_el_conflicto_entre_fuentes(hacer_observacion):
    motor = MotorFusion()
    resultado = motor.consolidar([
        hacer_observacion(10.0),
        hacer_observacion(25.0, fuente=Fuente.CIUDADANO, reputacion=0.5),
    ])
    assert resultado.hay_conflicto


def test_se_descarta_el_valor_atipico(hacer_observacion):
    """Un reporte manipulado no debe arrastrar el precio publicado."""
    motor = MotorFusion()
    normales = [hacer_observacion(v) for v in (10.0, 10.2, 9.8, 10.1)]
    manipulado = hacer_observacion(90.0, fuente=Fuente.CIUDADANO, reputacion=0.4)
    resultado = motor.consolidar(normales + [manipulado])
    assert resultado.rango.centro < 12.0
    assert resultado.observaciones_usadas == len(normales)


def test_normaliza_unidades_distintas(hacer_observacion):
    """
    Un precio por arroba y otro por kilo se tienen que poder comparar.
    Una arroba son 11,5 kg, así que Bs 115 la arroba son Bs 10 el kilo.
    """
    motor = MotorFusion()
    resultado = motor.consolidar([
        hacer_observacion(10.0, unidad="KILO"),
        hacer_observacion(115.0, unidad="ARROBA"),
    ])
    assert 9.0 <= resultado.rango.centro <= 11.0


def test_sin_observaciones_falla_explicitamente():
    with pytest.raises(SinObservaciones):
        MotorFusion().consolidar([])

