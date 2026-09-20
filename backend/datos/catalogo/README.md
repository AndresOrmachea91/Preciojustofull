# Catálogo versionado

Los puntos de venta y los productos no se cargan a mano en la base ni se
descubren en tiempo de ejecución: viven aquí, en CSV, dentro del
repositorio. Un cambio en el catálogo es un commit con autor, fecha y
diff, igual que un cambio de código.

## Por qué CSV en git y no una migración ni una tabla semilla

- El catálogo es **dato curado por una persona**, no dato observado. Su
  historia importa: por qué se agregó un mercado, por qué se corrigió una
  coordenada. Git ya sabe contar esa historia; una tabla no.
- Un revisor puede abrir el archivo sin levantar la base.
- La siembra es idempotente, así que el CSV es la única fuente de verdad:
  si difiere de la base, gana el CSV.

## puntos_venta.csv

| Columna | Significado |
|---|---|
| `codigo` | Identificador estable. Nunca se reescribe: si un mercado cambia de nombre, el código se queda. |
| `nombre` | Nombre para mostrar, ya corregido. |
| `tipo` | `mercado`, `supermercado`, `minimarket`, `tienda` o `mayorista`. Decide si el precio se publica como rango o como valor único, y a qué nivel de precio pertenece el local. |
| `macrodistrito` | Uno de los 7 macrodistritos urbanos de La Paz. |
| `latitud`, `longitud` | WGS84, 6 decimales (~0,1 m). Para nodos es el nodo; para polígonos, el centroide. |
| `codigo_padre` | Vacío si es un punto independiente. Si tiene valor, este local está **dentro** de ese punto de venta. |
| `osm_id` | Procedencia: `n`/`w`/`r` + id de OpenStreetMap. Permite volver al original y re-verificar. |
| `revision` | `ok`, o una nota de qué falta confirmar en campo. |
| `notas` | Procedencia y decisiones ya tomadas. No se mezcla con `revision`: una es lo pendiente, la otra es el porqué de lo resuelto. |

### La jerarquía

Un mercado grande no es un precio: es decenas de puestos. `codigo_padre`
permite registrar un local concreto y que el sistema siga sabiendo a qué
mercado pertenece, sin duplicar el mercado ni perder el detalle.

Hoy solo hay un hijo cargado (`rodriguez_cubierto`), porque OpenStreetMap
casi no mapea puestos individuales. Los demás van a entrar por
verificación en campo y por los reportes de comerciantes. La columna
existe desde el principio para que agregarlos no sea una migración.

## De dónde salieron los datos

### Consulta a Overpass (OpenStreetMap)

Ámbito: **municipio de Nuestra Señora de La Paz**, área `3604499870` de
Overpass, y no una caja de coordenadas. La diferencia no es cosmética: la
caja que cubre La Paz mete también El Alto, y devolvía 112 mercados en vez
de 84. El límite municipal es el criterio correcto y además es auditable.

    [out:json][timeout:180];
    area(3604499870)->.lp;
    (
      node["amenity"="marketplace"](area.lp);
      way["amenity"="marketplace"](area.lp);
      relation["amenity"="marketplace"](area.lp);
    );
    out center tags;

Y para las cadenas:

    [out:json][timeout:180];
    area(3604499870)->.lp;
    (
      node["shop"~"^(supermarket|wholesale)$"](area.lp);
      way["shop"~"^(supermarket|wholesale)$"](area.lp);
    );
    out center tags;

### El macrodistrito no se puso a ojo

Se descargaron las 7 fronteras administrativas de nivel 9 del municipio
(`relation["boundary"="administrative"]["admin_level"="9"]`) y cada punto
se clasificó por inclusión en el polígono. Nadie escribió "Sopocachi"
porque le pareció.

### Curación aplicada

De 84 mercados crudos quedaron 65, más 1 local hijo. Se descartaron:

- **Sin nombre** (9): polígonos que no se pueden identificar ni verificar.
- **No venden canasta familiar** (4): Mercado de las Brujas (artesanía y
  ritual), Mercado de Flores, Mercado de comida tradicional de Obrajes
  (comida preparada), EcoTambo (tienda, no mercado).
- **Mal etiquetados** (1): un Ketal con `amenity=marketplace`. Pasó a la
  lista de supermercados, que es lo que es.
- **Nombres inservibles** (2): "mercado de fruta", "Fruit and vegatebles".
- **Duplicados** (2): el mismo mercado mapeado como nodo y como polígono
  (Alto Mariscal Santa Cruz, La Merced). Se conservó el polígono, que
  tiene mejor geometría.

