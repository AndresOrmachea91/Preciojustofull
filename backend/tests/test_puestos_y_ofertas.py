"""
C133 y C134: el puesto del casero, sus ofertas con candado, el "¿Lo viste
así?" de los compradores y la ficha de cada mercado.

Los candados que se prueban acá son los que hacen que una oferta no sea
publicidad engañosa: vence, máximo tres, ahorro contra el precio del
sistema SIN la voz del casero, y dos desmentidos la pausan.
"""
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from src.aplicacion.casos_uso.administracion.importar_campo import ImportarCotizacionesCampo
from src.aplicacion.casos_uso.administracion.revisar_ofertas import RevisarOfertas
from src.aplicacion.casos_uso.precios.ficha_mercado import DirectorioMercados, FichaMercado
from src.aplicacion.casos_uso.precios.ofertas_vigentes import VerOfertasVigentes
from src.aplicacion.casos_uso.usuario.confirmar_oferta import ConfirmarOferta
from src.aplicacion.casos_uso.vendedor.mi_puesto import MiPuestoCasoUso
from src.aplicacion.casos_uso.vendedor.ofertas import OfertasDelCasero
from src.aplicacion.casos_uso.vendedor.publicar_precio import PublicarPrecioPropio
from src.dominio.excepciones import CodigoYaExiste, DatoInvalido, OfertaNoEncontrada, OfertaNoPermitida
from src.dominio.modelo import (
    Categoria, EstadoOferta, Fuente, Mercado, NivelPrecio, Observacion, Presentacion, Puesto, Rol,
    TipoPuntoVenta, Usuario,
)
from src.dominio.modelo.oferta import Confirmacion, Oferta, hay_que_pausar
from src.dominio.modelo.puesto import normalizar_numero, orden_de_numero
from src.dominio.servicio.motor_fusion import MotorFusion
from src.dominio.valor import Ambito, Dinero, Periodo, Unidad
from src.infraestructura.adaptadores.entrada.api.main import app
from src.infraestructura.adaptadores.salida.memoria.puestos_y_ofertas import OfertasEnMemoria, PuestosEnMemoria
from src.infraestructura.adaptadores.salida.persistencia.puestos_y_ofertas import OfertasPostgres, PuestosPostgres
from src.infraestructura.adaptadores.salida.persistencia.repositorios import ObservacionesPostgres
from src.infraestructura.adaptadores.salida.persistencia.sesion import (
    crear_esquema, crear_motor, fabrica_sesiones,
)
from src.infraestructura.adaptadores.salida.persistencia.tablas import (
    INDICE_CLAVE_NATURAL, NOMBRE_INDICE_CLAVE_NATURAL, NOMBRE_INDICE_CLAVE_NATURAL_ANTERIOR,
)

AHORA = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
ROSA = Usuario("rosa@pj.bo", "Rosa", Rol.VENDEDOR, "h", AHORA, codigo_punto_venta="rodriguez", id=7)
PEDRO = Usuario("pedro@pj.bo", "Pedro", Rol.VENDEDOR, "h", AHORA, codigo_punto_venta="rodriguez", id=9)
TERE = Usuario("tere@pj.bo", "Tere", Rol.VENDEDOR, "h", AHORA, codigo_punto_venta="villafatima", id=10)
TIENDERA = Usuario("lu@pj.bo", "Lu", Rol.VENDEDOR, "h", AHORA, codigo_punto_venta="minimarket_sopocachi", id=11)
ANA = Usuario("ana@pj.bo", "Ana", Rol.USUARIO, "h", AHORA, id=2)
LUIS = Usuario("luis@pj.bo", "Luis", Rol.USUARIO, "h", AHORA, id=3)
ADMIN = Usuario("admin@pj.bo", "Admin", Rol.ADMINISTRADOR, "h", AHORA, id=1)


class Reloj:
    """La hora de las pruebas, que se puede adelantar para ver vencer una oferta."""

    def __init__(self):
        self.ahora = AHORA

    def __call__(self):
        return self.ahora


