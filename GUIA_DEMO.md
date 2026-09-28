# Guía de la demo

Todo lo de acá está probado el 2026-09-21 contra la base real de Neon.
Los comandos son para Windows, desde la raíz del repositorio.

## 0. Antes de salir de casa (una vez)

```
cd backend
python -m pip install -r requirements.txt
cd ..\frontend
npm install
cd ..
copy backend\.env.example backend\.env
copy frontend\.env.example frontend\.env.local
```

Después editar `backend\.env` y pegar la cadena de Neon (rama `production`) en
`BASE_DATOS_URL`. Es la única edición a mano. `.env` y `.env.local` están en
`.gitignore`: no se suben.

Si `pip` falla en `psycopg2-binary`: `requirements.txt` ya pide `>=2.9.10`
(la 2.9.9 no tiene wheel para Python 3.13); repetir el comando.

## 1. Comprobar que la base responde (30 segundos, antes de presentar)

Doble clic en **`comprobar.cmd`** (o en VS Code: `Ctrl+Shift+P` → *Tasks: Run
Task* → **Demo: comprobar la base de datos**). Tiene que decir:

```
  [OK] La base responde.
       observaciones de precio: 31732
       puntos de venta:         88
       productos:               45
  Todo listo para la demo.
```

Si dice que la base no responde, la cadena de `BASE_DATOS_URL` está vieja
(la contraseña de Neon se rota): copiarla de Neon → *Connect*. Si no hay
internet, ir directo al plan B de la sección 5.

## 2. Arrancar: un comando, un enlace

Igual que `php artisan serve`. Desde una terminal en la raíz del proyecto:

```
serve.cmd
```

Imprime el enlace y se queda corriendo hasta `Ctrl+C`:

```
  PrecioJusto - servidor de desarrollo

    Aplicacion:  http://localhost:8000
    API (docs):  http://localhost:8000/docs
    Datos:       http

    Ctrl+C para detener
```

Un solo proceso: **FastAPI sirve también la interfaz** (la construye la
primera vez, ~20 s; después arranca en 2 s porque detecta que el build está
al día). No hay Vite aparte, no hay CORS, no hay dos ventanas.

| Variante | Para qué |
|---|---|
| `serve.cmd` | Normal: interfaz + API contra la base real |
| `serve.cmd memoria` | Plan B: datos fijos, sin base y sin internet |
| `serve.cmd 9000` | Otro puerto, si el 8000 está ocupado |
| `demo.cmd` | Lo mismo que `serve.cmd`, y además abre el navegador |

En VS Code: `Ctrl+Shift+B` (tarea *Servidor: arrancar*), o **F5** para
arrancar con depurador.

## 3. Qué abrir y qué se debería ver

| URL | Qué se ve |
|---|---|
| http://localhost:8000 | El mapa de La Paz con **88 puntos**, "Arroz de primera" seleccionado, y arriba el aviso: *88 puntos con precio ◌ estimado …, 0 con precio ● observado*. Abajo, 87 tarjetas de consumidor final y Makro aparte como mayorista. |
| clic en un punto | Panel a la derecha: nombre, tipo, macrodistrito, **PRECIO AL CONSUMIDOR** o **PRECIO MAYORISTA**, la insignia ◌ Estimado, el rango en Bs/kg, la explicación *"Estimado a partir del precio de referencia de la ciudad (N observaciones). Todavía nadie verificó este precio en …"* y el nivel de confianza. |
| http://localhost:8000/docs | Swagger de la API con `/mercados`, `/productos`, `/precios/{producto}/comparar`, `/precios/{producto}/mercado/{mercado}`, `/canasta/calcular`, `/reportes`. |
| F12 → Network (filtrar `api/v1`) | Al cargar: `GET /productos`, `GET /mercados`, `GET /precios/arroz_primera/comparar`. **Una** de cada, aunque dos partes de la pantalla las usen (el cliente HTTP comparte peticiones en vuelo). Al cambiar de producto: una sola `/comparar` nueva. |

Tiempos medidos contra Neon desde La Paz, con el servidor único:
`/mercados` ~1 s, `/precios/…/comparar` ~3–4 s; la carga inicial hasta ver
los 88 puntos, **9–12 s en frío** (la primera consulta a Neon despierta la
base). **Abrir la página unos minutos antes de presentar**: la segunda carga
va mucho más rápida.

Productos con cobertura completa (88 puntos): arroz, tomate, huevo, cebolla,
zanahoria, pollo, azúcar, harina… Los que dicen "87 sin precio" (aceite,
papa holandesa, quinua, pacú, ajo…) son productos para los que el IPC no
publica serie para La Paz: solo queda Makro, estimado desde el mayorista.
Eso es correcto y es parte del mensaje: no se inventa.

