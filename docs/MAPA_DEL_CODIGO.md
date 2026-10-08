# Mapa del código: ¿dónde está cada cosa?

La estructura es Clean + Hexagonal. No hay una carpeta `/bd/usuario`: lo que
en otros proyectos sería esa carpeta está repartido por **responsabilidad**,
siempre en el mismo lugar para cada tema. Las rutas son relativas a `backend/src/`.

    dominio/           las reglas (qué es válido)              no sabe que existe una base
    aplicacion/        los casos de uso (qué se puede pedir)    pide cosas a través de puertos
    infraestructura/   el borde (HTTP, base de datos, SIIP)     implementa los puertos

Dentro de cada capa, lo de cada ROL está en su carpeta:

    aplicacion/casos_uso/       precios/  cuentas/  usuario/  vendedor/  administracion/
    api/rutas/                  publico/  cuentas.py  usuario/  vendedor/  administracion/
    frontend/src/ui/paginas/    publico/  cuentas/  usuario/  vendedor/  administracion/

| Rol            | Casos de uso                          | Rutas HTTP                   |
|----------------|---------------------------------------|------------------------------|
| (público)      | `aplicacion/casos_uso/precios/`       | `api/rutas/publico/` → `/api/v1/precios`, `/canasta`, `/productos`, `/mercados` |
| (todos)        | `aplicacion/casos_uso/cuentas/`       | `api/rutas/cuentas.py` → `/api/v1/auth/...` |
| usuario        | `aplicacion/casos_uso/usuario/`       | `api/rutas/usuario/` → `/api/v1/reportes` |
| vendedor       | `aplicacion/casos_uso/vendedor/`      | `api/rutas/vendedor/` → `/api/v1/vendedor/...` |
| administrador  | `aplicacion/casos_uso/administracion/`| `api/rutas/administracion/` → `/api/v1/admin/...` |

## Auditoría (las 5 columnas en todas las tablas)

| Qué                                              | Dónde |
|--------------------------------------------------|-------|
| `Auditable` (el `@MappedSuperclass` de Spring)   | `infraestructura/adaptadores/salida/persistencia/auditable.py` |
| Las tablas que lo heredan (`class X(Base, Auditable)`) | `infraestructura/adaptadores/salida/persistencia/tablas.py` |
| Quién hizo el cambio (`actor_actual`)            | `auditable.py`; la API la fija en `api/seguridad.py → usuario_actual` |
| Que un actor no pase de una petición a otra      | `api/seguridad.py → ActorPorPeticion` |
| Borrado lógico (no devolver `eliminado = true`)  | cada lectura de `persistencia/repositorios.py` y `persistencia/cuentas.py` |
| Agregar la auditoría a bases que ya existían     | `persistencia/sesion.py → crear_esquema` |
| Pruebas                                          | `backend/tests/test_auditoria.py` |

## La equivalencia con "/bd/..."

| Si buscas...                         | Está en                                                              |
|--------------------------------------|----------------------------------------------------------------------|
| `/bd/usuario` (consultas SQL)        | `infraestructura/adaptadores/salida/persistencia/cuentas.py` → `UsuariosPostgres` |
| `/bd/reporte` (consultas SQL)        | `infraestructura/adaptadores/salida/persistencia/cuentas.py` → `ReportesPostgres` |
| `/bd/precios`, productos, mercados   | `infraestructura/adaptadores/salida/persistencia/repositorios.py`   |
| Las tablas (columnas, índices)       | `infraestructura/adaptadores/salida/persistencia/tablas.py`         |
| La conexión y las migraciones        | `infraestructura/adaptadores/salida/persistencia/sesion.py`         |
| Lo mismo, pero sin base (en memoria) | `infraestructura/adaptadores/salida/memoria/`                       |

## Usuarios y sesiones, de punta a punta

Ejemplo: alguien ingresa con correo y contraseña.

| Paso | Qué pasa                                         | Archivo y función |
|------|--------------------------------------------------|-------------------|
| 1    | Llega `POST /api/v1/auth/ingresar`                | `infraestructura/adaptadores/entrada/api/rutas/cuentas.py` → `ingresar` |
| 2    | Se valida la forma del JSON (campos, largos)      | `infraestructura/adaptadores/entrada/api/esquemas.py` → `IngresoEntrada` |
| 3    | El caso de uso decide si las credenciales sirven  | `aplicacion/casos_uso/cuentas/iniciar_sesion.py` → `IniciarSesion.ejecutar` |
| 4    | Se normaliza el correo (reglas del negocio)       | `dominio/modelo/usuario.py` → `normalizar_correo` |
| 5    | Se busca el usuario **en la base**                | `infraestructura/adaptadores/salida/persistencia/cuentas.py` → `UsuariosPostgres.obtener_por_correo` |
| 6    | Se compara la contraseña con su hash              | `infraestructura/adaptadores/salida/seguridad/cifrador.py` → `CifradorScrypt.verificar` |
| 7    | Se firma el token de sesión                       | `infraestructura/adaptadores/salida/seguridad/tokens.py` → `EmisorJwt.emitir` |
| 8    | Un error del dominio se vuelve código HTTP        | `infraestructura/adaptadores/entrada/api/seguridad.py` → `estado_http` |

