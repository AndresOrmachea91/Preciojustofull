# La base de datos de PrecioJusto, tabla por tabla

Este documento explica qué guarda cada tabla, para qué sirve cada columna y por qué está hecha así. Los números de filas son los de la base de Docker al 20 de octubre de 2026.

El esquema está escrito en `backend/src/infraestructura/adaptadores/salida/persistencia/tablas.py`. Lo que se le fue agregando a una base que ya existía (columnas nuevas, índices parciales) está en `sesion.py`, en el mismo lugar.

---

## Primero, los tipos de dato

Cuando abres la base con DBeaver o pgAdmin ves estos tipos. Esto es lo que significan:

| Tipo en PostgreSQL | En el código | Qué guarda | Ejemplo |
|---|---|---|---|
| `character varying(n)` (varchar) | `String(n)` | Texto de hasta *n* letras. | `"arroz_primera"`, `"La Paz"` |
| `integer` | `Integer` | Número entero, sin decimales (hasta unos 2 100 millones). | `id = 15`, `anio = 2026` |
| `double precision` | `Float` | Número con decimales. Ocupa 8 bytes y es exacto hasta unos 15 dígitos. | `precio_monto = 310.0`, `cantidad = 0.5` |
| `boolean` | `Boolean` | Sí o no. | `eliminado = false` |
| `date` | `Date` | Solo una fecha, sin hora. | `2026-10-18` |
| `timestamp with time zone` | `DateTime(timezone=True)` | Fecha y hora exactas con su zona horaria. Se guardan en UTC y se muestran en hora de Bolivia. | `2026-10-20 01:36:52+00` |

### ¿Por qué `double precision` y no `numeric`?

`double precision` es el número decimal "rápido" de la computadora. Tiene un detalle: guarda los decimales en binario, así que 0,1 queda como 0,1000000000000000055… Para plata de un banco eso no sirve y se usa `numeric`, que es exacto.

Aquí se usa `double precision` a propósito, por tres motivos:

1. **El sistema calcula, no lleva cuentas.** Los precios entran en un motor que saca medianas, rangos y factores de mercado. Todas esas operaciones son estadística con decimales. Nadie suma centavos para cuadrar una caja.
2. **El error es invisible.** Una diferencia en el decimal 15 no cambia ningún precio que se muestra con 2 decimales.
3. **Funciona igual en SQLite.** Las pruebas automáticas corren sobre SQLite, que no tiene un `numeric` exacto. Con `Float` el esquema es el mismo en las dos bases. Esa decisión está escrita al inicio de `tablas.py`.

**Sobre la columna `cantidad`:** es `double precision` porque una cantidad puede ser fraccionaria, como media arroba o 0,25 kg. Un entero no podría guardar `0.5`.

### Las 5 columnas que tienen TODAS las tablas (auditoría)

Todas las tablas heredan de `Auditable` (`auditable.py`). Es lo mismo que un `@MappedSuperclass` de Spring/JPA.

| Columna | Tipo | Qué guarda |
|---|---|---|
| `creado_en` | timestamp con zona | Cuándo se creó la fila. No se puede cambiar después. |
| `creado_por` | varchar(255) | Quién la creó: el correo del usuario, o `sistema`, `recolector-automatico`, `siembra`. Tampoco se puede cambiar. |
| `modificado_en` | timestamp con zona | Cuándo se cambió por última vez. Vacío si nunca se tocó. |
| `modificado_por` | varchar(255) | Quién la cambió por última vez. |
| `eliminado` | boolean | Borrado **lógico**: la fila nunca se borra de verdad, solo se marca. Los repositorios no devuelven las filas eliminadas. |

**Por qué columnas en cada fila y no una tabla de logs:** las columnas viajan con el dato, en la misma transacción. Una tabla de logs separada se puede alterar sin tocar el dato y crece sin control.

**Cómo sabe quién hizo el cambio:** la API pone el correo de la sesión en una variable de contexto (`actor_actual`). Es lo mismo que hace el `SecurityContextHolder` de Spring.

---

## Mapa general

