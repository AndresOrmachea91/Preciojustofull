"""Cuentas, comunes a todos los roles: /api/v1/auth/registro, /ingresar, /yo, /recuperar y /restablecer."""
from fastapi import APIRouter, Depends, Request, Response, status

from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.dependencias import (
    caso_iniciar_sesion, caso_recuperar_contrasena, caso_registrar_usuario,
)
from src.infraestructura.adaptadores.entrada.api.limite_intentos import contar, ip_de, limitador
from src.infraestructura.adaptadores.entrada.api.mapeo import usuario_a_salida
from src.infraestructura.adaptadores.entrada.api.seguridad import usuario_actual
from src.infraestructura.adaptadores.salida.persistencia.auditable import como_actor

router = APIRouter(prefix="/auth", tags=["cuentas"])


@router.post("/registro", response_model=e.UsuarioSalida, status_code=201)
def registrarse(cuerpo: e.RegistroEntrada, peticion: Request, caso=Depends(caso_registrar_usuario)):
    """Crea una cuenta de usuario común. Los demás roles los asigna un administrador."""
    contar("registro:ip", ip_de(peticion))
    # En la auditoría, la cuenta queda "creada por autoregistro".
    with como_actor("autoregistro"):
        return usuario_a_salida(caso.registrarse(cuerpo.correo, cuerpo.nombre, cuerpo.contrasena,
                                                 cuerpo.quiere_vender))


@router.post("/ingresar", response_model=e.SesionSalida)
def ingresar(cuerpo: e.IngresoEntrada, peticion: Request, caso=Depends(caso_iniciar_sesion)):
    """Devuelve un token para la cabecera `Authorization: Bearer <token>`."""
    contar("ingresar:ip", ip_de(peticion))
    contar("ingresar:correo", cuerpo.correo)
    sesion = caso.ejecutar(cuerpo.correo, cuerpo.contrasena)
    limitador.olvidar("ingresar:correo", cuerpo.correo)
    return e.SesionSalida(token=sesion.token, usuario=usuario_a_salida(sesion.usuario))


@router.get("/yo", response_model=e.UsuarioSalida)
def yo(usuario=Depends(usuario_actual)):
    """La cuenta de la sesión actual, con sus permisos vigentes."""
    return usuario_a_salida(usuario)


@router.post("/recuperar", status_code=202)
def recuperar(cuerpo: e.RecuperarEntrada, peticion: Request, caso=Depends(caso_recuperar_contrasena)):
    """Manda un enlace al correo, si hay una cuenta con él. La respuesta es la misma en los dos casos."""
    contar("recuperar:ip", ip_de(peticion))
    contar("recuperar:correo", cuerpo.correo)
    caso.solicitar(cuerpo.correo)
    return {"mensaje": "Si el correo está registrado, le llegará un enlace para elegir una contraseña nueva."}


@router.post("/restablecer", status_code=204)
def restablecer(cuerpo: e.RestablecerEntrada, caso=Depends(caso_recuperar_contrasena)):
    """Cambia la contraseña con el enlace del correo. El enlace deja de servir después."""
    with como_actor("recuperacion-por-correo"):
        caso.restablecer(cuerpo.token, cuerpo.contrasena)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
