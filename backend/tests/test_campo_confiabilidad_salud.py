"""
C127 importación de campo, C130 backtest del estimador, C131 límite de
intentos y C132 panel de salud.
"""
import json
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from src.aplicacion.casos_uso.administracion.importar_campo import ImportarCotizacionesCampo
from src.aplicacion.casos_uso.administracion.salud_sistema import VerSaludSistema
from src.aplicacion.casos_uso.precios.evaluar_estimador import EvaluarEstimador
from src.dominio.excepciones import PermisoDenegado
from src.dominio.modelo import (
    Categoria, DatosSalud, EstadoRespaldo, Fuente, Mercado, NivelPrecio, Observacion, Producto, Rol,
    TipoPuntoVenta, UltimaRecoleccion, Usuario,
)
from src.dominio.servicio.motor_fusion import MotorFusion
from src.dominio.valor import Ambito, Dinero, Periodo, Unidad
from src.infraestructura.adaptadores.entrada.api.limite_intentos import LimitadorIntentos, Regla
from src.infraestructura.adaptadores.salida.memoria.repositorios import (
    MercadosEnMemoria, ObservacionesEnMemoria, ProductosEnMemoria,
)
from src.infraestructura.adaptadores.salida.respaldos.estado_archivo import RespaldosEnArchivo

HOY = date(2026, 10, 17)
AHORA = datetime(2026, 10, 17, 15, tzinfo=timezone.utc)
ADMIN = Usuario(id=1, correo="admin@pj.bo", nombre="Admin", rol=Rol.ADMINISTRADOR, hash_contrasena="x", creado_en=AHORA)
COMPRADORA = Usuario(id=2, correo="ana@pj.bo", nombre="Ana", rol=Rol.USUARIO, hash_contrasena="x", creado_en=AHORA)

PAPA = Producto("papa", "Papa", Categoria.TUBERCULO)
RODRIGUEZ = Mercado("rodriguez", "Mercado Rodríguez", TipoPuntoVenta.MERCADO, "Centro", -16.5, -68.13, 1.10)
LANZA = Mercado("lanza", "Mercado Lanza", TipoPuntoVenta.MERCADO, "Centro", -16.49, -68.13, 0.90)


def _repos(observaciones=()):
    return (ProductosEnMemoria([PAPA]), MercadosEnMemoria([RODRIGUEZ, LANZA]),
            ObservacionesEnMemoria(list(observaciones)))


# --- C127: importación de campo --------------------------------------------------

def _fila(**cambios):
    fila = {"fecha": "2026-10-15", "mercado": "rodriguez", "producto": "papa", "monto": "8,50",
            "presentacion": "kilo", "observador": "Ana"}
    fila.update(cambios)
    return fila


def test_importa_las_filas_buenas_y_explica_las_malas():
    p, m, o = _repos()
    caso = ImportarCotizacionesCampo(p, m, o)
    resultado = caso.ejecutar(ADMIN, [
        _fila(),
        _fila(mercado="no_existe"),
        _fila(presentacion="litro"),
        _fila(fecha="2026-12-01"),
        _fila(monto="caro"),
    ], HOY)
    assert (resultado.leidas, resultado.validas, resultado.guardadas) == (5, 1, 1)
    assert [r.fila for r in resultado.rechazadas] == [3, 4, 5, 6]
    assert "no existe el mercado" in resultado.rechazadas[0].motivo.lower()
    guardada = o.buscar("papa")[0]
    assert guardada.fuente is Fuente.CAMPO
    assert guardada.precio_canonico() == 8.5
    assert guardada.informante == "campo:ana"


def test_solo_revisar_no_guarda_nada():
    p, m, o = _repos()
    resultado = ImportarCotizacionesCampo(p, m, o).ejecutar(ADMIN, [_fila()], HOY, solo_revisar=True)
    assert resultado.validas == 1 and resultado.guardadas == 0
    assert o.buscar("papa") == []


def test_solo_el_administrador_importa():
    with pytest.raises(PermisoDenegado):
        ImportarCotizacionesCampo(*_repos()).ejecutar(COMPRADORA, [_fila()], HOY)


def test_la_misma_planilla_dos_veces_no_duplica():
    p, m, o = _repos()
    caso = ImportarCotizacionesCampo(p, m, o)
    caso.ejecutar(ADMIN, [_fila()], HOY)
    assert caso.ejecutar(ADMIN, [_fila()], HOY).guardadas == 0