```
                 rol ──< rol_permiso >── permiso
                  │
usuario ──────────┤ (rol)
  │  └──1:1── vendedor ──> mercado
  │                          │  └── codigo_padre ──> mercado (sector de un mercado)
  ├──< lista_compras ──< item_lista_compras
  ├──< reporte_precio (autor y revisor)
  ├──< puesto ──> mercado
  ├──< oferta ──> mercado, producto
  └──< confirmacion_oferta ──> oferta

fuente ──< observacion_precio ──> (producto, mercado por código)
              └── revisa_a ──> observacion_precio (revisión de un dato)

corrida_fuente, intento_fuente: bitácora del recolector automático
```

`──<` significa "uno a muchos". Por ejemplo, un usuario tiene muchas listas.

Hay **19 tablas** en tres grupos:

- **Catálogos:** rol, permiso, rol_permiso, fuente, producto, mercado.
- **El dato:** observacion_precio, corrida_fuente, intento_fuente.
- **Las personas:** usuario, vendedor, reporte_precio, lista_compras, item_lista_compras, puesto, oferta, confirmacion_oferta.

---

## 1. Catálogos

### `rol` (3 filas)
Los tres roles: `usuario`, `vendedor` y `administrador`.

| Columna | Tipo | Qué es |
|---|---|---|
| `codigo` (PK) | varchar(16) | `usuario`, `vendedor` o `administrador`. |
| `nombre` | varchar(64) | El nombre que se muestra. |
| `descripcion` | varchar(255) | Qué hace ese rol. |

### `permiso` (9 filas)
Cada cosa que se puede hacer en el sistema: `reportar_precio`, `gestionar_listas`, `publicar_precio_propio`, `gestionar_usuarios`, `gestionar_catalogo`, `validar_reportes`, `ver_auditoria`, `importar_campo` y `ver_salud`.

| Columna | Tipo | Qué es |
|---|---|---|
| `codigo` (PK) | varchar(32) | El permiso. |
| `descripcion` | varchar(255) | Qué deja hacer. |

### `rol_permiso` (14 filas)
Qué permisos tiene cada rol: una fila por par rol–permiso. Su clave primaria es **compuesta** (`codigo_rol` + `codigo_permiso`), así un rol no puede tener dos veces el mismo permiso.

> **Ojo:** estas tres tablas son un *espejo* del dominio. La regla real vive en el código (`PERMISOS_POR_ROL`) y `referencias.py` las vuelve a sincronizar en cada arranque. Si alguien edita la tabla a mano, no cambia lo que el sistema permite. Están en la base para poder consultarlas y para que `usuario.rol` tenga una clave foránea de verdad.

### `fuente` (7 filas)
De dónde puede venir un precio.

| Columna | Tipo | Qué es |
|---|---|---|
| `codigo` (PK) | varchar(32) | `siip_ipc`, `siip_diario`, `vendedor`, `ciudadano`, `campo`, `medios`, `prensa`. |
| `nombre`, `descripcion` | varchar | Para mostrar. |
| `confianza_base` | varchar(16) | Cuánto se le cree de entrada: `alto` (SIIP), `medio` (vendedor, medios, prensa), `bajo` (ciudadano), `verificado` (campo). |
| `deriva_de` | varchar(32), FK a `fuente` | Si esta fuente copia a otra. La prensa reproduce el boletín del SIIP, así que **no** cuenta como una segunda voz. |
| `automatica` | boolean | Si la trae el recolector solo (los dos SIIP). |
| `url` | varchar(255) | De dónde se descarga, si aplica. |

### `producto` (45 filas)

| Columna | Tipo | Qué es |
|---|---|---|
| `codigo` (PK) | varchar(64) | Identificador legible: `arroz_primera`, `papa_holandesa`. |
| `nombre` | varchar(255) | Como lo dice la gente. |
| `categoria` | varchar(32) | `hortaliza`, `tuberculo`, `fruta`, `carne`, `pescado`, `lacteo`, `abarrote`, `otro`. |
| `dias_conservacion` | integer | Cuántos días dura el producto. Con esto el sistema decide cuándo un precio "ya es viejo": un tomate de hace 2 semanas está viejo, un arroz no. |
| `zona_origen` | varchar(128) | De dónde viene (Yungas, altiplano…). Es informativo. |
| `unidad_base` | varchar(8) | `kg`, `l` o `u`. Todos los precios se llevan a esta unidad para poder compararlos. |
| `presentaciones` | varchar(128) | En qué se vende: `"kilo,libra,arroba,quintal"`. Si está vacío, valen todas las que corresponden a la unidad. Así la carne no aparece "por arroba". |