@pytest.fixture
def mundo(repositorios):
    productos, mercados, observaciones = repositorios
    puestos, ofertas, reloj = PuestosEnMemoria(), OfertasEnMemoria(), Reloj()
    motor = MotorFusion()
    casero = OfertasDelCasero(productos, mercados, observaciones, motor, ofertas, puestos, ahora=reloj)
    vigentes = VerOfertasVigentes(productos, mercados, observaciones, motor, ofertas, puestos, ahora=reloj)
    return {
        "productos": productos, "mercados": mercados, "observaciones": observaciones, "puestos": puestos,
        "ofertas": ofertas, "reloj": reloj, "motor": motor, "casero": casero, "vigentes": vigentes,
        "mi_puesto": MiPuestoCasoUso(mercados, puestos),
        "confirmar": ConfirmarOferta(ofertas, ahora=reloj),
        "revisar": RevisarOfertas(ofertas, productos, mercados),
    }


# --- el puesto ---------------------------------------------------------------------

def test_el_numero_del_puesto_se_escribe_de_una_sola_forma():
    assert normalizar_numero("  b-3 ") == "B-3"
    assert sorted(["10", "2", "B-1"], key=orden_de_numero) == ["2", "10", "B-1"]
    with pytest.raises(DatoInvalido):
        normalizar_numero("")
    with pytest.raises(DatoInvalido):
        normalizar_numero("14; drop")


def test_el_casero_registra_su_puesto_y_nadie_mas_toma_ese_numero(mundo):
    puesto = mundo["mi_puesto"].guardar(ROSA, "14", "Verduras Doña Rosa", ["hortaliza", "fruta"], "pasillo 2")
    assert puesto.titulo == "Puesto 14 · Verduras Doña Rosa"
    assert puesto.rubros == (Categoria.HORTALIZA, Categoria.FRUTA)
    # Corregir el suyo no crea otro.
    mundo["mi_puesto"].guardar(ROSA, "14", "Verduras Rosa", ["hortaliza"])
    assert len(mundo["puestos"].del_mercado("rodriguez")) == 1
    with pytest.raises(CodigoYaExiste):
        mundo["mi_puesto"].guardar(PEDRO, "14", "Otro", [])


def test_un_puesto_va_solo_en_un_mercado(mundo):
    with pytest.raises(DatoInvalido, match="no un mercado"):
        mundo["mi_puesto"].guardar(TIENDERA, "1", "Caja", [])


def test_el_precio_del_casero_queda_anotado_con_su_puesto(mundo):
    mundo["mi_puesto"].guardar(ROSA, "14", "Verduras", [])
    PublicarPrecioPropio(mundo["productos"], mundo["mercados"], mundo["observaciones"], mundo["puestos"]).ejecutar(
        ROSA, "tomate", 6.0, Presentacion.KILO,
    )
    propia = next(o for o in mundo["observaciones"].buscar("tomate", "rodriguez") if o.fuente is Fuente.VENDEDOR)
    assert propia.puesto == "14"


# --- la oferta con candado ---------------------------------------------------------

def test_una_oferta_mas_barata_que_el_sistema_se_publica_y_vence_sola(mundo):
    # El tomate en el Rodríguez anda por Bs 14 el kilo (campo y un comprador).
    mundo["mi_puesto"].guardar(ROSA, "14", "Verduras", [])
    oferta = mundo["casero"].publicar(ROSA, "tomate", 10.0, Presentacion.KILO, horas=24, nota="hasta agotar")
    assert oferta.numero_puesto == "14"
    assert oferta.hasta - oferta.desde == timedelta(hours=24)

    (vista,) = mundo["vigentes"].ejecutar()
    assert vista.ahorro_por_unidad == pytest.approx(vista.precio_sistema.rango.centro - 10.0, abs=0.01)
    assert vista.puesto.numero == "14"

    mundo["reloj"].ahora = AHORA + timedelta(hours=25)
    assert mundo["vigentes"].ejecutar() == []
    assert mundo["casero"].mias(ROSA)[0].estado == "vencida"


def test_si_no_es_mas_barata_no_es_oferta(mundo):
    with pytest.raises(OfertaNoPermitida, match="no es más barato"):
        mundo["casero"].publicar(ROSA, "tomate", 30.0, Presentacion.KILO, horas=48)


