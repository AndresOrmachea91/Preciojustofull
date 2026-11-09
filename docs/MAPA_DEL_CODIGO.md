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
| La auditoría vista desde el dominio (solo lectura) | `dominio/modelo/auditoria.py → Auditoria` |
| Eliminar una cuenta (lógico: `DELETE`, la fila queda) | `casos_uso/administracion/gestionar_usuarios.py → eliminar`; `persistencia/cuentas.py → UsuariosPostgres.eliminar` |
| Listar con o sin eliminados                      | `GET /admin/usuarios?incluir_eliminados=true` → `UsuariosPostgres.listar` |
| DTO con y sin auditoría ("sobrecarga")           | `api/esquemas.py → UsuarioSalida` (propio, `/auth/yo`) y `UsuarioAuditadoSalida` (admin) |
| El correo es único solo entre cuentas vigentes   | `persistencia/sesion.py → uq_usuario_correo_vigente` (índice parcial) |
| Demostración en Postman (guardar, modificar, eliminar, listar) | `docs/postman/PrecioJusto_Auditoria.postman_collection.json` |
| Pruebas                                          | `backend/tests/test_auditoria.py`, `test_contrato_cuentas.py`, `test_api_autenticacion.py` |

## Las 14 tablas y qué guarda cada una

Todas heredan las 5 columnas de `Auditable`. Base: contenedor `preciojusto-db-1`, base `preciojusto`.

| Tabla | Guarda | Se relaciona con |
|-------|--------|------------------|
| `usuario` | Toda cuenta: correo, nombre, hash de la contraseña, activo | `rol` (FK `usuario.rol → rol.codigo`) |
| `vendedor` | Lo que un vendedor tiene además de su cuenta: su puesto | `usuario` (misma clave: herencia por tabla unida), `mercado` |
| `rol` | administrador, vendedor, usuario | |
| `permiso` | Las 7 acciones protegidas | |
| `rol_permiso` | Qué permiso tiene cada rol (la matriz) | `rol`, `permiso` |
| `fuente` | De dónde sale un precio: SIIP IPC, SIIP diario, vendedor, ciudadano, campo... | `fuente` (`deriva_de`, si copia a otra) |
| `producto` | Los 45 productos, su unidad base y presentaciones | |
| `mercado` | Mercados, tiendas, supermercados, mayoristas, con coordenadas | `mercado` (`codigo_padre`: el sector pertenece al mercado) |
| `observacion_precio` | **Todos los precios**, de cualquier fuente; inmutables | `fuente` (FK), producto, mercado o ciudad |
| `reporte_precio` | Precios que reportan los usuarios, pendientes o revisados | `usuario` (autor y revisor) |
| `lista_compras`, `item_lista_compras` | Listas de compras de cada usuario | `usuario`, `producto` |
| `corrida_fuente` | Qué trajo cada corrida del recolector, por producto | |
| `intento_fuente` | Cada llamada al SIIP y si respondió (métrica de disponibilidad) | |

Roles, permisos y fuentes **se deciden en el dominio** (`dominio/modelo/usuario.py`,
`observacion.py`); las tablas los reflejan para consultarlos y para las claves
foráneas. Se sincronizan solas al arrancar (`persistencia/referencias.py`):
editarlas a mano no cambia lo que el sistema permite, y lo que el dominio quita
se marca `eliminado`, no se borra.

## La equivalencia con "/bd/..."

| Si buscas...                         | Está en                                                              |
|--------------------------------------|----------------------------------------------------------------------|
| `/bd/usuario` (consultas SQL)        | `infraestructura/adaptadores/salida/persistencia/cuentas.py` → `UsuariosPostgres` (también escribe `vendedor`) |
| `/bd/rol`, `/bd/permiso`, `/bd/fuente` | `infraestructura/adaptadores/salida/persistencia/referencias.py` → `sincronizar_referencias` |
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

## Catálogo y presentaciones (kilo, libra, arroba, quintal)

