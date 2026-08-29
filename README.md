# PrecioJusto — Frontend

Aplicación en React con TypeScript, en **arquitectura hexagonal**.

## La regla

Igual que en el backend, las dependencias apuntan hacia adentro:

    ui  ->  aplicacion  ->  dominio
             ^
    infraestructura ---┘   (implementa los puertos)

**Ningún componente de React llama a `fetch`.** Un componente invoca un caso
de uso; el caso de uso depende de un puerto; el adaptador HTTP implementa ese
puerto. Por eso la aplicación entera se puede ejecutar y probar **con el
backend apagado**, cambiando el adaptador por el de memoria.

Eso no es un truco de pruebas: es la demostración de que la arquitectura no
es decorativa.

## Estructura

    src/
      dominio/          tipos y reglas puras. No sabe que existe React ni HTTP.
        modelo.ts
        servicio/       ordenarPorConveniencia: regla de negocio del front
      aplicacion/
        puertos.ts      interfaces: PrecioRepositorio, CatalogoRepositorio
        casosUso/       compararMercados, calcularCanasta, consultarCatalogo
      infraestructura/
        http/           adaptador contra la API real
        memoria/        adaptador con datos fijos, para trabajar sin backend
        contenedor.ts   raíz de composición: acá se elige el adaptador
      ui/               componentes React, hooks, estilos

## Cómo correrlo

    npm install
    cp .env.example .env
    npm run dev

Por defecto usa el adaptador en memoria, así que arranca sin backend.
Para apuntar a la API real, poné en `.env`:

    VITE_ORIGEN_DATOS=http
    VITE_API_URL=http://localhost:8000/api/v1

## Pruebas

    npm test

`tests/compararMercados.test.ts` ejecuta un caso de uso completo con el
adaptador en memoria: sin red, sin backend, sin navegador.

