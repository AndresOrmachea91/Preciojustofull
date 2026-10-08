"""
Auditoría: TODAS las tablas llevan creado_en, creado_por, modificado_en,
modificado_por y eliminado, y se llenan solas con quién y cuándo.

Corre sobre SQLite (el mismo adaptador de SQLAlchemy que PostgreSQL), sin
servidor.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from src.dominio.modelo import Categoria, Fuente, NivelPrecio, Observacion, Producto, Rol
from src.dominio.valor import Dinero, Periodo, Unidad
from src.infraestructura.adaptadores.salida.persistencia.auditable import (
    COLUMNAS_AUDITORIA, como_actor,
)
from src.infraestructura.adaptadores.salida.persistencia.cuentas import UsuariosPostgres
from src.infraestructura.adaptadores.salida.persistencia.repositorios import (
    ObservacionesPostgres, ProductosPostgres,
)
from src.infraestructura.adaptadores.salida.persistencia.sesion import (
    crear_esquema, crear_motor, fabrica_sesiones,
)
from src.infraestructura.adaptadores.salida.persistencia.tablas import (
    ObservacionTabla, ProductoTabla, UsuarioTabla, metadata,
)


@pytest.fixture
def base(tmp_path):
    motor = crear_motor(f"sqlite:///{tmp_path / 'auditoria.db'}")
    crear_esquema(motor)
    return motor, fabrica_sesiones(motor)


def _fila(fabrica, tabla, clave):
    with fabrica() as s:
        return s.get(tabla, clave)


def test_todas_las_tablas_tienen_las_cinco_columnas_de_auditoria():
    faltan = {
        tabla.name: [c for c in COLUMNAS_AUDITORIA if c not in tabla.c]
        for tabla in metadata.sorted_tables
    }
    assert {t: f for t, f in faltan.items() if f} == {}


def test_crear_y_modificar_quedan_firmados(base):
    _, fabrica = base
    productos = ProductosPostgres(fabrica)

    with como_actor("ana@pj.bo"):
        productos.guardar(Producto("tomate", "Tomate", Categoria.HORTALIZA, 5))
    creado = _fila(fabrica, ProductoTabla, "tomate")
    assert creado.creado_por == "ana@pj.bo"
    assert creado.creado_en is not None
    assert creado.modificado_en is None and creado.modificado_por is None
    assert creado.eliminado is False

    with como_actor("admin@pj.bo"):
        productos.guardar(Producto("tomate", "Tomate perita", Categoria.HORTALIZA, 5))
    modificado = _fila(fabrica, ProductoTabla, "tomate")
    assert modificado.modificado_por == "admin@pj.bo"
    assert modificado.modificado_en is not None
    # La creación no cambia al modificar.
    assert modificado.creado_por == "ana@pj.bo"
    assert modificado.creado_en == creado.creado_en


def test_sin_actor_explicito_firma_sistema(base):
    _, fabrica = base
    ProductosPostgres(fabrica).guardar(Producto("papa", "Papa", Categoria.TUBERCULO, 60))
    assert _fila(fabrica, ProductoTabla, "papa").creado_por == "sistema"


def test_la_creacion_no_se_puede_modificar(base):
    _, fabrica = base
    ProductosPostgres(fabrica).guardar(Producto("papa", "Papa", Categoria.TUBERCULO, 60))
    with fabrica() as s:
        fila = s.get(ProductoTabla, "papa")
        fila.creado_por = "otra persona"
        with pytest.raises(ValueError, match="auditoría"):
            s.flush()


def test_los_insert_masivos_del_recolector_tambien_se_auditan(base):
    _, fabrica = base
    observacion = Observacion(
        fuente=Fuente.MEDIOS, nivel=NivelPrecio.MINORISTA, codigo_producto="tomate",
        codigo_mercado="rodriguez", periodo=Periodo(2026, 8, 15),
        precio=Dinero(10.0, Unidad("KILO")), capturada_en=datetime.now(timezone.utc),
    )
    with como_actor("recolector-automatico"):
        assert ObservacionesPostgres(fabrica).guardar_varias([observacion]) == 1
    with fabrica() as s:
        fila = s.scalars(select(ObservacionTabla)).one()
    assert fila.creado_por == "recolector-automatico"
    assert fila.eliminado is False


def test_el_borrado_logico_oculta_la_fila_sin_borrarla(base):
    _, fabrica = base
    productos = ProductosPostgres(fabrica)
    productos.guardar(Producto("papa", "Papa", Categoria.TUBERCULO, 60))
    productos.guardar(Producto("tomate", "Tomate", Categoria.HORTALIZA, 5))
    with fabrica() as s:
        s.get(ProductoTabla, "papa").eliminado = True
        s.commit()

    assert productos.obtener("papa") is None
    assert [p.codigo for p in productos.listar()] == ["tomate"]
    assert _fila(fabrica, ProductoTabla, "papa") is not None   # sigue en la base


def test_un_usuario_eliminado_no_puede_ingresar_ni_cuenta_como_admin(base):
    from src.dominio.modelo import Usuario
    _, fabrica = base
    usuarios = UsuariosPostgres(fabrica)
    u = usuarios.guardar(Usuario("a@pj.bo", "A", Rol.ADMINISTRADOR, "h", datetime.now(timezone.utc)))
    with fabrica() as s:
        s.get(UsuarioTabla, u.id).eliminado = True
        s.commit()
    assert usuarios.obtener(u.id) is None
    assert usuarios.obtener_por_correo("a@pj.bo") is None
    assert usuarios.contar_administradores_activos() == 0


def test_la_migracion_audita_las_filas_historicas_con_su_fecha_real(base):
    motor, fabrica = base
    capturada = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)
    with motor.begin() as c:
        c.execute(text(
            "INSERT INTO observacion_precio (fuente, nivel, codigo_producto, codigo_mercado, anio, mes, dia, "
            "precio_monto, unidad_texto, cantidad, variedad, tipo_precio, reputacion_informante, ambito, "
            "capturada_en, creado_en, creado_por, eliminado) VALUES ('siip_diario', 'mayorista', 'tomate', NULL, "
            "2026, 8, 24, 10, 'KILO', 1, 'desconocida', 'desconocido', 1, 'ciudad', :c, :c, 'x', 0)"
        ), {"c": capturada})
        # Se simula una base de antes de la auditoría: sin las 5 columnas.
        for columna in COLUMNAS_AUDITORIA:
            c.execute(text(f"ALTER TABLE observacion_precio DROP COLUMN {columna}"))

    crear_esquema(motor)

    with motor.connect() as c:
        fila = c.execute(text("SELECT creado_en, creado_por, eliminado FROM observacion_precio")).one()
    assert fila.creado_por == "sistema"
    assert not fila.eliminado
    assert str(fila.creado_en).startswith("2026-08-24 12:00")


def test_la_api_firma_con_el_correo_de_la_sesion(tmp_path, monkeypatch):
    from src.configuracion import config
    from src.infraestructura.adaptadores.entrada.api import dependencias
    from src.infraestructura.adaptadores.entrada.api.main import app

    url = f"sqlite:///{tmp_path / 'api.db'}"
    monkeypatch.setattr(config, "base_datos_url", url)
    for cache in (dependencias._fabrica, dependencias._repositorios, dependencias._cuentas):
        cache.cache_clear()
    try:
        dependencias.caso_registrar_usuario().crear_como_sistema(
            "admin@pj.bo", "Admin", "clave1234", Rol.ADMINISTRADOR,
        )
        with TestClient(app) as cliente:
            cliente.post("/api/v1/auth/registro", json={"correo": "ana@pj.bo", "contrasena": "clave1234"})
            token = cliente.post("/api/v1/auth/ingresar",
                                 json={"correo": "admin@pj.bo", "contrasena": "clave1234"}).json()["token"]
            cabecera = {"Authorization": f"Bearer {token}"}
            vend = cliente.post("/api/v1/admin/usuarios", headers=cabecera, json={
                "correo": "vend@pj.bo", "contrasena": "clave1234", "rol": "vendedor"}).json()
            cliente.patch(f"/api/v1/admin/usuarios/{vend['id']}", headers=cabecera, json={"activo": False})

        fabrica = dependencias._fabrica()
        with fabrica() as s:
            firmas = {u.correo: (u.creado_por, u.modificado_por) for u in s.scalars(select(UsuarioTabla))}
        assert firmas == {
            "admin@pj.bo": ("sistema", None),
            "ana@pj.bo": ("autoregistro", None),
            "vend@pj.bo": ("admin@pj.bo", "admin@pj.bo"),
        }
    finally:
        for cache in (dependencias._fabrica, dependencias._repositorios, dependencias._cuentas):
            cache.cache_clear()