En cada petición protegida, `seguridad.py → usuario_actual` lee el token y
`cuentas/iniciar_sesion.py → ResolverSesion` vuelve a buscar al usuario en la base,
por eso desactivar una cuenta corta su sesión al instante.

## Las validaciones, una por una

| Validación                                         | Dónde |
|----------------------------------------------------|-------|
| Formato de correo                                  | `dominio/modelo/usuario.py` → `normalizar_correo` |
| Contraseña: 8 caracteres, letras y números         | `dominio/modelo/usuario.py` → `validar_contrasena` |
| Los 3 roles y qué puede hacer cada uno             | `dominio/modelo/usuario.py` → `Rol`, `PERMISOS_POR_ROL` |
| Una cuenta desactivada no puede nada               | `dominio/modelo/usuario.py` → `Usuario.puede` |
| Correo repetido                                    | `aplicacion/casos_uso/cuentas/registrar_usuario.py` → `RegistrarUsuario._crear` |
| El registro público solo crea usuarios comunes     | `aplicacion/casos_uso/cuentas/registrar_usuario.py` → `RegistrarUsuario.registrarse` |
| Exigir un permiso antes de actuar                  | `aplicacion/casos_uso/cuentas/permisos.py` → `exigir` |
| No quedarse sin administradores                    | `aplicacion/casos_uso/administracion/gestionar_usuarios.py` → `AdministrarUsuarios.actualizar` |
| El puesto del vendedor existe en el catálogo       | `aplicacion/casos_uso/administracion/gestionar_usuarios.py` → `AdministrarUsuarios.actualizar` |
| Un reporte revisado no se revisa dos veces         | `dominio/modelo/reporte.py` → `Reporte._revisar` |
| Producto, mercado y unidad del reporte existen     | `aplicacion/casos_uso/usuario/reportar_precio.py` → `RegistrarReporteCiudadano.ejecutar` |
| Aprobar convierte el reporte en observación        | `aplicacion/casos_uso/administracion/validar_reportes.py` → `ValidarReportes.aprobar` |
| Largo de campos que llegan por HTTP                | `infraestructura/adaptadores/entrada/api/esquemas.py` |
| Todos los mensajes de error                        | `dominio/excepciones.py` |

## Rutas de la API

| Ruta                                  | Quién            | Archivo |
|---------------------------------------|------------------|---------|
| `POST /auth/registro`, `/auth/ingresar`, `GET /auth/yo` | cualquiera / con sesión | `api/rutas/cuentas.py` |
| `POST /reportes`                      | usuario (con sesión) | `api/rutas/usuario/reportes.py` |
| `GET/POST /admin/usuarios`, `PATCH /admin/usuarios/{id}` (rol, activo, puesto), `PUT /admin/usuarios/{id}/contrasena` | administrador | `api/rutas/administracion/usuarios.py` |
| `GET /admin/reportes`, `POST /admin/reportes/{id}/aprobar` y `/rechazar` | administrador | `api/rutas/administracion/reportes.py` |
| Precios, comparar, canasta, catálogo  | público          | `api/rutas/publico/precios.py`, `canasta.py`, `catalogo.py` |

Todas cuelgan de `/api/v1`. Con el servidor arriba, `/docs` las muestra y deja probarlas.

## Quién decide qué adaptador se usa

`infraestructura/adaptadores/entrada/api/dependencias.py` es la **raíz de
composición**: el único archivo que decide "con `BASE_DATOS_URL`, PostgreSQL;
sin ella, memoria". Ningún caso de uso sabe cuál le tocó.

## Recolector, programador y comandos de consola

| Qué                                   | Dónde |
|---------------------------------------|-------|
| Recolectar una vez (SIIP diario e IPC) | `infraestructura/adaptadores/entrada/cli/recolectar.py` |
| Una vez por día con reintentos (Docker) | `infraestructura/adaptadores/entrada/cli/programador.py` |
| Los clientes del SIIP                  | `infraestructura/adaptadores/salida/fuentes/` |
| Crear o promover un administrador      | `infraestructura/adaptadores/entrada/cli/crear_admin.py` |
| Sembrar catálogos                      | `infraestructura/adaptadores/entrada/cli/sembrar.py` |

## Frontend (`frontend/src/`), la misma idea

| Si buscas...                    | Está en |
|---------------------------------|---------|
| Tipos y reglas (Usuario, Rol)   | `dominio/modelo.ts` |
| Puertos (interfaces)            | `aplicacion/puertos.ts` |
| Ingresar / salir / registrarse  | `aplicacion/casosUso/gestionarSesion.ts` |
| Acciones del administrador      | `aplicacion/casosUso/administrar.ts` |
| Las llamadas a la API           | `infraestructura/http/CuentasApi.ts` (y `clienteHttp.ts`, el único con `fetch`) |
| Dónde se guarda el token        | `infraestructura/almacen/almacenSesion.ts` |
| Qué adaptador se usa            | `infraestructura/contenedor.ts` |
| Pantallas                       | `ui/paginas/cuentas/PaginaIngreso.tsx`, `administracion/PaginaAdmin.tsx`, `publico/PaginaPrecios.tsx` |
