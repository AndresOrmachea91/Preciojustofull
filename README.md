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

    adaptadores  ->  aplicacion  ->  dominio

- `dominio/` no importa nada de fuera. Ni FastAPI, ni SQLAlchemy, ni requests.
- `aplicacion/` importa solo `dominio` y sus propios puertos (interfaces).
- `adaptadores/` importa lo que quiera: es el borde del sistema.

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
      adaptadores/
        entrada/
          api/          FastAPI: rutas, esquemas, inyección de dependencias
          cli/          el recolector como comando
        salida/
          memoria/      repositorios en memoria (para pruebas y para arrancar)
          fuentes/      un adaptador por cada fuente de precios
    tests/

## Cómo correrlo

    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    uvicorn src.adaptadores.entrada.api.main:app --reload

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

    python -m src.adaptadores.entrada.cli.recolectar --fuente diario --productos 5,12,30
    python -m src.adaptadores.entrada.cli.recolectar --disponibilidad

Sin `BASE_DATOS_URL` avisa y termina con error en lugar de correr en vacío:
es preferible fallar ruidosamente antes que perder días de serie en silencio.

Guardar es **idempotente** —hay una restricción de unicidad por fuente,
producto, mercado y fecha—, así que se puede correr tres veces al día sin
duplicar nada.

## Postman

La colección está en `docs/postman/PrecioJusto.postman_collection.json`.
Importala y apuntá la variable `base_url` a tu servidor.

