# PrecioJusto — Backend

API REST en FastAPI con **arquitectura hexagonal** (puertos y adaptadores).

## Por qué hexagonal

El dominio tiene cinco fuentes de precios externas, heterogéneas e inestables
(SIIP mayorista, SIIP IPC, medios, reportes ciudadanos, levantamiento de campo).
En hexagonal eso es **un puerto y cinco adaptadores**: perder o cambiar una
fuente no toca el núcleo. La resiliencia deja de ser un parche y pasa a ser
una propiedad de la estructura.

## La regla que hay que respetar

Las dependencias apuntan **siempre hacia adentro**:

    infraestructura  ->  aplicacion  ->  dominio

- `dominio/` no importa nada de fuera. Ni FastAPI, ni SQLAlchemy, ni requests.
- `aplicacion/` importa solo `dominio` y sus propios puertos (interfaces).
- `infraestructura/` importa lo que quiera: es el borde del sistema.

Si algún día `dominio/` necesita importar FastAPI, la arquitectura se rompió.
Hay una prueba que lo verifica automáticamente: `tests/test_arquitectura.py`.

## Estructura

    src/
      dominio/          entidades, objetos de valor y reglas. Cero dependencias.
        modelo/         Producto, Mercado, Observacion, PrecioConsolidado, Bloqueo
        valor.py        Dinero, Unidad, Periodo, NivelConfianza
        servicio/       MotorFusion, CalculadorMargen
      aplicacion/
        puertos/
          entrada.py    qué se le puede pedir al sistema (casos de uso)
          salida.py     qué necesita el sistema del mundo (repositorios, fuentes)
        casos_uso/      la implementación de los puertos de entrada
      infraestructura/
        adaptadores/
          entrada/
            api/        FastAPI: rutas, esquemas, inyección de dependencias
            cli/        el recolector y la siembra del catálogo como comandos
          salida/
            memoria/    repositorios en memoria (para pruebas y para arrancar)
            catalogo/   lector del CSV de puntos de venta
            fuentes/    un adaptador por cada fuente de precios
            persistencia/  SQLAlchemy sobre PostgreSQL
    tests/

## Cómo correrlo

    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    uvicorn src.infraestructura.adaptadores.entrada.api.main:app --reload

Documentación interactiva en http://localhost:8000/docs

## Base de datos

**PostgreSQL** es el motor. **Neon** (o Supabase) es solo quien lo aloja: no
son alternativas entre sí.

Hay dos adaptadores del mismo puerto y se elige con una variable de entorno:

- sin `BASE_DATOS_URL` → repositorios en memoria, arranca sin instalar nada
- con `BASE_DATOS_URL` → PostgreSQL

Nada más cambia. Ni el dominio, ni los casos de uso, ni las rutas.

    BASE_DATOS_URL=postgresql://usuario:clave@host/basededatos?sslmode=require

El esquema se crea solo la primera vez que arranca. Se acepta la cadena tal
como la entrega el proveedor, incluso con el prefijo `postgres://` que
SQLAlchemy ya no admite: se traduce internamente.

## Pruebas

    pytest -v

Tres pruebas cuentan la arquitectura mejor que cualquier explicación:

- `tests/test_contrato_repositorios.py` corre **el mismo conjunto de casos
  contra los dos adaptadores** — el de memoria y el de SQLAlchemy sobre
  SQLite. Si ambos pasan, son de verdad intercambiables. Agregar un tercer
  adaptador es agregarlo a una lista, sin escribir una prueba más.
- `tests/test_comparar_mercados.py` ejecuta un caso de uso completo sin base
  de datos y sin red.
- `tests/test_arquitectura.py` lee los archivos del dominio y falla si
  alguien importa un framework.

## El recolector

    python -m src.infraestructura.adaptadores.entrada.cli.recolectar                 # todo el catálogo, las dos fuentes
    python -m src.infraestructura.adaptadores.entrada.cli.recolectar --fuente ipc --productos arroz_primera,papa_holandesa
    python -m src.infraestructura.adaptadores.entrada.cli.recolectar --disponibilidad

Los productos salen de `datos/catalogo/productos.csv`, que dice qué código
usa cada fuente (`siip_diario`, `siip_ipc`) para cada uno. Las
observaciones se guardan con el código del catálogo (`arroz_primera`),
nunca con el de la fuente.

Sin `BASE_DATOS_URL` avisa y termina con error en lugar de correr en vacío:
es preferible fallar ruidosamente antes que perder días de serie en silencio.

Guardar es **idempotente**: cada observación se identifica por la clave
natural del hecho (fuente, nivel, producto, ámbito, lugar, período
observado, unidad y cantidad) y volver a verla no la duplica, solo anota
`ultima_captura_en`. Si la fuente publica otro valor para el mismo hecho,
se guarda como revisión (`revisa_a`) sin pisar la anterior.

El resumen de disponibilidad tiene dos partes: si el portal **responde**
(intentos HTTP) y si el dato **avanza** (corridas con al menos un hecho
nuevo). Una corrida que ve hechos ya conocidos y ninguno nuevo sale con
código 3 y cuenta como fallida: el servidor respondió, pero la serie no
se movió.

## Reparar los datos existentes

    python -m src.infraestructura.adaptadores.entrada.cli.reparar_datos            # simulación
    python -m src.infraestructura.adaptadores.entrada.cli.reparar_datos --aplicar

Una sola vez, idempotente. Siembra el catálogo, pone la ciudad en su campo
y el producto con el código del catálogo, reprocesa el parseo con el
parser actual, deduplica por clave natural conservando la primera captura
(y se detiene sin borrar nada si un hecho tiene más de un valor) y crea el
índice único. Correrlo primero en simulación es obligatorio.

## La siembra del catálogo

    python -m src.infraestructura.adaptadores.entrada.cli.sembrar --dry-run
    python -m src.infraestructura.adaptadores.entrada.cli.sembrar

Lleva `datos/catalogo/puntos_venta.csv` a la tabla `mercado`, con la
jerarquía (un sector apunta a su mercado por `codigo_padre`) y el
macrodistrito, y `datos/catalogo/productos.csv` a la tabla `producto`. Es
**idempotente**: inserta lo que falta y actualiza lo que cambió, por
código. Nunca borra, porque las observaciones ya apuntan a esos códigos, y
no pisa el `factor_mercado` aprendido en campo. `--dry-run` reporta cuántos
insertaría, actualizaría y dejaría igual sin tocar nada.

## Postman

La colección está en `docs/postman/PrecioJusto.postman_collection.json`.
Importala y apuntá la variable `base_url` a tu servidor.

