# Debate de funcionalidades (17 de octubre de 2026)

Treinta puntos de vista (casera, carnicero, vendedora de feria, compradoras de
El Alto, pensión, universitario, adulto mayor, madre de familia, Defensa del
Consumidor, abogado de publicidad, gremio, alcaldía, recomendación, economía
del comportamiento, ciencia de datos, seguridad, privacidad, UX, inclusión,
nutrición, logística, periodismo, sostenibilidad, comunidad, marketplaces,
gerencia de producto, ingeniero evaluador, tutor, jurado y abogado del diablo)
propusieron 90 ideas, fusionadas en 26, y votaron cada uno 6 (6 a 1 puntos).

Idea semilla del dueño del proyecto: que los caseros suban promociones y el
sistema las recomiende.

## Resultado

| Puesto | Idea | Puntos | Votos | 1º lugar |
|---|---|---|---|---|
| 1 | **Oferta del casero con candado** | 165 | 30/30 | 19 |
| 2 | **¿Lo viste así?**: confirmar o desmentir en un toque | 121 | 30/30 | 2 |
| 3 | Ofertas dentro de mi lista ("tu tomate está en oferta en el puesto 14") | 52 | 17 | 1 |
| 4 | Reproducir el precio: "¿de dónde sale este número?" | 44 | 13 | 2 |
| 5 | Recomendación explicable de puestos (nadie paga por aparecer) | 43 | 16 | 1 |
| 6 | Índice de cumplimiento del casero (declarado vs observado) | 29 | 12 | 0 |
| 7 | Panel del casero: su precio frente al mercado y demanda anónima | 28 | 7 | 0 |

Descartadas: encargo al casero (28 de 30 la descartan), costo por plato y
nutrición (11), detector de colusión (10), remate de tarde y alerta de alza.

## La regla que hace que una oferta no sea publicidad engañosa

Dicha por los 30, con sus palabras: **el ahorro se calcula contra el precio
del sistema (observado o estimado, diciendo cuál), nunca contra un "antes" que
escribe el casero**. Además: la oferta vence sola (24 a 72 h), máximo 3
activas por puesto, se muestra siempre como "declarada por el vendedor", no
entra al motor de fusión, y si no es de verdad más barata no se muestra como
oferta. Dos desmentidos de personas distintas la pausan y la mandan a revisión.

## Cómo encaja

- La oferta es una tabla aparte (`oferta`) que el motor no lee: una rebaja la
  elige el casero (sesgo de selección) y no debe hundir la referencia.
- La confirmación de un comprador sí es una observación (fuente ciudadano, con
  su informante): una voz por informante, límite de intentos y cola de revisión
  ya existen.
- Registrada en el cronograma como C133 (28 h), planificada.
