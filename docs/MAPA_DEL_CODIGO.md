# Mapa del código: ¿dónde está cada cosa?

La estructura es Clean + Hexagonal. No hay una carpeta `/bd/usuario`: lo que
en otros proyectos sería esa carpeta está repartido por **responsabilidad**,
siempre en el mismo lugar para cada tema. Las rutas son relativas a `backend/src/`.

    dominio/           las reglas (qué es válido)              no sabe que existe una base
    aplicacion/        los casos de uso (qué se puede pedir)    pide cosas a través de puertos
    infraestructura/   el borde (HTTP, base de datos, SIIP)     implementa los puertos

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
| 1    | Llega `POST /api/v1/auth/ingresar`                | `infraestructura/adaptadores/entrada/api/rutas/auth.py` → `ingresar` |
| 2    | Se valida la forma del JSON (campos, largos)      | `infraestructura/adaptadores/entrada/api/esquemas.py` → `IngresoEntrada` |
| 3    | El caso de uso decide si las credenciales sirven  | `aplicacion/casos_uso/gestionar_usuarios.py` → `IniciarSesion.ejecutar` |
| 4    | Se normaliza el correo (reglas del negocio)       | `dominio/modelo/usuario.py` → `normalizar_correo` |
| 5    | Se busca el usuario **en la base**                | `infraestructura/adaptadores/salida/persistencia/cuentas.py` → `UsuariosPostgres.obtener_por_correo` |
| 6    | Se compara la contraseña con su hash              | `infraestructura/adaptadores/salida/seguridad/cifrador.py` → `CifradorScrypt.verificar` |
| 7    | Se firma el token de sesión                       | `infraestructura/adaptadores/salida/seguridad/tokens.py` → `EmisorJwt.emitir` |
| 8    | Un error del dominio se vuelve código HTTP        | `infraestructura/adaptadores/entrada/api/seguridad.py` → `estado_http` |

En cada petición protegida, `seguridad.py → usuario_actual` lee el token y
`gestionar_usuarios.py → ResolverSesion` vuelve a buscar al usuario en la base,
por eso desactivar una cuenta corta su sesión al instante.

## Las validaciones, una por una

| Validación                                         | Dónde |
|----------------------------------------------------|-------|
| Formato de correo                                  | `dominio/modelo/usuario.py` → `normalizar_correo` |
| Contraseña: 8 caracteres, letras y números         | `dominio/modelo/usuario.py` → `validar_contrasena` |
| Qué puede hacer cada rol (matriz de permisos)      | `dominio/modelo/usuario.py` → `PERMISOS_POR_ROL` |
| Una cuenta desactivada no puede nada               | `dominio/modelo/usuario.py` → `Usuario.puede` |
| Correo repetido                                    | `aplicacion/casos_uso/gestionar_usuarios.py` → `RegistrarUsuario._crear` |
| El registro público solo crea usuarios comunes     | `aplicacion/casos_uso/gestionar_usuarios.py` → `RegistrarUsuario.registrarse` |
| Exigir un permiso antes de actuar                  | `aplicacion/casos_uso/gestionar_usuarios.py` → `exigir` |
| No quedarse sin administradores                    | `aplicacion/casos_uso/gestionar_usuarios.py` → `AdministrarUsuarios.actualizar` |
| Un reporte revisado no se revisa dos veces         | `dominio/modelo/reporte.py` → `Reporte._revisar` |
| Producto, mercado y unidad del reporte existen     | `aplicacion/casos_uso/registrar_reporte.py` → `RegistrarReporteCiudadano.ejecutar` |
| Aprobar convierte el reporte en observación        | `aplicacion/casos_uso/registrar_reporte.py` → `ValidarReportes.aprobar` |
| Largo de campos que llegan por HTTP                | `infraestructura/adaptadores/entrada/api/esquemas.py` |
| Todos los mensajes de error                        | `dominio/excepciones.py` |

## Rutas de la API

| Ruta                                  | Quién            | Archivo |
|---------------------------------------|------------------|---------|
| `POST /auth/registro`, `/auth/ingresar`, `GET /auth/yo` | cualquiera / con sesión | `api/rutas/auth.py` |
| `GET/POST /usuarios`, `PATCH /usuarios/{id}`, `PUT /usuarios/{id}/contrasena` | administrador | `api/rutas/usuarios.py` |
| `POST /reportes`                      | con sesión       | `api/rutas/reportes.py` |
| `GET /reportes`, `POST /reportes/{id}/aprobar` y `/rechazar` | administrador | `api/rutas/reportes.py` |
| Precios, comparar, canasta, catálogo  | público          | `api/rutas/precios.py`, `canasta.py`, `catalogo.py` |

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
| Pantallas                       | `ui/paginas/PaginaIngreso.tsx`, `PaginaAdmin.tsx`, `PaginaPrecios.tsx` |