| Qué                                                  | Dónde |
|------------------------------------------------------|-------|
| Las presentaciones y sus factores (quintal = 46 kg)  | `dominio/modelo/presentacion.py` |
| Qué presentaciones admite cada producto              | `dominio/modelo/producto.py` → `Producto.presentaciones` |
| Ubicación dentro de La Paz o El Alto                 | `dominio/modelo/mercado.py` → `ubicacion_valida` |
| Crear, editar y eliminar mercados y tiendas          | `aplicacion/casos_uso/administracion/gestionar_catalogo.py` → `GestionarPuntosVenta` |
| No eliminar un mercado con sectores o vendedores     | `gestionar_catalogo.py` → `GestionarPuntosVenta.eliminar` |
| Crear, editar y eliminar productos                   | `gestionar_catalogo.py` → `GestionarProductos` |
| Rutas `/api/v1/admin/mercados` y `/admin/productos`  | `api/rutas/administracion/catalogo.py` |
| Pantallas                                            | `frontend/src/ui/paginas/administracion/CatalogoPuntosVenta.tsx`, `CatalogoProductos.tsx` |
| Marcar la ubicación con un clic                      | `frontend/src/ui/componentes/MapaSelectorUbicacion.tsx` |
| Ver el precio por quintal en la página pública       | `frontend/src/dominio/modelo.ts` → `precioEnPresentacion`; `ui/paginas/publico/PaginaPrecios.tsx` |

Ojo: `cli/sembrar.py` vuelve a cargar los CSV del catálogo. Si se corre después de
editar algo desde el panel, pisa esos cambios. Se usa solo para la carga inicial.

## Vendedor y usuario

| Qué                                                   | Dónde |
|-------------------------------------------------------|-------|
| El vendedor publica el precio de SU puesto            | `aplicacion/casos_uso/vendedor/publicar_precio.py` → `PublicarPrecioPropio` |
| Sin puesto asignado no publica                        | `publicar_precio.py` → `_puesto_del` (error `SinPuntoVenta`) |
| Lo último que publicó de cada producto                | `publicar_precio.py` → `MisPrecios` |
| La fuente VENDEDOR y su confianza (media)             | `dominio/modelo/observacion.py` → `Fuente.VENDEDOR` |
| Mis reportes (solo los propios)                       | `aplicacion/casos_uso/usuario/mis_reportes.py` |
| La lista de compras y sus reglas                      | `dominio/modelo/lista_compras.py` → `ListaCompras`, `ItemLista` |
| Crear, editar, borrar y cotizar listas                | `aplicacion/casos_uso/usuario/listas_compras.py` → `GestionarListas` |
| La lista de otro responde como inexistente            | `listas_compras.py` → `GestionarListas._propia` |
| Cotizar: lo medido o, si no, estimado desde la ciudad | `aplicacion/casos_uso/precios/calcular_canasta.py` (usa `precio_del_local` del comparador) |
| Cuántos productos de la cotización son estimados      | `CostoCanastaEnMercado.productos_estimados` (`aplicacion/puertos/entrada.py`) |
| `/bd/listas` (consultas SQL)                          | `infraestructura/adaptadores/salida/persistencia/listas.py` → `ListasPostgres` |
| Rutas                                                 | `api/rutas/vendedor/precios.py`, `api/rutas/usuario/listas.py`, `api/rutas/usuario/reportes.py` |

En el frontend:

| Qué                                   | Dónde |
|---------------------------------------|-------|
| Casos de uso por rol                  | `src/aplicacion/casosUso/{publico, cuentas, usuario, vendedor, administracion}/` |
| Mayorista aparte en la cotización     | `src/aplicacion/casosUso/usuario/listasCompras.ts` → `cotizar` |
| Ahorro solo entre canastas completas  | `src/aplicacion/casosUso/publico/calcularCanasta.ts` → `resumirCanasta` |
| Pantallas del usuario                 | `src/ui/paginas/usuario/` (`MisListas`, `ReportarPrecio`, `MisReportes`) |
| Pantalla del vendedor                 | `src/ui/paginas/vendedor/PaginaVendedor.tsx` |
| Barra lateral: secciones de cada rol, ingresar / crear cuenta / salir, con iconos | `src/ui/componentes/BarraLateral.tsx` |
| Los iconos (SVG propios, sin dependencias) | `src/ui/componentes/Iconos.tsx` |
| Elegir un producto buscando (lista filtrada por categoría, con teclado) | `src/ui/componentes/SelectorProducto.tsx` |
| Rutas `#/ingresar` y `#/registrarse` (la misma pantalla en dos modos) | `src/ui/hooks/useRuta.ts`, `src/ui/paginas/cuentas/PaginaIngreso.tsx` |
| Piezas compartidas                    | `src/ui/componentes/Pestanas.tsx`, `Mensajes.tsx`; `src/ui/hooks/useCatalogo.ts` |

## Agregado del 13 al 17 de octubre

