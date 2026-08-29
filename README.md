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

## Pruebas

    pytest -v

`tests/test_comparar_mercados.py` ejecuta un caso de uso completo **con
repositorios en memoria, sin base de datos y sin red**. Eso es la demostración
práctica de que el núcleo no depende de la infraestructura.

## Postman

La colección está en `docs/postman/PrecioJusto.postman_collection.json`.
Importala y apuntá la variable `base_url` a tu servidor.