def test_sin_un_precio_contra_el_cual_comparar_no_hay_oferta(mundo):
    # Nadie midió arroz en Villa Fátima y no hay referencia de ciudad.
    with pytest.raises(OfertaNoPermitida, match="contra el cual comparar"):
        mundo["casero"].publicar(TERE, "arroz", 1.0, Presentacion.KILO, horas=48)


def test_la_duracion_es_24_48_o_72_horas(mundo):
    with pytest.raises(DatoInvalido):
        mundo["casero"].publicar(ROSA, "tomate", 10.0, Presentacion.KILO, horas=240)


def test_maximo_tres_activas_por_casero(mundo):
    for monto in (10.0, 11.0, 12.0):
        mundo["casero"].publicar(ROSA, "tomate", monto, Presentacion.KILO, horas=24)
    with pytest.raises(OfertaNoPermitida, match="3 ofertas activas"):
        mundo["casero"].publicar(ROSA, "tomate", 9.0, Presentacion.KILO, horas=24)
    # Retirar una libera el cupo.
    mundo["casero"].retirar(ROSA, mundo["casero"].mias(ROSA)[0].oferta.id)
    mundo["casero"].publicar(ROSA, "tomate", 9.0, Presentacion.KILO, horas=24)


def test_el_ahorro_se_mide_sin_la_voz_del_propio_casero(mundo):
    # En Villa Fátima un medio vio el tomate a Bs 6 la libra (13 el kilo).
    # Tere declara 40 el kilo y después "oferta" a 20: con su voz, el
    # sistema la vería más barata; sin su voz, no lo es.
    PublicarPrecioPropio(mundo["productos"], mundo["mercados"], mundo["observaciones"]).ejecutar(
        TERE, "tomate", 40.0, Presentacion.KILO,
    )
    with pytest.raises(OfertaNoPermitida):
        mundo["casero"].publicar(TERE, "tomate", 20.0, Presentacion.KILO, horas=24)


def test_las_ofertas_se_ordenan_por_el_ahorro_real(mundo):
    mundo["casero"].publicar(ROSA, "tomate", 13.0, Presentacion.KILO, horas=24)
    mundo["casero"].publicar(PEDRO, "tomate", 8.0, Presentacion.KILO, horas=24)
    vistas = mundo["vigentes"].ejecutar()
    assert [v.oferta.id_vendedor for v in vistas] == [PEDRO.id, ROSA.id]
    assert vistas[0].ahorro_relativo > vistas[1].ahorro_relativo


def test_solo_el_dueno_retira_su_oferta(mundo):
    oferta = mundo["casero"].publicar(ROSA, "tomate", 10.0, Presentacion.KILO, horas=24)
    with pytest.raises(OfertaNoEncontrada):
        mundo["casero"].retirar(PEDRO, oferta.id)


# --- ¿Lo viste así? ----------------------------------------------------------------

def test_dos_desmentidos_de_personas_distintas_la_pausan(mundo):
    oferta = mundo["casero"].publicar(ROSA, "tomate", 10.0, Presentacion.KILO, horas=24)
    r = mundo["confirmar"].ejecutar(ANA, oferta.id, la_vio_asi=False)
    assert not r.pausada
    # La misma persona dos veces es un desmentido, no dos.
    r = mundo["confirmar"].ejecutar(ANA, oferta.id, la_vio_asi=False)
    assert (r.desmintieron, r.pausada) == (1, False)
    r = mundo["confirmar"].ejecutar(LUIS, oferta.id, la_vio_asi=False)
    assert r.pausada
    assert mundo["vigentes"].ejecutar() == []

    (pendiente,) = mundo["revisar"].pendientes(ADMIN)
    assert pendiente.desmintieron == 2
    mundo["revisar"].reactivar(ADMIN, oferta.id)
    assert len(mundo["vigentes"].ejecutar()) == 1


def test_quien_cambia_de_opinion_cuenta_lo_ultimo(mundo):
    oferta = mundo["casero"].publicar(ROSA, "tomate", 10.0, Presentacion.KILO, horas=24)
    mundo["confirmar"].ejecutar(ANA, oferta.id, la_vio_asi=False)
    r = mundo["confirmar"].ejecutar(ANA, oferta.id, la_vio_asi=True)
    assert (r.confirmaron, r.desmintieron) == (1, 0)