# --- C130: backtest del estimador ------------------------------------------------

def _ipc(monto, mes):
    return Observacion(
        fuente=Fuente.SIIP_IPC, nivel=NivelPrecio.MINORISTA, codigo_producto="papa", codigo_mercado=None,
        ciudad="la_paz", ambito=Ambito.CIUDAD, periodo=Periodo(2026, mes), precio=Dinero(monto, Unidad("KILO")),
        capturada_en=AHORA,
    )


def _campo(monto, mercado, mes, dia=10, quien="ana"):
    return Observacion(
        fuente=Fuente.CAMPO, nivel=NivelPrecio.MINORISTA, codigo_producto="papa", codigo_mercado=mercado,
        periodo=Periodo(2026, mes, dia), precio=Dinero(monto, Unidad("KILO")), capturada_en=AHORA,
        fecha_observacion=date(2026, mes, dia), informante=f"campo:{quien}",
    )


def test_el_backtest_mide_error_sesgo_y_cobertura_contra_lo_observado():
    # Ciudad a 10 Bs. Rodríguez (factor 1,10) estima 11 y se midió 11: acierto.
    # Lanza (factor 0,90) estima 9 y se midió 9,20: se quedó corto un 2,2 %.
    obs = [_ipc(10.0, 9), _campo(11.0, "rodriguez", 9), _campo(9.2, "lanza", 9)]
    ev = EvaluarEstimador(*_repos(obs), MotorFusion()).ejecutar()
    assert ev.casos == 2 and ev.mercados == 2
    assert ev.error_medio == pytest.approx((0.2 / 9.2) / 2, abs=1e-3)
    assert ev.sesgo == pytest.approx(-(0.2 / 9.2) / 2, abs=1e-3)
    assert ev.cobertura == 1.0
    # Sin factor (10 Bs en los dos) se equivocaría 9,1 % y 8,7 %: el factor ayuda.
    assert ev.error_medio_sin_factor == pytest.approx((1 / 11 + 0.8 / 9.2) / 2, abs=1e-3)
    assert ev.el_factor_ayuda is True


def test_el_backtest_solo_compara_el_mismo_mes():
    # La medición es de octubre y la ciudad solo tiene septiembre: no hay caso.
    ev = EvaluarEstimador(*_repos([_ipc(10.0, 9), _campo(11.0, "rodriguez", 10)]), MotorFusion()).ejecutar()
    assert ev.casos == 0 and ev.error_medio is None


# --- C131: límite de intentos ------------------------------------------------------

def test_el_limite_frena_y_avisa_cuanto_esperar():
    reloj = [0.0]
    limitador = LimitadorIntentos({"ingresar:correo": Regla(3, 60)}, reloj=lambda: reloj[0])
    for _ in range(3):
        limitador.registrar("ingresar:correo", "ana@pj.bo")
    with pytest.raises(HTTPException) as error:
        limitador.registrar("ingresar:correo", "ANA@pj.bo")
    assert error.value.status_code == 429
    assert error.value.headers["Retry-After"] == "60"
    reloj[0] = 61
    limitador.registrar("ingresar:correo", "ana@pj.bo")   # pasó la ventana


def test_un_ingreso_correcto_olvida_los_fallos():
    limitador = LimitadorIntentos({"ingresar:correo": Regla(2, 60)}, reloj=lambda: 0.0)
    limitador.registrar("ingresar:correo", "ana@pj.bo")
    limitador.registrar("ingresar:correo", "ana@pj.bo")
    limitador.olvidar("ingresar:correo", "ana@pj.bo")
    limitador.registrar("ingresar:correo", "ana@pj.bo")


def test_la_api_responde_429_al_pasarse(monkeypatch):
    from fastapi.testclient import TestClient
    from src.configuracion import config
    from src.infraestructura.adaptadores.entrada.api import limite_intentos
    from src.infraestructura.adaptadores.entrada.api.main import app

    monkeypatch.setattr(config, "limite_intentos_activo", True)
    monkeypatch.setattr(limite_intentos, "limitador", LimitadorIntentos())
    with TestClient(app) as cliente:
        codigos = [cliente.post("/api/v1/auth/ingresar", json={"correo": "nadie@pj.bo", "contrasena": "malaclave1"}).status_code
                   for _ in range(6)]
    assert codigos[:5] == [401] * 5
    assert codigos[5] == 429


