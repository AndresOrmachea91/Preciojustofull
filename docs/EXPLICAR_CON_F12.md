# Explicar el sistema con F12 y con /docs

Esta guía sirve para mostrar en la presentación cómo funciona PrecioJusto por
dentro, sin abrir el código: mirando las consultas que la pantalla le hace al
servidor. Todo con el sistema corriendo en Docker (`http://localhost:8088`).

La idea que hay que transmitir es una sola: **la pantalla no guarda los
precios. Cada vez se los pide al servidor por la API, y el servidor responde en
JSON.** La pantalla nunca toca la base de datos: siempre pasa por la API
(arquitectura hexagonal).

---

## 1. Las cuentas para entrar

Las contraseñas **no se escriben en ningún documento**: están en
`docker\.env` (ábralo con el Bloc de notas). Lo que va después del `=` es la
contraseña.

| Para entrar como… | Usuario | Contraseña: línea de `docker\.env` |
|---|---|---|
| Administrador | `admin@preciojusto.bo` | `ADMIN_INICIAL_CONTRASENA=` |
| Compradora | `compradora@demo.preciojusto.bo` | `DEMO_CONTRASENA=` |
| Casera (51 cuentas) | `casero01@demo.preciojusto.bo` … `casero51@demo.preciojusto.bo` | `DEMO_CONTRASENA=` |
| Distribuidora (3) | `distribuidora01@demo.preciojusto.bo` … `03` | `DEMO_CONTRASENA=` |

Una casera registrada por el administrador en su puesto entra con su
**número de celular** (por ejemplo `71234567`) y la clave temporal que se le
anotó.

---

## 2. F12: ver las consultas en vivo

1. Abra `http://localhost:8088` en Chrome y presione **F12**. Se abren las
   herramientas para desarrolladores.
2. Elija la pestaña **Red** (en inglés, **Network**). Si no se ve, está en el
   botón **»**.
3. Con F12 abierto, presione **F5** para recargar: se llena la lista con cada
   pedido que la página le hizo al servidor.
4. Arriba, marque el filtro **Fetch/XHR**: deja solo los pedidos a la API.
5. Haga clic en un pedido (por ejemplo `mercados`) y mire sus pestañas:

| Pestaña | Qué muestra | Qué decir |
|---|---|---|
| **Encabezados** (Headers) | La dirección pedida, el método (`GET`, `POST`…) y el código de estado. | "200 quiere decir que salió bien; 401, que falta iniciar sesión; 400, que el dato no pasó una regla." |
| **Vista previa** (Preview) | La respuesta en JSON, ordenada y desplegable. | "Esto es lo que devolvió el servidor: los mercados con su nombre, tipo, zona y coordenadas." |
| **Respuesta** (Response) | El mismo JSON, en texto. | |
| **Carga útil** (Payload) | Lo que mandó la pantalla (solo en los `POST` y `PUT`). | "Esto es lo que escribió la persona en el formulario." |

6. Haga algo en la pantalla y mire qué pedido aparece:

| Acción en la pantalla | Pedido que aparece |
|---|---|
| Abrir la página | `GET /api/v1/productos`, `GET /api/v1/mercados` |
| Elegir un producto (tomate) | `GET /api/v1/precios/tomate/comparar` |
| Tocar el Mercado Lanza en el mapa | `GET /api/v1/mercados/lanza/puestos?producto=tomate` y `GET /api/v1/ofertas?mercado=lanza` |
| Entrar a Precios referenciales | `GET /api/v1/precios/referencia` |
| Entrar a Mercados | `GET /api/v1/mercados/directorio` |
| Iniciar sesión | `POST /api/v1/auth/ingresar` (en la respuesta viene el token de la sesión) |
| Cotizar una lista | `GET /api/v1/listas/{id}/cotizar` y un `comparar` por producto (el plan de compra) |
| La casera publica un combo | `POST /api/v1/vendedor/ofertas/combo` |

> **Ojo:** en la respuesta de `POST /auth/ingresar` aparece el token de la
> sesión. No lo muestre en pantalla grande; si lo muestra, cierre sesión
> después.

### Escribir una consulta a mano en la Consola

En la pestaña **Consola** (Console) de F12 se puede pedir algo directamente:

```js
await (await fetch("/api/v1/mercados")).json()
```

Aparece la lista de mercados para desplegar. Otra, contar cuántos hay:

```js
(await (await fetch("/api/v1/mercados")).json()).length
```

---

## 3. Abrir una dirección de la API directamente

Cualquier dirección `GET` se puede pegar en la barra del navegador:

- `http://localhost:8088/api/v1/mercados`: todos los lugares.
- `http://localhost:8088/api/v1/mercados/lanza/puestos`: los puestos del Lanza con su inventario.
- `http://localhost:8088/api/v1/precios/tomate/comparar`: el tomate en todos los mercados.
- `http://localhost:8088/api/v1/precios/referencia`: los precios referenciales de La Paz.
- `http://localhost:8088/api/v1/ofertas`: las ofertas vigentes (con `combo` si es parte de uno).

Chrome muestra el JSON en texto. Para verlo ordenado, active **Impresión
con formato** (*Pretty print*) arriba de la página.

---

## 4. /docs: todas las consultas, con un botón para probarlas

