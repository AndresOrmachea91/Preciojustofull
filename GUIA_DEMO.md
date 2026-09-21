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

## 1. Arrancar

Doble clic en **`arrancar.cmd`**, o desde una terminal:

```
arrancar.cmd
```

Verifica Python, dependencias, `backend\.env`, `node_modules`,
`frontend\.env.local` y los puertos, y si falta algo lo dice con el comando
para arreglarlo. Si todo está, abre dos ventanas (API y UI) y el navegador.
Cerrar una ventana apaga esa parte. Para levantar una sola:
`arrancar_api.cmd` o `arrancar_ui.cmd`.

Qué debería verse en cada ventana:

- **API**: `Uvicorn running on http://127.0.0.1:8000` y `Esquema verificado`.
- **UI**: `VITE ready` y `Local: http://localhost:5173/`.

## 2. Qué abrir y qué se debería ver

| URL | Qué se ve |
|---|---|
| http://localhost:5173 | El mapa de La Paz con **88 puntos**, "Arroz de primera" seleccionado, y arriba el aviso: *88 puntos con precio ◌ estimado …, 0 con precio ● observado*. Abajo, 87 tarjetas de consumidor final y Makro aparte como mayorista. |
| clic en un punto | Panel a la derecha: nombre, tipo, macrodistrito, **PRECIO AL CONSUMIDOR** o **PRECIO MAYORISTA**, la insignia ◌ Estimado, el rango en Bs/kg, la explicación *"Estimado a partir del precio de referencia de la ciudad (N observaciones). Todavía nadie verificó este precio en …"* y el nivel de confianza. |
| http://localhost:8000/docs | Swagger de la API con `/mercados`, `/productos`, `/precios/{producto}/comparar`, `/precios/{producto}/mercado/{mercado}`, `/canasta/calcular`, `/reportes`. |
| F12 → Network (filtrar `api/v1`) | Al cargar: `GET /productos`, `GET /mercados`, `GET /precios/arroz_primera/comparar`. **Una** de cada, aunque dos partes de la pantalla las usen (el cliente HTTP comparte peticiones en vuelo). Al cambiar de producto: una sola `/comparar` nueva. |

Tiempos medidos contra Neon desde La Paz: carga inicial hasta ver los 88
puntos **9–12 s** en frío (la primera consulta a Neon es lenta),
cambio de producto **~3 s**. **Abrir la página unos minutos antes de
presentar**: la segunda carga es más rápida y la conexión ya está caliente.

Productos con cobertura completa (88 puntos): arroz, tomate, huevo, cebolla,
zanahoria, pollo, azúcar, harina… Los que dicen "87 sin precio" (aceite,
papa holandesa, quinua, pacú, ajo…) son productos para los que el IPC no
publica serie para La Paz: solo queda Makro, estimado desde el mayorista.
Eso es correcto y es parte del mensaje: no se inventa.

## 3. El recorrido de una petición del mapa por las capas

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

## 4. Plan B: sin backend, sin base, sin wifi

Si la API o la base no responden, la interfaz corre sola con datos fijos:

```
notepad frontend\.env.local      → cambiar VITE_ORIGEN_DATOS=http por memoria
arrancar_ui.cmd
```

Probado: 0 peticiones a la API, 7 puntos en el mapa, 6 tarjetas, panel con
procedencia (4 observados, 2 estimados, 1 sin precio), mayorista aparte.
El fondo del mapa (OpenStreetMap) sí necesita internet: sin wifi queda gris,
pero los puntos, los precios y las procedencias se ven igual.

Es el mismo código y los mismos componentes: cambiar una variable de entorno
es el único cambio, y eso es justamente la demostración de la arquitectura.

## 5. Las tres fallas más probables

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