### `mercado` (89 filas)
Cada **punto de venta** del mapa: 66 mercados, 21 supermercados, 1 tienda y 1 mayorista.

| Columna | Tipo | Qué es |
|---|---|---|
| `codigo` (PK) | varchar(64) | `rodriguez`, `lanza`, `hipermaxi_sopocachi`. |
| `nombre` | varchar(255) | El nombre visible. |
| `tipo` | varchar(32) | `mercado`, `supermercado`, `tienda` o `mayorista`. No es decorativo: en un **mercado** hay muchos puestos y se regatea, así que se publica un **rango**. En una tienda el precio está puesto, así que se publica un solo número. El mayorista vende por bulto a comerciantes y no se compara con el precio de las familias. |
| `zona`, `macrodistrito` | varchar | Ubicación en palabras. |
| `latitud`, `longitud` | double precision | Coordenadas GPS para el mapa. Se usa `double` porque necesitan decimales: `-16.4955`. |
| `factor_mercado` | double precision | Cuánto más caro o más barato es este lugar que el promedio de la ciudad. `1.06` es 6 % más caro y `0.95` es 5 % más barato. Con esto se **estima** el precio donde nadie lo midió: precio de la ciudad × factor. Se calibra con el trabajo de campo. |
| `codigo_padre` | varchar(64), FK a `mercado` | Es una **autorreferencia**: el sector "Rodríguez – carnes" apunta al mercado "Rodríguez". Casi todos lo tienen vacío. |

---

## 2. El dato: los precios

### `observacion_precio` (33 148 filas) — la tabla más importante

**Cada fila es UN precio que alguien vio o publicó.** Es *inmutable*: se guarda tal como lo dijo la fuente y nunca se corrige. El precio que la gente ve en el mapa **no se guarda en ningún lado**. Se calcula en el momento a partir de estas filas, con el motor de fusión. Por eso se puede recalcular con otra configuración y demostrar que fusionar fuentes aporta algo.

Hoy tiene 28 455 filas del SIIP IPC (consumidor final), 4 692 del SIIP diario (mayorista) y 1 de un vendedor.

**Qué y dónde:**

| Columna | Tipo | Qué es |
|---|---|---|
| `id` (PK) | integer, autoincremental | Número correlativo. |
| `fuente` | varchar(32), FK a `fuente` | Quién lo publicó. |
| `nivel` | varchar(16) | `minorista` (lo que paga una familia) o `mayorista` (por bulto). Nunca se mezclan. |
| `codigo_producto` | varchar(64) | Qué producto. |
| `ambito` | varchar(16) | `punto_venta` si se midió en un lugar concreto, `ciudad` si la fuente publica un solo valor para toda la ciudad. El SIIP es `ciudad`, y por eso con él solo se **estima**: no dice cuánto cuesta en el Rodríguez. |
| `codigo_mercado` | varchar(64), puede ir vacío | El punto de venta, cuando el ámbito es `punto_venta`. |
| `ciudad` | varchar(64), puede ir vacío | `la_paz`, cuando el ámbito es `ciudad`. Una ciudad no es un mercado, por eso tiene su propia columna. |
| `puesto` | varchar(16) | Número del puesto dentro del mercado (`"14"`), si se sabe. Es texto porque hay puestos como `"14-B"`. |

**Cuándo** (en tres columnas, porque no todas las fuentes dan la fecha completa):

| Columna | Tipo | Qué es |
|---|---|---|
| `anio` | integer | Siempre está. |
| `mes` | integer, puede ir vacío | El SIIP IPC es mensual. |
| `dia` | integer, puede ir vacío | Solo cuando la fuente da el día. |
| `fecha_observacion` | date, puede ir vacío | La fecha del dato según el dato. **Nunca** se rellena con la fecha en que lo bajamos: vacío significa "no se sabe", y el sistema lo dice así. |