def test_el_casero_no_confirma_su_propia_oferta(mundo):
    oferta = mundo["casero"].publicar(ROSA, "tomate", 10.0, Presentacion.KILO, horas=24)
    with pytest.raises(OfertaNoPermitida):
        mundo["confirmar"].ejecutar(ROSA, oferta.id, la_vio_asi=True)


def test_una_oferta_vencida_ya_no_se_confirma(mundo):
    oferta = mundo["casero"].publicar(ROSA, "tomate", 10.0, Presentacion.KILO, horas=24)
    mundo["reloj"].ahora = AHORA + timedelta(days=2)
    with pytest.raises(OfertaNoEncontrada):
        mundo["confirmar"].ejecutar(ANA, oferta.id, la_vio_asi=True)


def test_hay_que_pausar_cuenta_personas_no_respuestas():
    no = [Confirmacion(1, 5, False, AHORA), Confirmacion(1, 5, False, AHORA), Confirmacion(1, 6, True, AHORA)]
    assert not hay_que_pausar(no)
    assert hay_que_pausar(no + [Confirmacion(1, 8, False, AHORA)])


def test_solo_el_administrador_revisa(mundo):
    from src.dominio.excepciones import PermisoDenegado
    with pytest.raises(PermisoDenegado):
        mundo["revisar"].pendientes(ANA)


# --- la ficha del mercado (C134) ---------------------------------------------------

def _ipc(producto, monto):
    return Observacion(
        fuente=Fuente.SIIP_IPC, nivel=NivelPrecio.MINORISTA, codigo_producto=producto, codigo_mercado=None,
        ciudad="la_paz", ambito=Ambito.CIUDAD, periodo=Periodo(2026, 9), precio=Dinero(monto, Unidad("KILO")),
        capturada_en=AHORA,
    )


def _campo(producto, monto, puesto, quien="ana"):
    return Observacion(
        fuente=Fuente.CAMPO, nivel=NivelPrecio.MINORISTA, codigo_producto=producto, codigo_mercado="rodriguez",
        periodo=Periodo(2026, 10, 17), precio=Dinero(monto, Unidad("KILO")), capturada_en=AHORA,
        fecha_observacion=date(2026, 10, 17), informante=f"campo:{quien}:puesto:{puesto}", puesto=puesto,
    )


def test_la_ficha_trae_cada_producto_sus_puestos_y_sus_ofertas(mundo):
    mundo["observaciones"].guardar_varias([_ipc("arroz", 8.0), _campo("papa", 7.0, "22")])
    mundo["mi_puesto"].guardar(ROSA, "14", "Verduras Doña Rosa", ["hortaliza"])
    mundo["casero"].publicar(ROSA, "tomate", 10.0, Presentacion.KILO, horas=24)
    ficha = FichaMercado(mundo["productos"], mundo["mercados"], mundo["observaciones"], mundo["motor"],
                         mundo["puestos"], mundo["vigentes"]).ejecutar("rodriguez")

    por_producto = {p.producto.codigo: p for p in ficha.precios}
    assert set(por_producto) == {"tomate", "papa", "arroz"}
    assert ficha.observados == 3 and ficha.estimados == 0
    # Arroz: medido a 8,20 (un medio) frente a 8 de la ciudad.
    assert por_producto["arroz"].diferencia == pytest.approx(8.2 / 8.0 - 1, abs=0.001)

    numeros = [(p.puesto.numero, p.registrado) for p in ficha.puestos]
    assert numeros == [("14", True), ("22", False)]
    assert ficha.puestos[0].ofertas[0].producto.codigo == "tomate"
    assert [(x.producto.codigo, x.fuente) for x in ficha.puestos[1].precios] == [("papa", "campo")]
    assert len(ficha.ofertas) == 1