| Qué | Dónde (backend: `backend/src/`, web: `frontend/src/`) |
|-----|-------|
| Vista de auditoría de las 14 tablas (`/bd/auditoria`) | `aplicacion/casos_uso/administracion/ver_auditoria.py`; `persistencia/auditoria.py → AuditoriaPostgres`; web: `ui/paginas/administracion/Auditoria.tsx` |
| Roles, permisos y fuentes descritos | `dominio/modelo/referencias.py`; ruta `GET /admin/referencias`; web: `ui/paginas/administracion/Referencias.tsx` |
| Eliminar cuentas desde la web y ver las eliminadas | `ui/paginas/administracion/PaginaAdmin.tsx → Usuarios` |
| Historial del precio (gráfico) | `aplicacion/casos_uso/precios/historial_precio.py`; ruta `GET /precios/{producto}/historial`; web: `ui/componentes/GraficoHistorial.tsx` |
| Cerca de mí | dominio web `masCercanos`, `distanciaKm`; `aplicacion/casosUso/publico/cercaDeMi.ts`; GPS: `infraestructura/ubicacion/ubicacionNavegador.ts` |
| Recuperar la contraseña por correo | `aplicacion/casos_uso/cuentas/recuperar_contrasena.py`; enlace: `seguridad/enlaces.py`; correo: `salida/correo/smtp.py`; rutas `POST /auth/recuperar` y `/auth/restablecer`; web: `ui/paginas/cuentas/PaginaRecuperar.tsx` |
| Buzón de prueba (los correos no salen a internet) | servicio `mailpit` en `docker-compose.yml` → http://localhost:8025 |
| Presentaciones según la categoría | `dominio/modelo/producto.py → presentaciones_habituales` |
| Cada producto cotizado en su unidad | `aplicacion/casos_uso/precios/comparar_mercados.py → en_unidad_del_producto` |
| Una voz por informante (C126) | `dominio/servicio/motor_fusion.py → _una_evidencia_por_clan`; columna `observacion_precio.informante` |
| Procedencia en palabras y precios viejos (C125) | `PrecioConsolidado.voces` y `factor_mercado`; web: `dominio/modelo.ts → explicacionProcedencia`, `esPrecioViejo`; leyenda en `PaginaPrecios.tsx` |
| Rango honesto y empates (C128) | `dominio/servicio/rango_honesto.py`; web: `empatan` en `dominio/modelo.ts` |
| "Ahorra X Bs yendo a Y" (C129) | web: `aplicacion/casosUso/publico/calcularCanasta.ts → resumirCanasta`; `ui/paginas/usuario/MisListas.tsx → ResumenAhorro` |
| Planilla de campo (C127) | `aplicacion/casos_uso/administracion/importar_campo.py`; ruta `POST /admin/campo/importar`; web: `ui/paginas/administracion/PlanillaCampo.tsx` |
| ¿Qué tan confiable es? — backtest (C130) | `aplicacion/casos_uso/precios/evaluar_estimador.py`; ruta `GET /precios/confiabilidad`; web: `ui/paginas/publico/PaginaConfiabilidad.tsx` |
| Límite de intentos (C131) | `adaptadores/entrada/api/limite_intentos.py`; usado en `rutas/cuentas.py` |
| Salud del sistema y respaldos verificados (C132) | `aplicacion/casos_uso/administracion/salud_sistema.py`; `persistencia/salud.py`; `salida/respaldos/estado_archivo.py`; `docker/respaldar.sh` (restauración de prueba → `respaldos/estado.json`); web: `ui/paginas/administracion/SaludSistema.tsx` |
| Puesto del casero (C133) | `dominio/modelo/puesto.py`; `aplicacion/casos_uso/vendedor/mi_puesto.py`; `persistencia/puestos_y_ofertas.py`; rutas `GET/PUT /vendedor/puesto`; web: pestaña «Datos del puesto» en `ui/paginas/vendedor/PaginaVendedor.tsx` |
| Oferta con candado (C133) | `dominio/modelo/oferta.py` (vence, máx. 3, ahorro contra el sistema); `aplicacion/casos_uso/vendedor/ofertas.py`; `precios/referencia_sistema.py` (precio sin la voz del casero); `precios/ofertas_vigentes.py`; rutas `GET /ofertas`, `POST /vendedor/ofertas`; web: `ui/paginas/publico/PaginaOfertas.tsx`, `ui/componentes/TarjetaOferta.tsx` |
| ¿Lo viste así? y revisión (C133) | `aplicacion/casos_uso/usuario/confirmar_oferta.py`; `administracion/revisar_ofertas.py`; rutas `POST /ofertas/{id}/confirmar`, `/admin/ofertas/*`; web: `ui/paginas/administracion/OfertasEnRevision.tsx` |
| Ofertas dentro de la lista (C133) | `ofertasParaLista` en `dominio/modelo.ts`; `OfertasDeLaLista` en `ui/paginas/usuario/MisListas.tsx` |
| Entrar a un mercado (C134) | `aplicacion/casos_uso/precios/ficha_mercado.py` (ficha y directorio); rutas `GET /mercados/directorio`, `GET /mercados/{codigo}/ficha` (caché en `api/cache_fichas.py`); web: `ui/paginas/publico/PaginaMercados.tsx`, `PaginaMercado.tsx`; anillo dorado y «Entrar al mercado» en `MapaPuntosVenta.tsx` y `PanelPunto.tsx` |
| Planilla de campo con puesto (A4200) | columna `puesto` en `importar_campo.py`; `Observacion.puesto` y clave natural v2 (`tablas.py`, `sesion.py`) |
| Qué medir primero (A4230) y cuánto varía cada producto (A5020) | `aplicacion/casos_uso/precios/priorizar_verificaciones.py`; ruta `GET /verificaciones`; web: `ui/componentes/PlanVerificacion.tsx` en `PaginaConfiabilidad.tsx`, «Próxima ronda sugerida» en `PlanillaCampo.tsx` (`planillaDeLaRonda` en `operarSistema.ts`) |
| Limpieza de la web (C135) | `agruparPorPrecio` en `dominio/modelo.ts` y `ListaDePrecios` en `PaginaPrecios.tsx`; resumen y «¿Lo vio aquí? Diga a cuánto» en `ui/componentes/PanelPunto.tsx`; `InterfazSinCacheViejo` en `api/main.py`; `public/favicon.svg` |
| Base de datos explicada (C136) | `docs/BASE_DE_DATOS.md`; índice `ix_observacion_precio_informante` en `sesion.py` |
| Solo mercados, distribuidores y mayoristas (decisión 26) | `TipoPuntoVenta.en_alcance` y `DISTRIBUIDOR` en `dominio/modelo/mercado.py`; baja lógica de cadenas en `sesion.py` (`_CADENAS_FUERA`); catálogo CSV sin supermercados |
| Negocio del casero: puesto elegido, distribuidora y foto (C137) | `aplicacion/casos_uso/vendedor/mi_puesto.py`; `dominio/modelo/foto.py`; `salida/fotos/almacen_local.py`; rutas `PUT /vendedor/puesto`, `/vendedor/distribuidora`, `/vendedor/puesto/foto`; web: `ui/paginas/vendedor/MiNegocio.tsx`, `ui/foto.ts` |
| Inventario del puesto (C137) | `dominio/modelo/inventario.py`; `aplicacion/casos_uso/vendedor/inventario.py`; tabla `inventario_puesto`; rutas `/vendedor/inventario`; web: `ui/paginas/vendedor/InventarioPuesto.tsx` |
| Ventana del mercado en el mapa (C137) | `aplicacion/casos_uso/precios/puestos_del_mercado.py`; ruta `GET /mercados/{codigo}/puestos`; web: `ui/componentes/VentanaMercado.tsx` y `ventana` en `MapaPuntosVenta.tsx` |
| Registro como vendedor (decisión 27) | `quiere_vender` en `registrar_usuario.py` y `PaginaIngreso.tsx` |
| App instalable en el celular (C138) | `frontend/public/manifest.json`, `sw.js`, íconos; registro en `main.tsx` |
| Viabilidad y mejoras | `docs/VIABILIDAD.md` |