**El precio:**

| Columna | Tipo | Qué es |
|---|---|---|
| `precio_monto` | double precision | Lo que dijo la fuente, tal cual. Por ejemplo, `310`. |
| `unidad_texto` | varchar(64) | La unidad, tal como la escribió la fuente. Por ejemplo, `"qq."` (quintal). |
| `cantidad` | double precision | Cuántas de esas unidades cubre el precio. Casi siempre es `1`. Sirve para casos como "Bs 5 por 2 libras": `cantidad = 2`. Lleva decimales porque puede ser media arroba (`0.5`). |
| `precio_canonico` | double precision, puede ir vacío | El mismo precio llevado a la unidad base del producto. Ejemplo real: 310 Bs el quintal de arroz ÷ 46 kg = **6,739 Bs/kg**. Si la unidad no se puede convertir, queda **vacío**: significa "no convertible", no "no calculado". |
| `unidad_canonica` | varchar(8) | `kg`, `l` o `u`. |

Se guardan **las dos cosas**, el par original y el canónico. Si mañana se corrige una equivalencia (por ejemplo, cuántos kg tiene una arroba), se recalcula sin haber perdido lo que dijo la fuente.

**Calidad y procedencia:**

| Columna | Tipo | Qué es |
|---|---|---|
| `variedad` | varchar(64) | `desconocida` por defecto. Es explícito: no se sabe y se dice. |
| `tipo_precio` | varchar(16) | `cotizado`, `pagado` o `desconocido`. Un precio que te dicen no es lo mismo que uno que pagaste. |
| `evidencia` | varchar(512) | Rastro del origen: `reporte:15`, `vendedor:2` o la URL del boletín. |
| `informante` | varchar(64), con índice | Quién lo afirmó: `usuario:12` o `campo:ana:puesto:14`. Vacío si no es una persona conocida. El motor junta por esta columna: **una voz por persona**, así que diez reportes de la misma persona no fabrican confianza alta. |
| `reputacion_informante` | double precision | El peso de quien lo dijo, de 0 a 1. Las fuentes oficiales y el campo van con 1. Un reporte aprobado entra con el peso del rol de su autor: 0,5 usuario, 0,6 vendedor y 0,8 administrador (`validar_reportes.py`). El motor multiplica la confianza de la fuente por este número. |

**Cuándo lo supimos:**

| Columna | Tipo | Qué es |
|---|---|---|
| `capturada_en` | timestamp con zona | La **primera** vez que el sistema vio este dato. No se pisa. |
| `ultima_captura_en` | timestamp con zona | La última vez que se volvió a ver. Va en otra columna para que "lo volví a ver" no borre "cuándo lo supe". |
| `revisa_a` | integer, FK a esta misma tabla | Si la fuente volvió a publicar el mismo dato con **otro** valor, la fila nueva apunta a la anterior. No es un duplicado, es una corrección, y se conservan las dos. |

**La clave natural (índice `uq_hecho_observado_v2`):** impide guardar dos veces el mismo hecho. Un hecho es la combinación fuente + nivel + producto + ámbito + mercado + ciudad + año + mes + día + unidad + cantidad + informante + puesto + monto.

Usa `coalesce(mes, 0)` porque en PostgreSQL dos `NULL` nunca son iguales, y sin eso los datos mensuales se duplicaban. Desde C133 incluye informante y puesto: dos caseros que venden al mismo precio el mismo día son **dos** datos, no uno repetido.

**Otros índices:** `ix_obs_consulta` (producto, mercado, año, mes) y `ix_obs_nivel` hacen rápidas las consultas del mapa.

### `corrida_fuente` (982 filas)
Qué trajo cada pasada del recolector, por fuente y producto.

| Columna | Tipo | Qué es |
|---|---|---|
| `id` (PK) | integer | |
| `fuente` | varchar(64) | `siip_ipc`, `siip_diario`. |
| `codigo_producto` | varchar(64) | |
| `hechos_vistos` | integer | Cuántos precios encontró. |
| `hechos_nuevos` | integer | Cuántos **no** tenía ya. |
| `ocurrido_en` | timestamp con zona | Cuándo corrió. |

