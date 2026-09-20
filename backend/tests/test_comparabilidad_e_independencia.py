"""
Las dos reglas que sostienen la honestidad del motor de fusión:

1. Solo se fusiona lo comparable (producto, variedad, unidad canónica,
   nivel, período). Lo no comparable se publica por separado y no es
   conflicto.
2. Dos fuentes que dicen lo mismo porque una copia a la otra son UNA
   evidencia. Si el sistema contara dos, inflaría la confianza y la
   tesis no se sostendría.
"""
from datetime import date, datetime, timezone

import pytest

from src.dominio.excepciones import DerivacionCiclica, GruposNoComparables, NivelesNoComparables
from src.dominio.modelo import Fuente, Mercado, NivelPrecio, Observacion, TipoPuntoVenta
from src.dominio.modelo import observacion as modulo_observacion
from src.dominio.servicio.motor_fusion import ClaveComparabilidad, MotorFusion
from src.dominio.valor import Dinero, NivelConfianza, Periodo, Unidad, UnidadCanonica

AHORA = datetime.now(timezone.utc)


def _obs(monto=10.0, unidad="KILO", fuente=Fuente.MEDIOS, periodo=Periodo(2026, 9, 15),
         variedad="desconocida", producto="papa", mercado="rodriguez", reputacion=1.0):
    return Observacion(
        fuente=fuente, nivel=fuente.nivel_fijo or NivelPrecio.MINORISTA,
        codigo_producto=producto, codigo_mercado=mercado, periodo=periodo,
        precio=Dinero(monto, Unidad(unidad)), capturada_en=AHORA, ambito=fuente.ambito,
        variedad=variedad, reputacion_informante=reputacion,
    )


# --- (a) comparabilidad ---------------------------------------------------

def test_la_clave_es_producto_variedad_unidad_nivel_y_periodo_mensual():
    clave = ClaveComparabilidad.de(_obs(variedad="holandesa", periodo=Periodo(2026, 9, 3)))
    assert clave == ClaveComparabilidad("papa", "holandesa", UnidadCanonica.KILOGRAMO,
                                        NivelPrecio.MINORISTA, 2026, 9)
    assert str(clave) == "papa/holandesa/kg/minorista/2026-09"


def test_una_diaria_y_una_mensual_del_mismo_mes_son_comparables():
    diaria = _obs(periodo=Periodo(2026, 9, 3))
    mensual = _obs(monto=10.4, periodo=Periodo(2026, 9))
    assert ClaveComparabilidad.de(diaria) == ClaveComparabilidad.de(mensual)
    assert MotorFusion().consolidar([diaria, mensual]).observaciones_usadas == 2


def test_julio_y_septiembre_no_se_fusionan_y_no_son_conflicto():
    julio = [_obs(8.0, periodo=Periodo(2026, 7, 10)), _obs(8.2, periodo=Periodo(2026, 7, 20))]
    septiembre = [_obs(12.0, periodo=Periodo(2026, 9, 10)), _obs(12.4, periodo=Periodo(2026, 9, 12))]

    grupos = MotorFusion().consolidar_grupos(julio + septiembre)

    assert [str(g.periodo)[:7] for g in grupos] == ["2026-09", "2026-07"]   # el más reciente primero
    assert grupos[0].rango.centro == pytest.approx(12.2, abs=0.3)
    assert grupos[1].rango.centro == pytest.approx(8.1, abs=0.3)
    assert not any(g.hay_conflicto for g in grupos)   # 50% de diferencia entre meses NO es conflicto


def test_variedades_distintas_son_grupos_distintos():
    holandesa = _obs(9.0, variedad="holandesa")
    huaycha = _obs(14.0, variedad="huaycha")

    grupos = MotorFusion().consolidar_grupos([holandesa, huaycha])
    assert len(grupos) == 2 and not any(g.hay_conflicto for g in grupos)

    with pytest.raises(GruposNoComparables) as e:
        MotorFusion().consolidar([holandesa, huaycha])
    assert "papa/holandesa/kg" in str(e.value) and "papa/huaycha/kg" in str(e.value)


