# Arquitectura del backend

## La regla

Las dependencias apuntan **hacia adentro**. Nunca al revés.

    infraestructura  ->  aplicacion  ->  dominio

| Capa | Puede importar | Nunca importa |
|---|---|---|
| `dominio` | solo la biblioteca estándar | frameworks, base de datos, HTTP |
| `aplicacion` | `dominio` y sus puertos | infraestructura, frameworks |
| `infraestructura` | todo | — |

`tests/test_arquitectura.py` verifica esto automáticamente en cada corrida.

## Los puertos

**De salida** — lo que el sistema necesita del mundo:

| Puerto | Adaptadores que lo implementan |
|---|---|
| `FuentePrecios` | SIIP diario, SIIP IPC, medios, reportes ciudadanos, campo |
| `RepositorioObservaciones` | memoria, PostgreSQL |
| `RepositorioProductos` | memoria, PostgreSQL |
| `RepositorioMercados` | memoria, PostgreSQL |
| `ServicioPrediccion` | modelo entrenado, modelo de prueba |

Que `FuentePrecios` sea **un solo puerto con cinco adaptadores** es el
argumento central de por qué esta arquitectura le queda bien al proyecto:
perder o cambiar una fuente no toca el núcleo.

**De entrada** — lo que se le puede pedir al sistema: `ConsultarPrecio`,
`CompararMercados`, `CalcularCanasta`, `RegistrarReporte`. Los invocan dos
adaptadores distintos: la API REST y el recolector de línea de comandos.

## Decisiones que conviene poder defender

**La observación es inmutable; el precio consolidado es derivado.** Se
guarda lo que dijo cada fuente, con su unidad original, y el consolidado se
recalcula. Sin eso no se podría reejecutar el motor de fusión con otra
configuración sobre los mismos datos históricos — que es exactamente lo que
permite demostrar que fusionar aporta algo frente a usar una sola fuente.

**El conflicto se registra, no se promedia y se olvida.** Un sistema que
solo promedia fuentes discordantes tira la información más valiosa que
tiene. El registro permite auditar la decisión y detectar manipulación.

**El tipo de punto de venta define qué se publica.** En un mercado grande
hay decenas de puestos y se regatea, así que se publica un rango. En una
tienda o minimarket hay un dueño y el precio está puesto, así que se puede
publicar el precio de ese local.

**La conversión de unidades vive en el dominio.** No es un detalle técnico:
si el quintal se convierte mal, todos los precios del sistema quedan mal.

## Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/v1/salud` | Estado del servicio |
| GET | `/api/v1/productos` | Catálogo de productos |
| GET | `/api/v1/mercados?zona=` | Puntos de venta, filtrables por zona |
| GET | `/api/v1/precios/{producto}/comparar?zona=` | Comparación entre puntos de venta |
| GET | `/api/v1/precios/{producto}/mercado/{mercado}` | Precio en un punto concreto |
| POST | `/api/v1/canasta/calcular` | Costo de la lista de compras por mercado |
| POST | `/api/v1/reportes` | Reporte ciudadano de precio |

## Lo que falta (trabajo futuro)

- Adaptador de PostgreSQL para los tres repositorios
- Adaptador de la fuente de medios (transcripción de audio)
- Adaptador del servicio de predicción con el modelo entrenado
- Autenticación para los reportes y el modelo de reputación
- Panel de administración

