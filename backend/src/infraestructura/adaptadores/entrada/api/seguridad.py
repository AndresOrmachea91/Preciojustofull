"""
Sesión en el borde HTTP: de la cabecera Authorization al usuario.

Solo traduce. Quién puede hacer qué lo deciden los casos de uso con la
matriz de permisos del dominio; acá únicamente se exige que haya una
sesión válida, y se traducen los errores del dominio a códigos HTTP.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.concurrency import run_in_threadpool

from src.infraestructura.adaptadores.entrada.api.dependencias import caso_resolver_sesion
from src.infraestructura.adaptadores.salida.persistencia.auditable import actor_actual
from src.dominio import excepciones as ex
from src.dominio.modelo import Usuario

# auto_error=False: la falta de token se responde con nuestro propio 401,
# no con el 403 que FastAPI devuelve por defecto.
_portador = HTTPBearer(auto_error=False, description="Token de /api/v1/auth/ingresar")


async def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_portador),
    resolver=Depends(caso_resolver_sesion),
) -> Usuario:
    usuario = (
        await run_in_threadpool(resolver.ejecutar, credenciales.credentials) if credenciales else None
    )
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inválida o vencida. Vuelva a ingresar.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Auditoría: todo lo que se guarde en esta petición queda a nombre de
    # este usuario. Es async a propósito: así el valor se fija en el
    # contexto de la petición y lo ven la ruta y los repositorios.
    actor_actual.set(usuario.correo)
    return usuario


class ActorPorPeticion:
    """
    Middleware ASGI: cada petición empieza como "anonimo". Sin esto, una
    conexión que se reutiliza (keep-alive) podría heredar el actor de la
    petición anterior y firmar cambios a nombre de otra persona.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        marca = actor_actual.set("anonimo")
        try:
            await self.app(scope, receive, send)
        finally:
            actor_actual.reset(marca)


_ESTADO_POR_ERROR: list[tuple[type[ex.ErrorDominio], int]] = [
    (ex.CredencialesInvalidas, status.HTTP_401_UNAUTHORIZED),
    (ex.PermisoDenegado, status.HTTP_403_FORBIDDEN),
    (ex.UsuarioNoEncontrado, status.HTTP_404_NOT_FOUND),
    (ex.ReporteNoEncontrado, status.HTTP_404_NOT_FOUND),
    (ex.ProductoNoEncontrado, status.HTTP_404_NOT_FOUND),
    (ex.MercadoNoEncontrado, status.HTTP_404_NOT_FOUND),
    (ex.CorreoYaRegistrado, status.HTTP_409_CONFLICT),
    (ex.ReporteYaRevisado, status.HTTP_409_CONFLICT),
    (ex.SinAdministradores, status.HTTP_409_CONFLICT),
    (ex.CodigoYaExiste, status.HTTP_409_CONFLICT),
    (ex.PuntoVentaConDependientes, status.HTTP_409_CONFLICT),
]


def estado_http(error: ex.ErrorDominio) -> int:
    for tipo, estado in _ESTADO_POR_ERROR:
        if isinstance(error, tipo):
            return estado
    return status.HTTP_400_BAD_REQUEST


async def manejar_error_dominio(_: Request, error: ex.ErrorDominio) -> JSONResponse:
    return JSONResponse(status_code=estado_http(error), content={"detail": str(error)})
