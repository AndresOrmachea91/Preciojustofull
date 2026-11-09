"""Administración de cuentas: /api/v1/admin/usuarios. Cada caso de uso exige gestionar_usuarios."""
from fastapi import APIRouter, Depends, Response, status

from src.infraestructura.adaptadores.entrada.api import esquemas as e
from src.infraestructura.adaptadores.entrada.api.dependencias import (
    caso_administrar_usuarios, caso_registrar_casera, caso_registrar_usuario,
)
from src.infraestructura.adaptadores.entrada.api.mapeo import usuario_a_salida, usuario_auditado_a_salida
from src.infraestructura.adaptadores.entrada.api.seguridad import usuario_actual
from src.dominio.modelo import Rol

router = APIRouter(prefix="/admin/usuarios", tags=["administración"])


@router.get("", response_model=list[e.UsuarioAuditadoSalida])
def listar(incluir_eliminados: bool = False, actor=Depends(usuario_actual),
           caso=Depends(caso_administrar_usuarios)):
    """Solo los vigentes; con ?incluir_eliminados=true también los eliminados lógicamente."""
    return [usuario_auditado_a_salida(u) for u in caso.listar(actor, incluir_eliminados)]


@router.delete("/{id_usuario}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(id_usuario: int, actor=Depends(usuario_actual), caso=Depends(caso_administrar_usuarios)):
    caso.eliminar(actor, id_usuario)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("", response_model=e.UsuarioSalida, status_code=201)
def crear(cuerpo: e.CrearUsuarioEntrada, actor=Depends(usuario_actual),
          caso=Depends(caso_registrar_usuario)):
    return usuario_a_salida(
        caso.crear(actor, cuerpo.correo, cuerpo.nombre, cuerpo.contrasena, Rol(cuerpo.rol))
    )


@router.post("/caseras", response_model=e.CaseraRegistradaSalida, status_code=201)
def registrar_casera(cuerpo: e.RegistrarCaseraEntrada, actor=Depends(usuario_actual),
                     caso=Depends(caso_registrar_casera)):
    """Registra a una casera con puesto fijo desde el mercado: entra con su celular y una clave temporal."""
    r = caso.ejecutar(actor, nombre=cuerpo.nombre, celular=cuerpo.celular, codigo_mercado=cuerpo.codigo_mercado,
                      numero=cuerpo.numero, nombre_puesto=cuerpo.nombre_puesto, rubros=cuerpo.rubros,
                      referencia=cuerpo.referencia)
    return e.CaseraRegistradaSalida(id_usuario=r.usuario.id, nombre=r.usuario.nombre, celular=r.celular,
                                    codigo_mercado=r.puesto.codigo_mercado, numero=r.puesto.numero,
                                    clave_temporal=r.clave_temporal)


@router.patch("/{id_usuario}", response_model=e.UsuarioSalida)
def actualizar(id_usuario: int, cuerpo: e.ActualizarUsuarioEntrada,
               actor=Depends(usuario_actual), caso=Depends(caso_administrar_usuarios)):
    rol = Rol(cuerpo.rol) if cuerpo.rol is not None else None
    cambios = {}
    # El punto de venta se cambia solo si vino en el cuerpo: null lo quita.
    if "codigo_punto_venta" in cuerpo.model_fields_set:
        cambios["punto_venta"] = cuerpo.codigo_punto_venta
    return usuario_a_salida(caso.actualizar(actor, id_usuario, rol=rol, activo=cuerpo.activo, **cambios))


@router.put("/{id_usuario}/contrasena", response_model=e.UsuarioSalida)
def restablecer_contrasena(id_usuario: int, cuerpo: e.ContrasenaEntrada,
                           actor=Depends(usuario_actual), caso=Depends(caso_administrar_usuarios)):
    return usuario_a_salida(caso.restablecer_contrasena(actor, id_usuario, cuerpo.contrasena))
