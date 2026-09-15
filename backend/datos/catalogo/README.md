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
| `tipo` | `mercado`, `supermercado`, `minimarket` o `tienda`. Decide si el precio se publica como rango o como valor único. |
| `macrodistrito` | Uno de los 7 macrodistritos urbanos de La Paz. |
| `latitud`, `longitud` | WGS84, 6 decimales (~0,1 m). Para nodos es el nodo; para polígonos, el centroide. |
| `codigo_padre` | Vacío si es un punto independiente. Si tiene valor, este local está **dentro** de ese punto de venta. |
| `osm_id` | Procedencia: `n`/`w`/`r` + id de OpenStreetMap. Permite volver al original y re-verificar. |
| `revision` | `ok`, o una nota de qué falta confirmar en campo. |

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
