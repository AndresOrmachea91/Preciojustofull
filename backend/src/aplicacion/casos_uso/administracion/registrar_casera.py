"""
Registrar a una casera con puesto fijo (C144), desde el mercado.

Muchas caseras no se van a registrar solas: el administrador (o quien hace
la ronda de campo) las registra ahí mismo, en su puesto. La cuenta entra con
su número de celular (no hace falta correo) y una clave temporal que se le
anota en un papel; después la puede cambiar.

Todo se valida ANTES de crear la cuenta: si el número de puesto ya tiene
dueña o el mercado no existe, no queda una cuenta suelta sin puesto.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass

from src.aplicacion.casos_uso.cuentas.permisos import exigir
from src.aplicacion.casos_uso.cuentas.registrar_usuario import RegistrarUsuario
from src.aplicacion.casos_uso.vendedor.mi_puesto import MiPuestoCasoUso
from src.aplicacion.puertos.salida import LectorMercados, RepositorioPuestos, RepositorioUsuarios
from src.dominio.excepciones import CodigoYaExiste, DatoInvalido, MercadoNoEncontrado
from src.dominio.modelo import Permiso, Puesto, Rol, TipoPuntoVenta, Usuario
from src.dominio.modelo.puesto import normalizar_numero
from src.dominio.modelo.usuario import correo_de_celular

# Sin letras que se confunden al leerlas en un papel (l, 1, O, 0).
_LETRAS = "abcdefghjkmnpqrstuvwxyz"
_NUMEROS = "23456789"


def clave_temporal() -> str:
    """Ocho caracteres fáciles de dictar: cuatro letras y cuatro números."""
    return "".join(secrets.choice(_LETRAS) for _ in range(4)) + "".join(secrets.choice(_NUMEROS) for _ in range(4))


@dataclass(frozen=True, slots=True)
class CaseraRegistrada:
    usuario: Usuario
    puesto: Puesto
    celular: str
    # Se muestra UNA vez, al administrador, para que se la dé a la casera.
    clave_temporal: str


class RegistrarCasera:
    def __init__(self, registrar: RegistrarUsuario, mi_puesto: MiPuestoCasoUso, usuarios: RepositorioUsuarios,
                 mercados: LectorMercados, puestos: RepositorioPuestos):
        self._registrar = registrar
        self._mi_puesto = mi_puesto
        self._usuarios = usuarios
        self._mercados = mercados
        self._puestos = puestos

    def ejecutar(self, actor: Usuario, *, nombre: str, celular: str, codigo_mercado: str, numero: str,
                 nombre_puesto: str = "", rubros: list[str] | None = None, referencia: str = "") -> CaseraRegistrada:
        exigir(actor, Permiso.GESTIONAR_USUARIOS)
        nombre = " ".join((nombre or "").split())
        if not nombre:
            raise DatoInvalido("Escriba el nombre de la casera")
        correo = correo_de_celular(celular)
        numero = normalizar_numero(numero) if (numero or "").strip() else ""
        if not numero:
            raise DatoInvalido("Escriba el número del puesto")

        # Primero lo que puede fallar, sin tocar nada.
        mercado = self._mercados.obtener(codigo_mercado)
        if mercado is None:
            raise MercadoNoEncontrado(codigo_mercado)
        if mercado.tipo is not TipoPuntoVenta.MERCADO:
            raise DatoInvalido(f"{mercado.nombre} no es un mercado: las caseras con puesto fijo están en un mercado")
        ocupado = self._puestos.obtener_por_numero(mercado.codigo, numero)
        if ocupado is not None and ocupado.id_vendedor is not None:
            raise CodigoYaExiste("puesto en este mercado", numero)
        if self._usuarios.obtener_por_correo(correo) is not None:
            raise DatoInvalido(f"El celular {correo.split('@')[0]} ya tiene una cuenta: búsquela en Usuarios")

        clave = clave_temporal()
        casera = self._registrar.crear(actor, correo, nombre, clave, Rol.VENDEDOR)
        puesto = self._mi_puesto.guardar(casera, numero, nombre_puesto.strip(), rubros or [], referencia.strip(),
                                         mercado.codigo)
        return CaseraRegistrada(usuario=self._usuarios.obtener_por_correo(correo) or casera, puesto=puesto,
                                celular=correo.split("@")[0], clave_temporal=clave)
