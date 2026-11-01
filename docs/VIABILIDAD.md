# ¿Es viable PrecioJusto? Revisión del 1 de noviembre de 2026

Esta revisión mira el proyecto como lo miraría alguien que tiene que decidir si vale la pena seguirlo después de la defensa. Va en orden: qué resuelve, qué lo hace posible hoy, dónde se puede caer y qué cambiaría para que la gente lo use de verdad.

## Qué resuelve y para quién

En La Paz el precio de la comida cambia de un mercado a otro y de una semana a otra, y nadie lo junta en un solo lugar. La familia que hace la compra del mes no sabe si el tomate está más barato en el Rodríguez o en Villa Fátima hasta que llega. El casero, por su lado, no tiene cómo avisar que tiene papa buena y a buen precio, salvo gritarlo en el pasillo.

PrecioJusto pone las dos cosas en un mapa. Muestra lo que cuesta cada producto en cada mercado, dice de dónde sale ese número (si alguien lo midió o si se calculó desde el boletín oficial) y, desde este cambio, deja que el casero muestre su puesto, su foto y lo que tiene hoy.

## Lo que ya lo hace posible

- **Hay datos desde el primer día.** El recolector baja solo el boletín del SIIP. Hoy hay más de 33 000 precios guardados. Aunque ningún casero se registre, el mapa nunca está vacío.
- **Es barato de mantener.** Corre en un servidor propio con Docker: un VPS de unos 6 a 12 dólares al mes alcanza. No depende de Supabase ni de Firebase, así que no hay sorpresas de cobro ni de cierre.
- **Es honesto con el dato.** Cada precio dice si es medido o estimado, qué tan viejo es y cuánto se equivoca el estimado. Eso es lo que lo separa de una página de precios cualquiera, y es lo que defiende la tesis.
- **El casero ya no depende del administrador.** Se registra solo, elige su mercado y su número de puesto, sube la foto desde el celular y maneja su inventario con un toque.

## Dónde se puede caer

**1. El arranque en frío.** Es el riesgo más grande. Sin caseros registrados, la ventana de cada mercado dice "todavía ningún casero cargó su puesto". La gente entra una vez, no ve puestos y no vuelve. *Qué hacer:* no lanzarlo en los 66 mercados a la vez. Empezar con dos o tres (Rodríguez, Lanza y Villa Fátima) y registrar en persona a 10 o 15 caseros en cada uno, sentados con ellos con el celular en la mano. Un mercado lleno convence más que sesenta vacíos.

**2. ¿Qué gana el casero?** Si cargar su inventario no le trae clientes, lo deja a la semana. *Qué hacer:* darle algo que pueda ver. Por ejemplo, cuántas personas miraron su puesto esta semana, cuántas lo tienen en su lista, y un enlace o un código QR para pegar en el puesto o mandar por WhatsApp a sus caseras de siempre. Eso convierte el sistema en su vitrina, no en una tarea más.

**3. Precios inventados.** Un vendedor puede declarar un precio que no cobra. *Lo que ya hay:* todo lo declarado sale marcado así, las ofertas tienen candados (vencen solas, máximo tres, tienen que ser más baratas que el precio del sistema), los compradores pueden desmentirlas y el administrador las revisa. *Lo que falta:* el índice de cumplimiento, que compara lo que el casero dice con lo que ven los compradores y lo muestra en su puesto.

**4. Cuentas falsas de vendedor.** Ahora cualquiera se puede registrar como vendedor. El motor junta "una voz por persona", pero diez cuentas son diez voces. *Mitigación:* hay límite de registros por conexión, y lo declarado pesa menos que lo medido. Si crece, se puede pedir un número de celular verificado o que otro casero del mismo mercado lo avale.

**5. Gremios y dirigentes de mercado.** En La Paz cada mercado tiene su asociación. Si la dirigencia lo ve como control de precios, puede pedir a los afiliados que no participen. *Qué hacer:* presentarlo como vitrina gratuita para el casero, nunca como fiscalización, y conversar con la directiva antes del piloto.

**6. Celulares sencillos y mala señal.** Muchos caseros tienen equipos de gama baja y poco saldo. *Lo que ya hay:* la app se instala desde el navegador (no pesa como una app de tienda), la foto se achica en el celular antes de subir y la página abre aunque la señal sea mala. Lo que no se guarda sin conexión son los precios, a propósito: un precio viejo mostrado como actual sería mentir.

**7. El estimado todavía es plano.** El ajuste de cada mercado está en 1 hasta que haya mediciones de campo, así que hoy todos los mercados muestran el mismo precio estimado. Se corrige con el levantamiento de campo (A3250 a A3290) y la calibración (A5030). Mientras tanto, los precios de los caseros son los que harán la diferencia entre un mercado y otro.

**8. ¿Quién lo sostiene?** Sin publicidad ni ranking pagado, que es una promesa del proyecto ("nadie paga por aparecer"). *Caminos posibles:* un convenio con la Alcaldía o con la Defensoría del Consumidor, que necesitan estos datos; publicarlos como datos abiertos para periodistas e investigadores, o fondos de proyectos de seguridad alimentaria.

## Qué lo haría atractivo de verdad

### Para quien compra
- **"¿Dónde hay?"**: ver qué puestos tienen hoy un producto, no solo a cuánto. Ya se puede, porque el inventario dice "hay, poco o se acabó".
- **Alertas**: "el tomate bajó 20 % en el Rodríguez esta semana". Una sola notificación útil por semana vale más que una app abierta todos los días.
- **Compartir por WhatsApp** la lista con el mercado más conveniente. En La Paz la compra se coordina por WhatsApp.

### Para el casero
- **Su vitrina con QR** para pegar en el puesto y mandar a sus clientes.
- **Cuántos lo vieron** esta semana y qué buscaron.
- **Su precio frente al mercado**: "su papa está 5 % más barata que el promedio del Rodríguez". Le sirve para decidir y para presumir.

### Para La Paz
- **Un tablero público de precios** para la Alcaldía, periodistas y vecinos, con la evolución semanal por mercado.
- **Alerta de subidas bruscas**: cuando un producto sube mucho en pocos días en varios mercados a la vez, que se vea. Sirve en bloqueos y crisis de abastecimiento, que en La Paz no son raras.
- **Datos abiertos** en CSV, con su procedencia.

## Qué haría en las dos semanas que quedan hasta la entrega

1. Llevarlo al servidor propio (A7180 a A7200), porque sin eso nadie de afuera lo puede usar.
2. Hacer un piloto chico en un mercado: registrar en persona a 10 caseros y medir cuántos actualizan su inventario después de una semana. Ese número vale oro en la defensa.
3. Hacer la vitrina con QR y el contador de visitas del puesto: es lo que más pide el casero y es poco trabajo.
4. Dejar las alertas y el tablero para después de la defensa.

## Veredicto

Es viable como herramienta pública y barata de mantener, y la parte de precios oficiales ya funciona sin depender de nadie. Lo que decide si la gente lo usa no es técnico: es conseguir que los primeros caseros carguen su puesto y que vean algo a cambio. Por eso el siguiente paso más importante no es otra función, sino un piloto chico, bien acompañado, en uno o dos mercados.