## 4. El recorrido de una petición del mapa por las capas

Al elegir "Tomate Rio Fuego":

```
frontend
  ui/App.tsx                      el componente NO llama a fetch: usa el hook
  ui/hooks/useMapa.ts             → contenedor.verMapa.ejecutar("tomate")
  aplicacion/casosUso/verMapa.ts  caso de uso: pide mercados() y compararMercados()
                                  a los PUERTOS (aplicacion/puertos.ts)
  infraestructura/contenedor.ts   raíz de composición: VITE_ORIGEN_DATOS decide el adaptador
  infraestructura/http/PreciosApi.ts   adaptador HTTP: GET /mercados, GET /precios/tomate/comparar
  infraestructura/http/clienteHttp.ts  el ÚNICO archivo del frontend con fetch()
        │
        ▼  HTTP (CORS permitido para localhost:5173 en backend/.env)
backend
  infraestructura/adaptadores/entrada/api/rutas/precios.py     FastAPI recibe /comparar
  infraestructura/adaptadores/entrada/api/dependencias.py     enchufa repositorios (Neon)
  aplicacion/casos_uso/comparar_mercados.py                   UNA consulta de observaciones
                                                              por producto; por cada mercado:
  dominio/servicio/motor_fusion.py                            estimar_desde_ciudad(...)
                                                              → PrecioConsolidado ESTIMADO
  infraestructura/adaptadores/salida/persistencia/            SQLAlchemy sobre Neon (Postgres)
        │
        ▼  JSON con procedencia obligatoria
frontend
  PreciosApi traduce snake_case → dominio; VerMapa junta 88 mercados + precios
  ui/componentes/MapaPuntosVenta.tsx   Leaflet solo dibuja lo que le dan
  ui/componentes/PanelPunto.tsx        procedencia, explicación, confianza
```

`frontend/tests/arquitectura.test.ts` y `backend/tests/test_arquitectura.py`
leen los archivos y fallan si alguien salta una capa.

## 5. Depurar en vivo: dónde parar y qué mirar

Un **punto de interrupción** es una marca en una línea: cuando el programa
llega ahí, se detiene y deja ver el valor de cada variable en ese instante.

Cómo se pone en VS Code: abrir el archivo, hacer **clic en el margen
izquierdo**, a la izquierda del número de línea → aparece un punto rojo
(también con `F9` parado en la línea). Después **F5** → *Demo con depurador*.
Cuando el programa pare: `F10` avanza una línea, `F11` entra en la función,
`F5` sigue hasta la próxima parada, `Shift+F5` corta.

### El recorrido, parada por parada

El navegador pide los datos en **un solo lugar de todo el frontend**:
`frontend/src/infraestructura/http/clienteHttp.ts`, **línea 49**
(`const respuesta = await fetch(url, init)`). Es el único `fetch` del
proyecto y hay una prueba que falla si aparece otro en cualquier otra parte.

| # | Archivo y línea | Qué se ve al parar ahí |
|---|---|---|
| 1 | `frontend/src/ui/App.tsx:57` | El clic en el producto. `p.codigo` es lo único que el componente sabe: no conoce HTTP ni la base. |
| 2 | `frontend/src/ui/hooks/useMapa.ts:21` | El puente React → caso de uso: `contenedor.verMapa.ejecutar(codigoProducto)`. |
| 3 | `frontend/src/aplicacion/casosUso/verMapa.ts:31-32` | El caso de uso pide **dos cosas a los puertos**: `catalogo.mercados()` y `precios.compararMercados()`. No sabe si detrás hay HTTP o datos en memoria. |
| 4 | `frontend/src/infraestructura/http/PreciosApi.ts:110` | El adaptador arma la ruta: `/precios/<producto>/comparar`. Acá empieza a existir HTTP. |
| 5 | `frontend/src/infraestructura/http/clienteHttp.ts:49` | **La petición sale del navegador.** `url` es la URL completa. |

Cruza la red y entra al backend (acá sí paran los puntos de `F5`):