Una corrida con 200 vistos y 0 nuevos **falló** para la tesis, aunque el portal haya respondido: el dato no avanzó.

### `intento_fuente` (1 219 filas)
Cada llamada a cada portal y cómo terminó.

| Columna | Tipo | Qué es |
|---|---|---|
| `fuente`, `url` | varchar | A quién se llamó. |
| `exito` | integer | 1 si respondió bien, 0 si no. |
| `duracion_ms` | integer | Cuánto tardó, en milisegundos. |
| `detalle` | varchar(512) | El error, si hubo. |
| `ocurrido_en` | timestamp con zona | |

De esta tabla sale la métrica de **disponibilidad**: cuántas veces la fuente original estaba caída frente a cuántas veces el sistema siguió dando un precio. Es uno de los resultados de la tesis.

---

## 3. Las personas

### `usuario` (4 filas)

| Columna | Tipo | Qué es |
|---|---|---|
| `id` (PK) | integer | |
| `correo` | varchar(255) | Se guarda ya en minúsculas. Es único **solo entre las cuentas vigentes** (índice parcial `uq_usuario_correo_vigente ... WHERE NOT eliminado`): si una cuenta se elimina, esa persona puede volver a registrarse. |
| `nombre` | varchar(255) | |
| `rol` | varchar(16), FK a `rol` | |
| `hash_contrasena` | varchar(255) | **Nunca** se guarda la contraseña, solo su hash con scrypt (de la biblioteca estándar de Python), con su sal y sus parámetros: `scrypt$n$r$p$sal$hash`. Ni el administrador puede leerla. |
| `activo` | boolean | Una cuenta suspendida no puede ingresar, pero no está eliminada. |

### `vendedor` (2 filas)
Lo que un vendedor tiene **además** de su cuenta. Es **herencia por tabla unida** (el `JOINED` de JPA): la clave primaria `id_usuario` es al mismo tiempo la clave foránea al usuario. Un vendedor **es** un usuario con algo más.

| Columna | Tipo | Qué es |
|---|---|---|
| `id_usuario` (PK y FK) | integer | |
| `codigo_punto_venta` | varchar(64), FK a `mercado` | El mercado o tienda donde vende. |

### `reporte_precio` (0 filas)
Lo que reporta un ciudadano queda **en espera** hasta que un administrador lo revisa. Al aprobarlo se convierte en una `observacion_precio` con `evidencia = reporte:ID`. Nunca se borra: el rechazado queda con su motivo, porque ese historial es la base para medir, más adelante, la reputación de quien reporta.

| Columna | Tipo | Qué es |
|---|---|---|
| `codigo_producto`, `codigo_mercado` | varchar(64) | Qué y dónde. |
| `monto` | double precision | El precio reportado. |
| `unidad` | varchar(64) | `kilo`, `libra`… |
| `id_autor` | integer, FK a `usuario` | Quién lo reportó. |
| `estado` | varchar(16) | `pendiente`, `aprobado` o `rechazado`. |
| `id_revisor`, `revisado_en` | integer FK / timestamp | Quién lo revisó y cuándo. |
| `motivo_rechazo` | varchar(512) | Por qué se rechazó. |

### `lista_compras` (2) e `item_lista_compras` (4)
Las listas del usuario ("Lo de la semana") y sus renglones.

| Columna (`item_lista_compras`) | Tipo | Qué es |
|---|---|---|
| `id_lista` | integer, FK | A qué lista pertenece. |
| `codigo_producto` | varchar(64) | |
| `cantidad` | double precision | Cuánto: `2`, `0.5`, `1.5`. Lleva decimales para poder pedir media arroba. |
| `presentacion` | varchar(16) | En qué: `kilo`, `libra`, `arroba`, `quintal`, `unidad`… Así "2 arrobas de papa" es `cantidad=2, presentacion=arroba`, y el sistema lo multiplica por 11,5 kg. |