def test_el_directorio_cuenta_puestos_y_ofertas(mundo):
    mundo["mi_puesto"].guardar(ROSA, "14", "Verduras", [])
    mundo["casero"].publicar(ROSA, "tomate", 10.0, Presentacion.KILO, horas=24)
    entradas = {x.mercado.codigo: x for x in DirectorioMercados(
        mundo["mercados"], mundo["puestos"], mundo["vigentes"]).ejecutar()}
    assert (entradas["rodriguez"].puestos, entradas["rodriguez"].ofertas) == (1, 1)
    assert (entradas["lanza"].puestos, entradas["lanza"].ofertas) == (0, 0)


# --- planilla de campo con puesto (A4200) --------------------------------------------

def test_la_planilla_anota_el_puesto_y_cada_puesto_es_una_voz(repositorios):
    productos, mercados, observaciones = repositorios
    fila = {"fecha": "2026-10-17", "mercado": "rodriguez", "producto": "papa", "monto": "7",
            "presentacion": "kilo", "observador": "Ana"}
    r = ImportarCotizacionesCampo(productos, mercados, observaciones).ejecutar(
        ADMIN, [dict(fila, puesto="14"), dict(fila, puesto=" b-3 "), dict(fila, puesto="??")], date(2026, 10, 18),
    )
    # El mismo precio el mismo día en dos puestos son dos hechos, no uno.
    assert r.guardadas == 2
    assert [f.fila for f in r.rechazadas] == [4]
    campo = [o for o in observaciones.buscar("papa", "rodriguez") if o.fuente is Fuente.CAMPO]
    assert sorted(o.informante for o in campo) == ["campo:ana:puesto:14", "campo:ana:puesto:B-3"]


# --- persistencia ------------------------------------------------------------------

def _sqlite():
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    return motor, fabrica_sesiones(motor)


def test_puestos_y_ofertas_se_guardan_en_la_base():
    _, fabrica = _sqlite()
    puestos, ofertas = PuestosPostgres(fabrica), OfertasPostgres(fabrica)
    p = puestos.guardar(Puesto("rodriguez", "10", "Carnes", (Categoria.CARNE,), "fondo", id_vendedor=7))
    puestos.guardar(Puesto("rodriguez", "2", "Frutas"))
    assert [x.numero for x in puestos.del_mercado("rodriguez")] == ["2", "10"]
    assert puestos.del_vendedor(7).rubros == (Categoria.CARNE,)
    assert puestos.contar_por_mercado() == {"rodriguez": 2}
    assert puestos.obtener_por_numero("rodriguez", "10").id == p.id

    o = ofertas.guardar(Oferta.nueva(id_vendedor=7, codigo_mercado="rodriguez", codigo_producto="tomate", monto=5,
                                     presentacion=Presentacion.KILO, horas=24, ahora=AHORA, numero_puesto="10"))
    assert [x.id for x in ofertas.vigentes(AHORA + timedelta(hours=1))] == [o.id]
    assert ofertas.vigentes(AHORA + timedelta(hours=30)) == []
    ofertas.guardar_confirmacion(Confirmacion(o.id, 2, False, AHORA))
    ofertas.guardar_confirmacion(Confirmacion(o.id, 2, True, AHORA))
    assert [c.la_vio_asi for c in ofertas.confirmaciones([o.id])[o.id]] == [True]
    ofertas.guardar(o.a_revision())
    assert [x.estado for x in ofertas.en_revision()] == [EstadoOferta.EN_REVISION]


def test_el_numero_de_puesto_es_unico_en_su_mercado_en_la_base():
    _, fabrica = _sqlite()
    puestos = PuestosPostgres(fabrica)
    puestos.guardar(Puesto("rodriguez", "10", "Carnes"))
    puestos.guardar(Puesto("lanza", "10", "Otro mercado, mismo número"))
    with pytest.raises(Exception):
        puestos.guardar(Puesto("rodriguez", "10", "Repetido"))


