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

Con `VITE_ORIGEN_DATOS=memoria` (el valor por defecto) corre sin backend.
Con `VITE_ORIGEN_DATOS=http` y `VITE_API_URL=http://localhost:8000/api/v1`
usa la API real: es el único cambio, y `tests/arquitectura.test.ts` verifica
que siga siendo el único (ningún archivo fuera de `infraestructura/http`
llama a `fetch`). Desde la raíz del repositorio, `arrancar.cmd` levanta las
dos cosas juntas.

## El mapa y la honestidad visible

`ui/componentes/MapaPuntosVenta.tsx` dibuja con Leaflet los puntos de venta
que le entrega el caso de uso `VerMapa`; Leaflet es una librería de dibujo,
no de dominio, y es el único archivo que la importa. Cada punto se colorea
por tipo (mercado, supermercado, minimarket, mayorista) y se dibuja
punteado cuando su precio es estimado.

Todo precio lleva su **procedencia**: `observado` (alguien lo midió en ese
lugar) o `estimado` (calculado desde el precio de referencia de la ciudad).
Hoy todos son estimados, y la interfaz lo dice en un aviso, con la cantidad
de observaciones que respaldan cada uno. Un precio mayorista se muestra en
su propia sección: es otro nivel de la cadena y no compite con los de
consumidor final.

Por defecto usa el adaptador en memoria, así que arranca sin backend.
Para apuntar a la API real, poné en `.env`:

    VITE_ORIGEN_DATOS=http
    VITE_API_URL=http://localhost:8000/api/v1

## Pruebas

    npm test

`tests/compararMercados.test.ts` ejecuta un caso de uso completo con el
adaptador en memoria: sin red, sin backend, sin navegador.