def test_unidades_canonicas_distintas_son_grupos_distintos():
    """Un atado de cebolla verde y un kilo de cebolla verde no se promedian."""
    por_kilo = _obs(10.0, "KILO", producto="cebolla_verde")
    por_atado = _obs(3.0, "atado", producto="cebolla_verde")
    grupos = MotorFusion().consolidar_grupos([por_kilo, por_atado])
    assert {g.unidad for g in grupos} == {UnidadCanonica.KILOGRAMO, UnidadCanonica.ATADO}


def test_la_variedad_desconocida_es_su_propio_grupo_no_un_comodin():
    conocida = _obs(9.0, variedad="holandesa")
    desconocida = _obs(9.1)
    assert len(MotorFusion().consolidar_grupos([conocida, desconocida])) == 2


def test_las_no_convertibles_quedan_fuera_de_todos_los_grupos():
    grupos = MotorFusion().agrupar([_obs(10.0), _obs(50.0, "BOLSA")])
    assert sum(len(v) for v in grupos.values()) == 1


def test_el_conflicto_es_desacuerdo_dentro_de_un_mismo_grupo():
    mismo_grupo = [_obs(10.0, fuente=Fuente.MEDIOS), _obs(16.0, fuente=Fuente.CIUDADANO)]
    assert MotorFusion().consolidar(mismo_grupo).hay_conflicto


def test_los_niveles_distintos_siguen_teniendo_nombre_propio():
    minorista = _obs(10.0, fuente=Fuente.CAMPO)
    mayorista = Observacion(
        fuente=Fuente.CAMPO, nivel=NivelPrecio.MAYORISTA, codigo_producto="papa",
        codigo_mercado="rodriguez", periodo=Periodo(2026, 9, 15),
        precio=Dinero(4.0, Unidad("KILO")), capturada_en=AHORA,
    )
    with pytest.raises(NivelesNoComparables):
        MotorFusion().consolidar([minorista, mayorista])


# --- (b) independencia entre fuentes ---------------------------------------

def test_la_prensa_declara_que_deriva_del_siip():
    assert Fuente.PRENSA.deriva_de is Fuente.SIIP_DIARIO
    assert Fuente.PRENSA.raiz is Fuente.SIIP_DIARIO
    assert Fuente.SIIP_DIARIO.deriva_de is None and Fuente.SIIP_DIARIO.raiz is Fuente.SIIP_DIARIO
    # Hereda nivel y ámbito de lo que copia: es el mismo dato.
    assert Fuente.PRENSA.nivel_fijo is NivelPrecio.MAYORISTA
    assert Fuente.PRENSA.ambito is Fuente.SIIP_DIARIO.ambito


def test_una_copia_del_siip_no_infla_la_confianza():
    """
    La prueba que sostiene la tesis: el SIIP solo, y el SIIP más un diario
    que lo reproduce, tienen que dar EXACTAMENTE la misma confianza.
    """
    makro = Mercado("makro", "Makro", TipoPuntoVenta.MAYORISTA, "Centro")
    siip = _obs(565.0, "qq.", fuente=Fuente.SIIP_DIARIO, producto="arroz", mercado="la_paz")
    prensa = _obs(565.0, "qq.", fuente=Fuente.PRENSA, producto="arroz", mercado="la_paz")
    motor = MotorFusion()

    solo = motor.estimar_desde_ciudad([siip], makro)
    con_copia = motor.estimar_desde_ciudad([siip, prensa], makro)

    assert con_copia.confianza is solo.confianza
    assert con_copia.rango == solo.rango