def test_el_indice_viejo_de_la_clave_natural_se_reemplaza_al_arrancar():
    motor, fabrica = _sqlite()
    with motor.begin() as c:
        c.execute(text(f"DROP INDEX IF EXISTS {NOMBRE_INDICE_CLAVE_NATURAL}"))
        c.execute(text(INDICE_CLAVE_NATURAL.replace(NOMBRE_INDICE_CLAVE_NATURAL, NOMBRE_INDICE_CLAVE_NATURAL_ANTERIOR)
                       .replace("coalesce(informante, ''), coalesce(puesto, ''), ", "")))
    crear_esquema(motor)
    with motor.connect() as c:
        nombres = {f[0] for f in c.execute(text("SELECT name FROM sqlite_master WHERE type = 'index'"))}
    assert NOMBRE_INDICE_CLAVE_NATURAL in nombres
    assert NOMBRE_INDICE_CLAVE_NATURAL_ANTERIOR not in nombres
    # Y con el índice nuevo, dos puestos al mismo precio conviven.
    repo = ObservacionesPostgres(fabrica)
    assert repo.guardar_varias([_campo("papa", 7.0, "14"), _campo("papa", 7.0, "15")]) == 2


# --- API pública -------------------------------------------------------------------

def test_la_api_publica_de_mercados_y_ofertas_responde():
    with TestClient(app) as cliente:
        assert cliente.get("/api/v1/ofertas").status_code == 200
        directorio = cliente.get("/api/v1/mercados/directorio")
        assert directorio.status_code == 200
        assert {"mercado", "puestos", "ofertas", "sectores"} <= set(directorio.json()[0])
        ficha = cliente.get("/api/v1/mercados/rodriguez/ficha")
        assert ficha.status_code == 200
        assert ficha.json()["mercado"]["codigo"] == "rodriguez"
        assert ficha.json()["precios"]
        assert cliente.get("/api/v1/mercados/no_existe/ficha").status_code == 404


def test_confirmar_y_publicar_piden_sesion():
    with TestClient(app) as cliente:
        assert cliente.post("/api/v1/ofertas/1/confirmar", json={"la_vio_asi": True}).status_code == 401
        assert cliente.post("/api/v1/vendedor/ofertas", json={
            "codigo_producto": "tomate", "monto": 5, "presentacion": "kilo", "horas": 24,
        }).status_code == 401


# --- C145: combos -------------------------------------------------------------------

def test_un_combo_junta_productos_y_cuenta_como_una_sola_oferta(mundo):
    publicadas = mundo["casero"].publicar_combo(
        ROSA, "Combo sopa", [("tomate", 1.0, Presentacion.KILO), ("papa", 0.5, Presentacion.KILO)], horas=48)
    assert {o.combo for o in publicadas} == {"Combo sopa"} and len(publicadas) == 2
    # El combo ocupa un cupo: quedan dos para ofertas sueltas.
    mundo["casero"].publicar(ROSA, "arroz", 1.0, Presentacion.KILO, horas=24)
    mundo["casero"].publicar(ROSA, "tomate", 1.5, Presentacion.KILO, horas=24)
    with pytest.raises(OfertaNoPermitida, match="un combo cuenta como una"):
        mundo["casero"].publicar(ROSA, "papa", 0.4, Presentacion.KILO, horas=24)
    combos = {v.oferta.combo for v in mundo["vigentes"].ejecutar(codigo_mercado="rodriguez")}
    assert "Combo sopa" in combos


def test_un_combo_con_un_precio_inflado_no_se_publica_entero(mundo):
    with pytest.raises(OfertaNoPermitida, match="no es más barato"):
        mundo["casero"].publicar_combo(
            ROSA, "Combo caro", [("tomate", 1.0, Presentacion.KILO), ("papa", 999.0, Presentacion.KILO)], horas=48)
    assert mundo["casero"].mias(ROSA) == [], "ni el tomate quedó publicado: o va entero o nada"


@pytest.mark.parametrize("nombre, renglones", [
    ("", [("tomate", 1.0), ("papa", 0.5)]),
    ("Solo uno", [("tomate", 1.0)]),
    ("Repetido", [("tomate", 1.0), ("tomate", 0.9)]),
])
def test_un_combo_mal_armado_se_rechaza(mundo, nombre, renglones):
    with pytest.raises(DatoInvalido):
        mundo["casero"].publicar_combo(ROSA, nombre, [(c, m, Presentacion.KILO) for c, m in renglones], horas=48)