De 164 tiendas crudas quedaron 22. El filtro fue **cadena reconocible**
(Ketal, Hipermaxi, Fidalga, Makro, EMAPA, ZuMarket). El resto de los
`shop=supermarket` de OpenStreetMap en La Paz son tiendas de barrio mal
etiquetadas, y entre ellas hay una zapatería, una librería y dos casas en
venta. Sirven para el mapa de la ciudad, no para comparar precios.

También se fusionaron 2 pares de sucursales duplicadas en OSM (dos
Hipermaxi a 40 m y dos Ketal en el mismo punto).

## Qué falta confirmar

13 filas tienen la columna `revision` distinta de `ok`. Son casos que los
datos no resuelven y que necesitan a alguien que conozca la ciudad:
homónimos (dos "Mercado Bolívar"), un nombre que OSM escribe "Virgen de
las Nueves", barrios de sucursales de cadena, y si el "Mercado de Frutas"
es independiente o parte del complejo Rodríguez.

## Licencia de los datos

Los datos de ubicación provienen de OpenStreetMap y están bajo
[ODbL](https://opendatacommons.org/licenses/odbl/). La atribución
corresponde a los colaboradores de OpenStreetMap.

## productos.csv

45 productos de la canasta familiar de La Paz, con su correspondencia en
las dos fuentes del SIIP.

| Columna | Significado |
|---|---|
| `codigo` | Identificador estable, en minúsculas y sin tilde. |
| `nombre` | Nombre para mostrar. |
| `categoria` | `abarrote`, `lacteo`, `carne`, `pescado`, `tuberculo`, `hortaliza` o `fruta`. Las mismas del dominio. |
| `unidad_base` | En qué unidad se publica el precio: `kg`, `litro`, `unidad` o `atado`. Un atado no convierte a kilo y no se pretende. |
| `es_perecedero` | `si` o `no`. Decide cuán rápido le pega un bloqueo: días para una hortaliza, semanas para un abarrote. |
| `siip_diario` | Código del producto en el **catálogo mayorista** del SIIP (`busquedaJSONC.php`). |
| `siip_ipc` | Código del mismo producto en el **catálogo de consumidor final** del SIIP (`itemsXDivision`, versión 2018). |
| `revision` | `ok`, o qué falta confirmar: `confirmar_ipc`, `revisar_corte`, `verificar_unidad`, `colision_ipc`. |
| `notas` | Procedencia y decisiones ya tomadas. |

### Por qué `siip_diario` y `siip_ipc` son dos columnas

No son dos nombres del mismo dato. El diario cotiza el precio **mayorista**
(arroz por quintal, carne en gancho) y el IPC el precio que paga el
**consumidor final** (el mismo arroz por libra). Son dos niveles de precio
distintos del mismo producto, y el dominio se niega a promediarlos. Por eso
cada producto guarda las dos correspondencias por separado y puede tener
una sola: `manteca_vegetal` no existe en el IPC, `banana` se dejó sin IPC a
propósito.

### Qué se excluyó del catálogo diario (74 productos en la fuente, 45 acá)

- **9 razones sociales**: los grupos "Ingenios" (BELGICA, UNAGRO, GUABIRA,
  SAN AURELIO, BERMEJO) y "Empresas" (SOFIA, IMBA, ALG, PIO RICO) no son
  productos, son quién vende azúcar y pollo.
- **5 insumos industriales**: maíz amarillo duro, sorgo, soya, trigo en
  grano y trigo pelado. Son materia prima para molinos y granjas, no
  canasta familiar.
- **Pollo vivo al productor**: es un tercer nivel de precio, anterior al
  mayorista, y no tiene con qué compararse.
- **Las variantes importadas** (arroz, azúcar, harina, aceite, manteca de
  cerdo, papa holandesa, ají, cebolla roja): duplican al nacional sin
  aportar en esta versión. Entran cuando haya con qué distinguirlas en el
  IPC.

### Qué se usa del IPC

Solo la **división 1, Alimentos y Bebidas No Alcohólicas** (179 ítems de
513). Las otras 11 divisiones son prendas de vestir, vivienda, transporte,
salud, educación: nada que se compre en un mercado.

La serie del IPC llega **por ciudad**: "La Paz" es un valor mensual, no una
medición en el Rodríguez. Además la unidad cambia por ciudad (arroz en
libra en La Paz, en cuartilla en Potosí) y varios ítems no tienen serie
para La Paz aunque existan en el catálogo (aceite de soya, quinua real,
carne de cerdo entero, pacú, surubí, papa holandesa, yuca, ají, ajo, piña,
sandía al 18 de septiembre de 2026). Para esos, la única fuente efectiva
en La Paz es el diario.

### Desfase entre las dos fuentes

Al 18 de septiembre de 2026 el diario mayorista publica datos hasta
**julio de 2026** y el IPC hasta **agosto de 2026**. El desfase es del SIIP,
no del recolector: cada fuente publica cuando el ministerio la actualiza.