`http://localhost:8088/docs` lista todas las direcciones de la API agrupadas
por tema (precios, mercados, cuentas, vendedor, administración…).

1. Abra una, por ejemplo **GET /api/v1/mercados**.
2. Toque **Try it out** y después **Execute**.
3. Abajo aparece la respuesta real, el código de estado y el comando `curl`
   equivalente.

Las que piden sesión (las del vendedor y las del administrador) responden
**401** si no hay token: eso también sirve para mostrar que la seguridad
funciona (RBAC con token firmado JWT).

---

## 5. De la dirección al código

Ejemplo con `GET /api/v1/mercados`:

| Capa | Archivo |
|---|---|
| La pantalla lo pide | `frontend/src/infraestructura/http/PreciosApi.ts` (función `mercados`), por `clienteHttp.ts`, el único lugar con `fetch` |
| El servidor lo recibe | `backend/src/infraestructura/adaptadores/entrada/api/rutas/publico/catalogo.py` (`listar_mercados`) |
| Se decide qué adaptador usar | `backend/src/infraestructura/adaptadores/entrada/api/dependencias.py` |
| Se lee de la base | el repositorio de mercados (PostgreSQL), tabla `mercado` |

Las demás direcciones siguen el mismo camino: ruta → caso de uso (en
`backend/src/aplicacion/casos_uso/`) → dominio (las reglas, en
`backend/src/dominio/`) → repositorio → base. El mapa completo de qué está
dónde está en [MAPA_DEL_CODIGO.md](MAPA_DEL_CODIGO.md).

---

## 6. Todas las direcciones de la API

**Públicas (sin sesión):**

| Método | Dirección | Para qué |
|---|---|---|
| GET | `/api/v1/productos` | El catálogo de productos |
| GET | `/api/v1/mercados` | Los lugares (mercados, distribuidores, mayoristas) |
| GET | `/api/v1/mercados/directorio` | Cada lugar con cuántos puestos y ofertas tiene |
| GET | `/api/v1/mercados/{codigo}/ficha` | Todo lo de un mercado: precios, puestos, ofertas |
| GET | `/api/v1/mercados/{codigo}/puestos` | Los puestos de un mercado con su inventario (las ramas del mapa) |
| GET | `/api/v1/ofertas` | Las ofertas vigentes |
| GET | `/api/v1/precios/referencia` | Los precios referenciales de La Paz |
| GET | `/api/v1/precios/{producto}/comparar` | Un producto en todos los lugares |
| GET | `/api/v1/precios/{producto}/historial` | Cómo cambió el precio en la ciudad |
| GET | `/api/v1/precios/{producto}/mercado/{mercado}` | Un producto en un lugar |
| GET | `/api/v1/precios/confiabilidad` | Cuánto se equivoca el estimado |
| GET | `/api/v1/verificaciones` | Qué conviene medir primero en el campo |
| POST | `/api/v1/canasta/calcular` | Cuánto sale una canasta en cada lugar |
| GET | `/api/v1/salud` | Si el sistema está vivo |

**Cuentas:** `POST /auth/registro`, `POST /auth/ingresar` (con correo o
celular), `GET /auth/yo`, `POST /auth/recuperar`, `POST /auth/restablecer`.

**Comprador (con sesión):** listas (`/listas`, `/listas/{id}/cotizar`),
reportes de precio (`/reportes`, `/reportes/mios`) y confirmar ofertas
(`/ofertas/{id}/confirmar`).

**Casera o distribuidora (con sesión de vendedor):** su puesto
(`/vendedor/puesto`, `/vendedor/puesto/foto`, `/vendedor/distribuidora`), su
inventario (`/vendedor/inventario`), sus precios (`/vendedor/precios`) y sus
ofertas (`/vendedor/ofertas`, `/vendedor/ofertas/combo`,
`/vendedor/ofertas/{id}/retirar`).

**Administrador:** usuarios (`/admin/usuarios`, `/admin/usuarios/caseras`),
reportes, mercados, productos, auditoría, planilla de campo, salud y ofertas
en revisión (todas bajo `/admin/…`).

## 7. Qué mostrar de la velocidad (C147)

En F12 → **Red**, la columna **Tiempo** y la columna **Tamaño** cuentan dos mejoras del servidor:

- **Memoria corta.** `ofertas`, `precios/referencia`, `mercados/directorio` y la ficha de cada mercado se
  calculan una vez y se guardan dos minutos. Por eso responden en milésimas de segundo en vez de dos
  segundos. Cuando una casera publica una oferta o cambia un precio, lo guardado se olvida al instante
  y ella ve su cambio sin esperar. El código está en
  `backend/src/infraestructura/adaptadores/entrada/api/cache_fichas.py`.
- **Respuestas comprimidas.** Al tocar una consulta, en **Encabezados de respuesta** aparece
  `content-encoding: gzip`. La lista de ofertas pesa unos 34 KB y viaja en menos de 4 KB, que es lo que
  se nota en un celular con datos móviles. Se enciende en una línea de `main.py` (`GZipMiddleware`).

Para verlo en vivo: recargue con F5 mirando la pestaña Red y compare el tiempo de `ofertas` con el de
`comparar`, que no se guarda porque cambia con cada producto.