| # | Archivo y línea | Qué se ve al parar ahí |
|---|---|---|
| 6 | `backend/.../api/rutas/precios.py:14` | La petición llegó. FastAPI ya tradujo la URL a parámetros: `codigo_producto`. |
| 7 | `backend/src/aplicacion/casos_uso/comparar_mercados.py:71` | `todas = self._observaciones.buscar(...)`: **una sola** consulta a Neon con todas las observaciones del producto. Al pasar la línea con `F10`, `len(todas)` dice cuántas trajo. |
| 8 | `backend/src/aplicacion/casos_uso/comparar_mercados.py:81` | **La parada más útil.** Se recorre punto por punto: `mercado` es el que evalúa, `locales` son las mediciones *en ese lugar* (hoy **lista vacía**) y `referencia` el dato del SIIP para la ciudad. |
| 9 | `backend/src/aplicacion/casos_uso/comparar_mercados.py:41` | Dentro de `precio_del_local`: como `locales` estaba vacío, cae en `motor.estimar_desde_ciudad(...)`. Con `F11` en la línea 81 se entra acá. |
| 10 | `backend/src/dominio/servicio/motor_fusion.py:143` | **El motor.** `f = mercado.factor_mercado`: cuánto se aparta ese local del precio de la ciudad. La línea 142 ya consolidó la referencia; las de abajo multiplican el rango por `f`. |
| 11 | `backend/src/dominio/servicio/motor_fusion.py:155` | `procedencia=Procedencia.ESTIMADO`, escrito a mano y sin alternativa: **por eso ningún precio puede salir sin decir de dónde viene**. Un par de líneas más abajo se arma el texto "no es una medición en …". |
| 12 | `backend/.../persistencia/repositorios.py:182` | Si se quiere ver el SQL: acá se arma la consulta que sale a Postgres. |

Con eso se explica la tesis entera sin diapositivas: **en la parada 8 se ve
que `locales` está vacío** (nadie midió en ese mercado) y **en la 10-11 se ve
que el precio se calcula desde la ciudad y se marca como estimado**.

### Detalles que evitan un papelón

- Si el punto rojo queda **hueco** y nunca para: se eligió la configuración
  *API con recarga automática*. Con `--reload`, uvicorn corre en un proceso
  hijo y los puntos no se disparan. Usar *Demo con depurador*.
- `F5` **detiene el servidor mientras está parado**: la página se queda
  "cargando". Es normal; `F5` de nuevo (o el botón ▶) lo suelta.
- Las paradas 1 a 5 son **JavaScript**, no Python: no se detienen con `F5`.
  Para esas, en el navegador `F12` → pestaña *Sources*, o `arrancar.cmd`
  (modo desarrollo) donde el código va sin minificar.
- Con 88 puntos, la parada 8 se dispara 88 veces. Para verla una sola vez:
  clic derecho en el punto rojo → *Edit Breakpoint* → condición
  `mercado.codigo == "rodriguez"`.

## 6. Plan B: sin backend, sin base, sin wifi

Si la base no responde, o no hay internet, o Neon está caído:

```
demo.cmd memoria
```

Mismo comando, mismo puerto, misma pantalla: la interfaz se construye con
datos fijos y no le pide nada a la API. Probado: 0 peticiones, 7 puntos en el
mapa, 6 tarjetas, panel con procedencia (4 observados, 2 estimados, 1 sin
precio), mayorista aparte.

Para volver al modo normal: `demo.cmd` (sin argumento) reconstruye.
El fondo del mapa (OpenStreetMap) sí necesita internet: sin wifi queda gris,
pero los puntos, los precios y las procedencias se ven igual.

Es el mismo código y los mismos componentes: cambiar una variable de entorno
es el único cambio, y eso es justamente la demostración de la arquitectura.

## 7. Las tres fallas más probables

| Síntoma | Solución en una línea |
|---|---|
| `address already in use` / la UI sale en otro puerto (5174) | `netstat -ano \| findstr :8000` (o `:5173`) → `taskkill /F /PID <pid>` y volver a arrancar. |
| En consola del navegador: `blocked by CORS policy` | El backend arrancó sin `backend\.env` o con otro origen: revisar `CORS_ORIGENES=http://localhost:5173,http://127.0.0.1:5173` y usar exactamente `http://localhost:5173`. |
| La API tarda mucho o `could not connect` / `password authentication failed` | La cadena de `BASE_DATOS_URL` es vieja (la contraseña se rotó el 21/09): pegar la actual desde Neon → Connect; si Neon no responde, plan B. |

Otras dos que aparecieron ensayando: `No module named uvicorn` → las
dependencias están en otro Python; correr `python -m pip install -r
backend\requirements.txt` con el mismo `python` que usa `arrancar.cmd` (lo
imprime al arrancar). Y `main.tsx: Unexpected token '<'` → Vite se arrancó
desde una ruta rara; usar `arrancar_ui.cmd`, que entra a `frontend` con la
ruta real.
