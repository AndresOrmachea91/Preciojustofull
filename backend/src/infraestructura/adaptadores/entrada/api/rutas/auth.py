from fastapi import APIRouter, Depends

from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.dependencias import (
    caso_iniciar_sesion, caso_registrar_usuario,
)
from src.infraestructura.adaptadores.entrada.api.mapeo import usuario_a_salida
from src.infraestructura.adaptadores.entrada.api.seguridad import usuario_actual

router = APIRouter(prefix="/auth", tags=["sesión"])


@router.post("/registro", response_model=e.UsuarioSalida, status_code=201)
def registrarse(cuerpo: e.RegistroEntrada, caso=Depends(caso_registrar_usuario)):
    """Crea una cuenta de usuario común. Los demás roles los asigna un administrador."""
    return usuario_a_salida(caso.registrarse(cuerpo.correo, cuerpo.nombre, cuerpo.contrasena))


@router.post("/ingresar", response_model=e.SesionSalida)
def ingresar(cuerpo: e.IngresoEntrada, caso=Depends(caso_iniciar_sesion)):
    """Devuelve un token para la cabecera `Authorization: Bearer <token>`."""
    sesion = caso.ejecutar(cuerpo.correo, cuerpo.contrasena)
    return e.SesionSalida(token=sesion.token, usuario=usuario_a_salida(sesion.usuario))


@router.get("/yo", response_model=e.UsuarioSalida)
def yo(usuario=Depends(usuario_actual)):
    """La cuenta de la sesión actual, con sus permisos vigentes."""
    return usuario_a_salida(usuario)
