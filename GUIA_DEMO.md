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

## 2. Arrancar: UN SOLO servidor

Igual que `mvn spring-boot:run`: un comando, un puerto, una ventana. La
interfaz se construye y **la sirve el mismo proceso de FastAPI**, así que no
hay que levantar Vite aparte ni hay CORS de por medio.

```
demo.cmd
```

Doble clic, o en VS Code `Ctrl+Shift+B` (tarea *Demo: arrancar TODO en un
solo servidor*). Tarda ~20 s la primera vez porque construye la interfaz.
Abre el navegador solo. Cuando la terminal diga `Application startup
complete`, todo está en:

| | |
|---|---|
| La aplicación | **http://localhost:8000** |
| La API (Swagger) | http://localhost:8000/docs |
| Estado | http://localhost:8000/api/v1/salud → `interfaz_servida: true` |

Para detenerlo: `Ctrl+C` en esa terminal, o cerrar la ventana.

**Plan B en el mismo comando**: `demo.cmd memoria` construye la interfaz con
datos fijos; funciona sin Neon, sin `.env` y sin internet.

### Con depurador (F5)

`F5` → *Demo con depurador (interfaz + API en :8000)*. Hace lo mismo pero
con el depurador de Python enganchado, y abre el navegador al arrancar.

Para poner un **punto de interrupción**:

1. Abrir `backend/src/aplicacion/casos_uso/comparar_mercados.py`.
2. Buscar, dentro de `CompararMercadosCasoUso.ejecutar`, la línea
   `precio = precio_del_local(self._motor, mercado, locales, referencia)`.
3. Hacer clic en el **margen izquierdo**, justo a la izquierda del número de
   línea: aparece un punto rojo. (También con `F9` sobre la línea.)
4. `F5` y, en el navegador, elegir un producto.
5. VS Code se detiene ahí. En el panel izquierdo, *Variables* muestra
   `mercado` (el punto de venta que está evaluando), `locales` (mediciones
   en ese lugar: hoy vacío) y `referencia` (el dato del SIIP para la ciudad).
   `F10` avanza una línea, `F11` entra en la función, `F5` continúa hasta el
   siguiente punto de venta.

Es la forma más clara de mostrar por qué un precio sale **estimado**: se ve
que `locales` está vacío y que el precio se calcula desde `referencia`.

Otros lugares que valen la pena para un punto de interrupción:

| Archivo | Qué se ve |
|---|---|
| `dominio/servicio/motor_fusion.py` → `estimar_desde_ciudad` | El cálculo: referencia de ciudad × `factor_mercado`, y la confianza acotada. |
| `infraestructura/.../api/rutas/precios.py` → `comparar` | La petición HTTP entrando, antes de tocar el dominio. |
| `infraestructura/.../persistencia/repositorios.py` → `buscar` | La consulta que se manda a Neon. |

Si el punto rojo aparece **hueco** y nunca se detiene: se está usando la
configuración *API con recarga automática*; con `--reload` uvicorn corre en
un proceso hijo y los puntos no se disparan. Usar la primera configuración.

### Para programar (no para presentar)

`arrancar.cmd`, o la tarea *Desarrollo: API y Vite por separado*, levanta los
dos servidores (8000 y 5173) con recarga en caliente: cada cambio en el
frontend se ve al instante, sin reconstruir. Ahí sí hay dos ventanas, y la
interfaz se mira en **http://localhost:5173**.

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

## 5. Plan B: sin backend, sin base, sin wifi

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

## 6. Las tres fallas más probables

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