## Rutas de la API

| Ruta                                  | Quién            | Archivo |
|---------------------------------------|------------------|---------|
| `POST /auth/registro`, `/auth/ingresar`, `GET /auth/yo` | cualquiera / con sesión | `api/rutas/cuentas.py` |
| `POST /reportes`                      | usuario (con sesión) | `api/rutas/usuario/reportes.py` |
| `GET /reportes/mios`                  | usuario (con sesión) | `api/rutas/usuario/reportes.py` |
| `GET/POST /listas`, `PUT/DELETE /listas/{id}`, `GET /listas/{id}/cotizar` | usuario (con sesión) | `api/rutas/usuario/listas.py` |
| `GET/POST /vendedor/precios`          | vendedor con puesto | `api/rutas/vendedor/precios.py` |
| `GET/POST /admin/usuarios`, `PATCH /admin/usuarios/{id}` (rol, activo, puesto), `PUT /admin/usuarios/{id}/contrasena` | administrador | `api/rutas/administracion/usuarios.py` |
| `GET /admin/reportes`, `POST /admin/reportes/{id}/aprobar` y `/rechazar` | administrador | `api/rutas/administracion/reportes.py` |
| `POST/PUT/DELETE /admin/mercados[/{codigo}]` y `/admin/productos[/{codigo}]` | administrador | `api/rutas/administracion/catalogo.py` |
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
| Datos de prueba (C142)                 | `infraestructura/adaptadores/entrada/cli/sembrar_demo.py` |

## Frontend (`frontend/src/`), la misma idea

| Si buscas...                    | Está en |
|---------------------------------|---------|
| Tipos y reglas (Usuario, Rol)   | `dominio/modelo.ts` |
| Puertos (interfaces)            | `aplicacion/puertos.ts` |
| Ingresar / salir / registrarse  | `aplicacion/casosUso/cuentas/gestionarSesion.ts` |
| Acciones del administrador      | `aplicacion/casosUso/administracion/administrarCuentas.ts`, `administrarCatalogo.ts` |
| Las llamadas a la API           | `infraestructura/http/CuentasApi.ts` (y `clienteHttp.ts`, el único con `fetch`) |
| Dónde se guarda el token        | `infraestructura/almacen/almacenSesion.ts` |
| Qué adaptador se usa            | `infraestructura/contenedor.ts` |
| Pantallas                       | `ui/paginas/{publico, cuentas, usuario, vendedor, administracion}/` |
| El mapa: pines, filtros (C141)  | `ui/componentes/MapaPuntosVenta.tsx` |
| Tema de vidrio y paleta (C141)  | `ui/tema.css` (sobre `ui/estilos.css`) |
| Puestos en ramas (C143)         | `MapaPuntosVenta.tsx` (ramas), `ui/hooks/useRamasDelMercado.ts`, `ui/componentes/VentanaPuesto.tsx` |
| Zonas sin GPS (C143)            | `ZONAS_DE_LA_PAZ` en `dominio/modelo.ts`, `ui/hooks/useCercania.ts` |