def test_una_copia_no_arrastra_el_precio_ni_aunque_sea_distinta():
    """Si el diario transcribió mal, manda el miembro más confiable del clan: el SIIP."""
    makro = Mercado("makro", "Makro", TipoPuntoVenta.MAYORISTA, "Centro")
    siip = _obs(565.0, "qq.", fuente=Fuente.SIIP_DIARIO, producto="arroz", mercado="la_paz")
    prensa_mal = _obs(656.0, "qq.", fuente=Fuente.PRENSA, producto="arroz", mercado="la_paz")

    estimado = MotorFusion().estimar_desde_ciudad([siip, prensa_mal], makro)

    assert estimado.rango.centro == pytest.approx(565.0 / 46, abs=0.05 * 565 / 46 + 0.01)


def test_la_confianza_sube_con_clanes_independientes_no_con_observaciones():
    makro = Mercado("makro", "Makro", TipoPuntoVenta.MAYORISTA, "Centro")
    motor = MotorFusion()
    siip = _obs(565.0, "qq.", fuente=Fuente.SIIP_DIARIO, producto="arroz", mercado="la_paz")
    copias = [_obs(565.0, "qq.", fuente=Fuente.PRENSA, producto="arroz", mercado="la_paz") for _ in range(3)]

    # Cuatro observaciones, un solo clan: una evidencia. La confianza no sube
    # (queda ALTO por el SIIP, acotada a MEDIO por ser estimación).
    con_copias = motor.estimar_desde_ciudad([siip] + copias, makro)
    solo = motor.estimar_desde_ciudad([siip], makro)
    assert con_copias.confianza is solo.confianza
    assert con_copias.observaciones_usadas == 4   # se cuentan; no se ponderan

    # Dos voces independientes que coinciden sí suben la confianza.
    dos_voces = [_obs(10.0, fuente=Fuente.MEDIOS), _obs(10.2, fuente=Fuente.CIUDADANO)]
    assert motor.consolidar(dos_voces).confianza is NivelConfianza.ALTO


def test_las_voces_independientes_no_forman_clan():
    """Tres ciudadanos distintos no son copias: cada uno es evidencia propia."""
    assert not Fuente.CIUDADANO.es_voz_unica and not Fuente.CAMPO.es_voz_unica
    assert Fuente.SIIP_DIARIO.es_voz_unica and Fuente.PRENSA.es_voz_unica
    tres = [_obs(10.0 + i * 0.1, fuente=Fuente.CIUDADANO) for i in range(3)]
    assert MotorFusion().consolidar(tres).confianza is NivelConfianza.ALTO


def test_las_copias_no_votan_en_el_filtro_de_atipicos():
    """Tres diarios que transcribieron mal no expulsan al SIIP original."""
    makro = Mercado("makro", "Makro", TipoPuntoVenta.MAYORISTA, "Centro")
    siip = _obs(565.0, "qq.", fuente=Fuente.SIIP_DIARIO, producto="arroz", mercado="la_paz")
    copias_mal = [_obs(656.0, "qq.", fuente=Fuente.PRENSA, producto="arroz", mercado="la_paz") for _ in range(3)]

    estimado = MotorFusion().estimar_desde_ciudad([siip] + copias_mal, makro)

    assert estimado.rango.centro == pytest.approx(565.0 / 46, rel=0.09)
    assert not any("atípicas" in c for c in estimado.conflictos)


def test_un_ciclo_en_la_derivacion_falla_fuerte(monkeypatch):
    monkeypatch.setitem(modulo_observacion._DERIVA_DE, Fuente.SIIP_DIARIO, Fuente.PRENSA)
    with pytest.raises(DerivacionCiclica) as e:
        Fuente.validar_derivaciones()
    assert {"prensa", "siip_diario"} <= set(e.value.ciclo)
    with pytest.raises(DerivacionCiclica):
        MotorFusion()   # el motor no se construye sobre una relación rota


def test_la_derivacion_real_no_tiene_ciclos():
    Fuente.validar_derivaciones()