### `puesto` (0 filas todavía)
Un puesto **dentro** de un mercado. Se identifica como lo dice la gente: "el 14 del Rodríguez".

| Columna | Tipo | Qué es |
|---|---|---|
| `id` (PK) | integer | |
| `codigo_mercado` | varchar(64), FK | |
| `numero` | varchar(16) | `"14"`, `"14-B"`. Es único dentro de su mercado entre los vigentes (`uq_puesto_numero_vigente`). |
| `nombre` | varchar(80) | "Verduras Doña Rosa". |
| `rubros` | varchar(128) | `"hortaliza,fruta"`: qué vende. |
| `referencia` | varchar(160) | "Entrada por la Max Paredes, al fondo". |
| `id_vendedor` | integer, FK a `usuario` | El dueño. Un vendedor tiene un solo puesto (`uq_puesto_vendedor_vigente`). |

### `oferta` (0 filas todavía)
La rebaja que declara un casero. **No** es una observación: el motor de fusión no la lee, para que una rebaja que elige el vendedor no mueva el precio de referencia.

| Columna | Tipo | Qué es |
|---|---|---|
| `id_vendedor` | integer, FK | |
| `codigo_mercado`, `numero_puesto` | varchar | Dónde. |
| `codigo_producto` | varchar(64), FK | |
| `monto` | double precision | Lo que pide: `12.0`. |
| `presentacion` | varchar(16) | Por qué: `kilo`, `arroba`… |
| `precio_por_unidad_base` | double precision | El mismo precio en Bs/kg. Con esto se compara contra el sistema y se rechaza la oferta si no es más barata. |
| `desde`, `hasta` | timestamp con zona | Vigencia, de 24 a 72 horas. Vence sola. |
| `nota` | varchar(80) | "Solo hasta el mediodía". |
| `estado` | varchar(16) | `activa`, `en_revision` (dos personas dijeron que no estaba así) o `retirada`. |

### `confirmacion_oferta` (0 filas todavía)
El "¿Lo viste así?". Hay una fila por persona y oferta (índice único `id_oferta + id_usuario`). Si la persona cambia de opinión se actualiza la misma fila, y la auditoría guarda cuándo.

| Columna | Tipo | Qué es |
|---|---|---|
| `id_oferta` | integer, FK | |
| `id_usuario` | integer, FK | |
| `la_vio_asi` | boolean | `true` si confirmó, `false` si desmintió. |

---

## Cómo viaja un precio, de punta a punta

1. **El recolector** baja el boletín del SIIP. Anota la llamada en `intento_fuente` y guarda en `observacion_precio` "arroz 310 Bs por `qq.`", con `precio_canonico = 6.739` y `ambito = ciudad`. El resumen va a `corrida_fuente`.
2. **Un ciudadano** reporta "tomate a 8 Bs el kilo en el Rodríguez". Queda en `reporte_precio` como `pendiente`. Si el administrador lo aprueba, nace una `observacion_precio` con `ambito = punto_venta`, `fuente = ciudadano` e `informante = usuario:3`.
3. **Cuando alguien abre el mapa,** el motor de fusión toma todas las observaciones del producto, junta las voces por `informante`, descarta las viejas según `dias_conservacion` y calcula el precio y su rango. En un mercado donde nadie midió, multiplica el precio de la ciudad por `factor_mercado` y lo marca como **estimado**.
4. **Nada de ese cálculo se guarda.** Así siempre sale de los datos originales.

## Lo que se agregó después (migración mínima)

`create_all` crea las tablas nuevas, pero no cambia las que ya existen. Por eso `sesion.py` tiene una pequeña migración que corre en cada arranque y es idempotente:

- agrega las columnas que faltan (`_COLUMNAS_AGREGADAS`);
- agrega las 5 columnas de auditoría a las tablas viejas;
- crea los índices parciales ("único solo entre los no eliminados"), que es algo propio de PostgreSQL;
- rellena con honestidad lo histórico. Por ejemplo, el `ambito` sale de la fuente; la fecha se recupera solo si el dato trae el día y, si no, queda vacía.

Si el esquema sigue creciendo, el paso siguiente natural es Alembic, que lleva versiones numeradas de cada cambio.
