#!/usr/bin/env python3
"""
Adaptador de entrada por línea de comandos: alta de administradores.

    python -m src.infraestructura.adaptadores.entrada.cli.crear_admin --correo admin@preciojusto.bo
    python -m src.infraestructura.adaptadores.entrada.cli.crear_admin --correo ana@x.bo --promover

Es la puerta de entrada del primer administrador: desde la web nadie se
puede nombrar administrador a sí mismo, así que la primera cuenta nace en
la consola del servidor, donde ya hace falta tener acceso.

La contraseña se pide por teclado y no se repite en pantalla, para que no
quede en el historial de la terminal. Con --promover, una cuenta que ya
existe pasa a ser administradora (y se reactiva si estaba desactivada).
"""
from __future__ import annotations

import argparse
import getpass
import logging
import os
import sys

from src.aplicacion.casos_uso.gestionar_usuarios import RegistrarUsuario
from src.dominio.excepciones import ErrorDominio
from src.dominio.modelo import Rol
from src.dominio.modelo.usuario import normalizar_correo
from src.infraestructura.adaptadores.salida.persistencia.cuentas import UsuariosPostgres
from src.infraestructura.adaptadores.salida.persistencia.sesion import (
    crear_esquema, crear_motor, fabrica_sesiones,
)
from src.infraestructura.adaptadores.salida.seguridad.cifrador import CifradorScrypt
from src.configuracion import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("crear_admin")


def _pedir_contrasena() -> str:
    # Para scripts y contenedores: la variable evita el teclado.
    desde_entorno = os.environ.get("ADMIN_CONTRASENA")
    if desde_entorno:
        return desde_entorno
    primera = getpass.getpass("Contraseña: ")
    if primera != getpass.getpass("Repita la contraseña: "):
        raise SystemExit("Las contraseñas no coinciden")
    return primera


def main() -> int:
    p = argparse.ArgumentParser(description="Crea o promueve una cuenta de administrador")
    p.add_argument("--correo", required=True)
    p.add_argument("--nombre", default="Administrador")
    p.add_argument("--promover", action="store_true",
                   help="Si la cuenta ya existe, la convierte en administradora")
    args = p.parse_args()

    if not config.base_datos_url:
        log.error("BASE_DATOS_URL no está configurada: no hay dónde guardar la cuenta.")
        return 2

    motor = crear_motor(config.base_datos_url)
    crear_esquema(motor)
    usuarios = UsuariosPostgres(fabrica_sesiones(motor))

    try:
        existente = usuarios.obtener_por_correo(normalizar_correo(args.correo))
        if existente is not None:
            if not args.promover:
                log.error("Ya existe la cuenta %s. Use --promover para hacerla administradora.",
                          existente.correo)
                return 1
            usuarios.guardar(existente.con_rol(Rol.ADMINISTRADOR).con_activo(True))
            print(f"{existente.correo} ahora es administrador.")
            return 0

        nuevo = RegistrarUsuario(usuarios, CifradorScrypt()).crear_como_sistema(
            args.correo, args.nombre, _pedir_contrasena(), Rol.ADMINISTRADOR,
        )
    except ErrorDominio as error:
        log.error("%s", error)
        return 1
    print(f"Administrador creado: {nuevo.correo} (id {nuevo.id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
