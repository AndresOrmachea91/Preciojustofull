"""
Las tablas rol, permiso, rol_permiso, fuente y vendedor: reflejan al
dominio, se auditan como todas y la migración mueve el puesto del vendedor
sin perder a nadie.
"""
from datetime import datetime, timezone

from sqlalchemy import inspect, text

from src.dominio.modelo import Fuente, PERMISOS_POR_ROL, Permiso, Rol, Usuario
from src.infraestructura.adaptadores.salida.persistencia.auditable import COLUMNAS_AUDITORIA
from src.infraestructura.adaptadores.salida.persistencia.cuentas import UsuariosPostgres
from src.infraestructura.adaptadores.salida.persistencia.sesion import (
    crear_esquema, crear_motor, fabrica_sesiones,
)

AHORA = datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc)
NUEVAS = ("rol", "permiso", "rol_permiso", "fuente", "vendedor")


def _motor():
    motor = crear_motor("sqlite://")
    crear_esquema(motor)
    return motor


def _filas(motor, sql):
    with motor.connect() as c:
        return c.execute(text(sql)).all()


def test_las_tablas_nuevas_existen_y_heredan_la_auditoria():
    inspector = inspect(_motor())
    for tabla in NUEVAS:
        columnas = {c["name"] for c in inspector.get_columns(tabla)}
        assert set(COLUMNAS_AUDITORIA) <= columnas, tabla


def test_los_catalogos_son_los_del_dominio():
    motor = _motor()
    assert {r for (r,) in _filas(motor, "SELECT codigo FROM rol")} == {r.value for r in Rol}
    assert {p for (p,) in _filas(motor, "SELECT codigo FROM permiso")} == {p.value for p in Permiso}
    pares = set(_filas(motor, "SELECT codigo_rol, codigo_permiso FROM rol_permiso WHERE NOT eliminado"))
    assert pares == {(r.value, p.value) for r, ps in PERMISOS_POR_ROL.items() for p in ps}
    fuentes = dict(_filas(motor, "SELECT codigo, confianza_base FROM fuente"))
    assert fuentes == {f.value: f.confianza_base.name.lower() for f in Fuente}
    assert all(por == "sistema" for (por,) in _filas(motor, "SELECT creado_por FROM rol"))


def test_sincronizar_dos_veces_no_duplica_ni_marca_modificado():
    motor = _motor()
    crear_esquema(motor)
    assert _filas(motor, "SELECT count(*) FROM rol_permiso")[0][0] == sum(map(len, PERMISOS_POR_ROL.values()))
    assert _filas(motor, "SELECT count(*) FROM fuente WHERE modificado_en IS NOT NULL")[0][0] == 0


def test_un_permiso_quitado_a_mano_vuelve_y_uno_agregado_se_marca_eliminado():
    motor = _motor()
    with motor.begin() as c:
        c.execute(text("UPDATE rol_permiso SET eliminado = TRUE WHERE codigo_rol = 'usuario'"))
        c.execute(text("INSERT INTO rol_permiso (codigo_rol, codigo_permiso, creado_en, creado_por, eliminado) "
                       "VALUES ('usuario', 'gestionar_usuarios', CURRENT_TIMESTAMP, 'alguien', FALSE)"))
    crear_esquema(motor)
    vigentes = {p for (p,) in _filas(
        motor, "SELECT codigo_permiso FROM rol_permiso WHERE codigo_rol = 'usuario' AND NOT eliminado")}
    assert vigentes == {p.value for p in PERMISOS_POR_ROL[Rol.USUARIO]}


def test_el_puesto_del_vendedor_vive_en_su_tabla():
    motor = _motor()
    with motor.begin() as c:
        c.execute(text("INSERT INTO mercado (codigo, nombre, tipo, latitud, longitud, zona, macrodistrito, factor_mercado, creado_en, creado_por, "
                       "eliminado) VALUES ('rodriguez', 'Rodríguez', 'mercado', -16.5, -68.1, 'centro', 'centro', 1.0, "
                       "CURRENT_TIMESTAMP, 'test', FALSE)"))
    usuarios = UsuariosPostgres(fabrica_sesiones(motor))
    vend = usuarios.guardar(Usuario("v@pj.bo", "Vend", Rol.VENDEDOR, "h", AHORA))
    assert vend.codigo_punto_venta is None
    assert _filas(motor, "SELECT id_usuario, codigo_punto_venta, eliminado FROM vendedor") == [(vend.id, None, False)]

    vend = usuarios.guardar(vend.con_punto_venta("rodriguez"))
    assert usuarios.obtener(vend.id).codigo_punto_venta == "rodriguez"

    # Deja de ser vendedor y pierde el puesto: su fila no se borra, se marca.
    usuarios.guardar(vend.con_punto_venta(None).con_rol(Rol.USUARIO))
    assert _filas(motor, "SELECT eliminado FROM vendedor") == [(True,)]
    assert usuarios.obtener(vend.id).codigo_punto_venta is None
    # Un usuario común no tiene fila de vendedor.
    usuarios.guardar(Usuario("u@pj.bo", "Usu", Rol.USUARIO, "h", AHORA))
    assert _filas(motor, "SELECT count(*) FROM vendedor")[0][0] == 1


def test_la_migracion_mueve_el_puesto_viejo_a_vendedor():
    motor = crear_motor("sqlite://")
    with motor.begin() as c:
        c.execute(text("CREATE TABLE usuario (id INTEGER PRIMARY KEY, correo VARCHAR(255) NOT NULL, "
                       "nombre VARCHAR(255) NOT NULL, rol VARCHAR(16) NOT NULL, hash_contrasena VARCHAR(255) "
                       "NOT NULL, activo BOOLEAN NOT NULL, codigo_punto_venta VARCHAR(64))"))
        c.execute(text("INSERT INTO usuario VALUES (1, 'a@pj.bo', 'A', 'administrador', 'h', 1, NULL), "
                       "(2, 'v@pj.bo', 'V', 'recolector', 'h', 1, 'rodriguez'), "
                       "(3, 'u@pj.bo', 'U', 'usuario', 'h', 1, NULL)"))
    crear_esquema(motor)
    crear_esquema(motor)  # idempotente

    assert "codigo_punto_venta" not in {c["name"] for c in inspect(motor).get_columns("usuario")}
    assert _filas(motor, "SELECT id_usuario, codigo_punto_venta, creado_por FROM vendedor") == [
        (2, "rodriguez", "migracion"),
    ]
    assert usuarios_rol(motor) == {1: "administrador", 2: "vendedor", 3: "usuario"}


def usuarios_rol(motor):
    return dict(_filas(motor, "SELECT id, rol FROM usuario"))


def test_eliminar_al_usuario_elimina_tambien_su_parte_de_vendedor():
    motor = _motor()
    usuarios = UsuariosPostgres(fabrica_sesiones(motor))
    vend = usuarios.guardar(Usuario("v@pj.bo", "Vend", Rol.VENDEDOR, "h", AHORA))
    usuarios.eliminar(vend.id)
    assert _filas(motor, "SELECT eliminado FROM vendedor") == [(True,)]