# --- C132: salud del sistema ---------------------------------------------------------

class _SaludFija:
    def __init__(self, datos):
        self._datos = datos

    def leer(self, desde):
        return self._datos


class _RespaldoFijo:
    def __init__(self, estado):
        self._estado = estado

    def ultimo(self):
        return self._estado


def _respaldo(horas_atras=5, verificado=True):
    return EstadoRespaldo(AHORA - timedelta(hours=horas_atras), "x.dump", 1000, verificado, 120, None)


def test_todo_bien_cuando_recolecta_respalda_y_hay_observados():
    datos = DatosSalud(recolecciones=[UltimaRecoleccion("siip_ipc", AHORA - timedelta(hours=3), True, None, 40)],
                       pares_observados=10, pares_posibles=100)
    s = VerSaludSistema(_SaludFija(datos), _RespaldoFijo(_respaldo())).ejecutar(ADMIN, HOY, AHORA)
    assert [p.estado for p in s.puntos] == ["bien", "bien", "bien"]
    assert s.estado_general == "bien"
    assert s.cobertura_observada == 0.1


def test_un_respaldo_que_no_se_pudo_restaurar_pide_revisar():
    datos = DatosSalud(recolecciones=[UltimaRecoleccion("siip_ipc", AHORA, True, None, 0)],
                       pares_observados=10, pares_posibles=100)
    s = VerSaludSistema(_SaludFija(datos), _RespaldoFijo(_respaldo(verificado=False))).ejecutar(ADMIN, HOY, AHORA)
    assert s.puntos[1].estado == "revisar"
    assert s.estado_general == "revisar"


def test_recoleccion_vieja_y_sin_respaldos():
    datos = DatosSalud(recolecciones=[UltimaRecoleccion("siip_diario", AHORA - timedelta(days=3), True, None, 0)])
    s = VerSaludSistema(_SaludFija(datos), _RespaldoFijo(None)).ejecutar(ADMIN, HOY, AHORA)
    assert s.puntos[0].estado == "revisar"
    assert s.puntos[1].estado == "sin_datos"


def test_solo_el_administrador_ve_la_salud():
    with pytest.raises(PermisoDenegado):
        VerSaludSistema(_SaludFija(DatosSalud()), _RespaldoFijo(None)).ejecutar(COMPRADORA, HOY, AHORA)


def test_lee_el_estado_que_deja_el_script_de_respaldos(tmp_path):
    (tmp_path / "estado.json").write_text(json.dumps({
        "fecha": "2026-10-17T03:00:12-04:00", "archivo": "preciojusto_2026-10-17_0300.dump",
        "tamano_bytes": 52311, "verificado": True, "filas_observaciones": 8123, "detalle": "ok",
    }), encoding="utf-8")
    estado = RespaldosEnArchivo(tmp_path).ultimo()
    assert estado.verificado and estado.filas_observaciones == 8123 and estado.tamano_bytes == 52311
    assert estado.fecha.utcoffset() == timedelta(hours=-4)
    assert RespaldosEnArchivo(tmp_path / "no_hay").ultimo() is None


def test_la_salud_lee_la_base(tmp_path):
    from sqlalchemy import text
    from src.infraestructura.adaptadores.salida.persistencia.salud import SaludPostgres
    from src.infraestructura.adaptadores.salida.persistencia.sesion import (
        crear_esquema, crear_motor, fabrica_sesiones,
    )

    motor = crear_motor(f"sqlite:///{tmp_path / 'salud.db'}")
    crear_esquema(motor)
    ahora = datetime.now(timezone.utc)
    with motor.begin() as c:
        c.execute(text("INSERT INTO intento_fuente (fuente, exito, ocurrido_en, creado_en, creado_por, eliminado) "
                       "VALUES ('siip_ipc', 1, :a, :a, 'x', 0), ('siip_ipc', 0, :b, :b, 'x', 0)"),
                  {"a": ahora - timedelta(hours=2), "b": ahora})
    datos = SaludPostgres(fabrica_sesiones(motor)).leer(HOY - timedelta(days=30))
    (rec,) = datos.recolecciones
    assert rec.fuente == "siip_ipc" and rec.exito
    assert abs((rec.ocurrido_en - (ahora - timedelta(hours=2))).total_seconds()) < 2
