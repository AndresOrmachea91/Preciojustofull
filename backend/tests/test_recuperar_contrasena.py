"""
Recuperar la contraseña por correo: el enlace llega, sirve una sola vez,
vence, no se confunde con un token de sesión y la respuesta no delata qué
correos existen.
"""
import re
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from src.aplicacion.casos_uso.cuentas.recuperar_contrasena import RecuperarContrasena
from src.dominio.excepciones import ContrasenaDebil, EnlaceInvalido
from src.dominio.modelo import Rol, Usuario
from src.infraestructura.adaptadores.entrada.api import dependencias
from src.infraestructura.adaptadores.entrada.api.main import app
from src.infraestructura.adaptadores.salida.correo.smtp import CorreoEnBitacora
from src.infraestructura.adaptadores.salida.memoria.cuentas import UsuariosEnMemoria
from src.infraestructura.adaptadores.salida.seguridad.cifrador import CifradorScrypt
from src.infraestructura.adaptadores.salida.seguridad.enlaces import EnlacesJwt
from src.infraestructura.adaptadores.salida.seguridad.tokens import EmisorJwt

SECRETO = "s" * 40
AHORA = datetime(2026, 10, 17, tzinfo=timezone.utc)


@pytest.fixture
def entorno():
    usuarios, cifrador, correo = UsuariosEnMemoria(), CifradorScrypt(), CorreoEnBitacora()
    ana = usuarios.guardar(Usuario("ana@pj.bo", "Ana", Rol.USUARIO, cifrador.cifrar("vieja1234"), AHORA))
    caso = RecuperarContrasena(usuarios, EnlacesJwt(SECRETO), correo, cifrador, "http://localhost:8088/")
    return caso, usuarios, cifrador, correo, ana


def _enlace(correo: CorreoEnBitacora) -> str:
    return re.search(r"token=(\S+)", correo.enviados[-1][2]).group(1)


def test_llega_un_enlace_que_cambia_la_contrasena_una_sola_vez(entorno):
    caso, usuarios, cifrador, correo, ana = entorno
    caso.solicitar("  ANA@pj.bo ")
    [(para, asunto, texto)] = correo.enviados
    assert para == "ana@pj.bo" and "contraseña" in asunto
    assert "http://localhost:8088/#/restablecer?token=" in texto

    token = _enlace(correo)
    caso.restablecer(token, "nueva1234")
    assert cifrador.verificar("nueva1234", usuarios.obtener(ana.id).hash_contrasena)

    with pytest.raises(EnlaceInvalido):   # ya se usó: la huella de la contraseña cambió
        caso.restablecer(token, "otra12345")


def test_un_correo_que_no_existe_no_manda_nada_ni_falla(entorno):
    caso, _, _, correo, _ = entorno
    caso.solicitar("nadie@pj.bo")
    caso.solicitar("no-es-un-correo")
    assert correo.enviados == []


def test_la_cuenta_desactivada_no_recupera(entorno):
    caso, usuarios, _, correo, ana = entorno
    caso.solicitar("ana@pj.bo")
    token = _enlace(correo)
    usuarios.guardar(usuarios.obtener(ana.id).con_activo(False))
    with pytest.raises(EnlaceInvalido):
        caso.restablecer(token, "nueva1234")


def test_enlaces_adulterados_vencidos_o_de_sesion_no_sirven(entorno):
    caso, _, _, _, ana = entorno
    with pytest.raises(EnlaceInvalido):
        caso.restablecer("cualquier.cosa.aqui", "nueva1234")
    vencido = EnlacesJwt(SECRETO, minutos_validez=-1).emitir(ana)
    with pytest.raises(EnlaceInvalido):
        caso.restablecer(vencido, "nueva1234")
    de_sesion = EmisorJwt(SECRETO).emitir(ana)   # mismo secreto, otro propósito
    with pytest.raises(EnlaceInvalido):
        caso.restablecer(de_sesion, "nueva1234")


def test_la_contrasena_nueva_cumple_las_reglas(entorno):
    caso, _, _, correo, _ = entorno
    caso.solicitar("ana@pj.bo")
    with pytest.raises(ContrasenaDebil):
        caso.restablecer(_enlace(correo), "corta")


@pytest.fixture
def cliente():
    dependencias._cuentas.cache_clear()
    dependencias._correo.cache_clear()
    dependencias.caso_registrar_usuario().crear_como_sistema("ana@pj.bo", "Ana", "vieja1234", Rol.USUARIO)
    with TestClient(app) as c:
        yield c
    dependencias._cuentas.cache_clear()
    dependencias._correo.cache_clear()


def test_api_misma_respuesta_exista_o_no_el_correo_y_flujo_completo(cliente):
    existe = cliente.post("/api/v1/auth/recuperar", json={"correo": "ana@pj.bo"})
    no_existe = cliente.post("/api/v1/auth/recuperar", json={"correo": "nadie@pj.bo"})
    assert existe.status_code == no_existe.status_code == 202
    assert existe.json() == no_existe.json()

    token = _enlace(dependencias._correo())
    assert cliente.post("/api/v1/auth/restablecer", json={"token": token, "contrasena": "nueva1234"}).status_code == 204
    r = cliente.post("/api/v1/auth/ingresar", json={"correo": "ana@pj.bo", "contrasena": "nueva1234"})
    assert r.status_code == 200
    r = cliente.post("/api/v1/auth/restablecer", json={"token": token, "contrasena": "otra12345"})
    assert r.status_code == 400 and "venció" in r.json()["detail"]
