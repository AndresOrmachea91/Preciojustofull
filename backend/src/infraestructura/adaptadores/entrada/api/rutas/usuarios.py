"""Administración de cuentas. Cada caso de uso exige el permiso gestionar_usuarios."""
from fastapi import APIRouter, Depends

from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.dependencias import (
    caso_administrar_usuarios, caso_registrar_usuario,
)
from src.infraestructura.adaptadores.entrada.api.mapeo import usuario_a_salida
from src.infraestructura.adaptadores.entrada.api.seguridad import usuario_actual
from src.dominio.modelo import Rol

router = APIRouter(prefix="/usuarios", tags=["administración"])


@router.get("", response_model=list[e.UsuarioSalida])
def listar(actor=Depends(usuario_actual), caso=Depends(caso_administrar_usuarios)):
    return [usuario_a_salida(u) for u in caso.listar(actor)]


@router.post("", response_model=e.UsuarioSalida, status_code=201)
def crear(cuerpo: e.CrearUsuarioEntrada, actor=Depends(usuario_actual),
          caso=Depends(caso_registrar_usuario)):
    return usuario_a_salida(
        caso.crear(actor, cuerpo.correo, cuerpo.nombre, cuerpo.contrasena, Rol(cuerpo.rol))
    )


@router.patch("/{id_usuario}", response_model=e.UsuarioSalida)
def actualizar(id_usuario: int, cuerpo: e.ActualizarUsuarioEntrada,
               actor=Depends(usuario_actual), caso=Depends(caso_administrar_usuarios)):
    rol = Rol(cuerpo.rol) if cuerpo.rol is not None else None
    return usuario_a_salida(caso.actualizar(actor, id_usuario, rol=rol, activo=cuerpo.activo))


@router.put("/{id_usuario}/contrasena", response_model=e.UsuarioSalida)
def restablecer_contrasena(id_usuario: int, cuerpo: e.ContrasenaEntrada,
                           actor=Depends(usuario_actual), caso=Depends(caso_administrar_usuarios)):
    return usuario_a_salida(caso.restablecer_contrasena(actor, id_usuario, cuerpo.contrasena))
