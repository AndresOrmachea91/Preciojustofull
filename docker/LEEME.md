# PrecioJusto en contenedores

Cuatro contenedores, una sola orden: `docker compose up -d --build` desde la
raíz del proyecto (o en VS Code: `Ctrl+Shift+P` → *Tasks: Run Task* →
*Docker: levantar todo*).

    ┌──────────────┐   ┌────────────────────┐   ┌──────────────┐
    │ app  :8088   │   │ recolector         │   │ respaldos    │
    │ API + web    │   │ 1 vez al día 11:00 │   │ 1 vez al día │
    └──────┬───────┘   └─────────┬──────────┘   └──────┬───────┘
           └─────────────┬───────┴─────────────────────┘
                   ┌─────┴──────┐
                   │ db  :5433  │  PostgreSQL 18, volumen "datos_pg"
                   └────────────┘

| Servicio     | Qué hace | Dónde mirarlo |
|--------------|----------|---------------|
| `db`         | PostgreSQL 18 propio. Los datos viven en el volumen `datos_pg` y sobreviven a `down`, reinicios y reconstrucciones. | `localhost:5433` (pgAdmin/DBeaver), usuario y contraseña en `docker/.env` |
| `app`        | La API (FastAPI) y la interfaz web en un solo proceso. Al arrancar crea el administrador inicial si no hay ninguno. | http://localhost:8088 y http://localhost:8088/docs |
| `recolector` | Duerme hasta `RECOLECCION_HORA` (hora de Bolivia), corre el recolector, y si falla reintenta el mismo día. | `docker compose logs -f recolector` |
| `respaldos`  | `pg_dump` diario a la carpeta `respaldos/`, borra los de más de `RESPALDO_DIAS` días. | carpeta `respaldos/` del proyecto |

La app y el recolector usan **la misma imagen** (el `Dockerfile` de la raíz):
mismo código, distinto comando.

## Configuración

Todo sale de `docker/.env` (no se sube a git; la plantilla es
`docker/.env.example`). Ahí están la contraseña de la base, el secreto de las
sesiones, el administrador inicial y las cuentas de prueba.

## Órdenes útiles

    docker compose ps                         estado
    docker compose logs -f app                registros de la API
    docker compose exec recolector python -m src.infraestructura.adaptadores.entrada.cli.recolectar
                                              recolectar ahora, sin esperar la hora
    docker compose down                       detener (los datos quedan)
    docker compose down -v                    detener y BORRAR la base (cuidado)
    herramientas\copiar_desde_neon.cmd        traer una copia fresca de Neon

## Datos de prueba

Mientras no hay caseros reales, este comando carga unos 50 puestos en
mercados de La Paz (los grandes, como el Lanza y el Rodríguez, con más de diez
cada uno) y tres distribuidoras, con foto ilustrada, inventario y ofertas, más
una compradora con su lista. Las ofertas vencen a las 72 horas: volver a correr
el comando el día de una demostración repone las vencidas. Los precios parten del
precio del sistema en cada mercado y se mueven un poco. La contraseña de esas
cuentas es `DEMO_CONTRASENA` de `docker/.env`.

    docker compose exec app python -m src.infraestructura.adaptadores.entrada.cli.sembrar_demo
    docker compose exec app python -m src.infraestructura.adaptadores.entrada.cli.sembrar_demo --retirar

Las cuentas son `casero01@demo.preciojusto.bo` a `casero51@…`,
`distribuidora01@…` a `03` y `compradora@demo.preciojusto.bo`, todas con la
contraseña `DEMO_CONTRASENA`. El administrador es `ADMIN_INICIAL_CORREO` con
`ADMIN_INICIAL_CONTRASENA` (las dos en `docker/.env`). Algunos caseros tienen
combos. `--retirar` da de baja (lógica) todo lo que creó el comando; nada se
borra. Se niega a correr contra Neon.

Para mostrar las consultas con F12 y `/docs`, ver `docs/EXPLICAR_CON_F12.md`.

## Ver la base con Navicat (u otro cliente)

La base de Docker escucha solo en esta computadora: servidor `127.0.0.1`,
puerto `5433`, base `preciojusto`, usuario `preciojusto` y la contraseña de
`POSTGRES_PASSWORD` en `docker/.env`. En Navicat: Conexión → PostgreSQL con
esos datos; para el modelo físico, clic derecho en el esquema `public` →
"Reverse Schema to Model". El mismo modelo, como SQL (solo estructura, sin
datos), se saca con:

    docker compose exec -T db pg_dump -U preciojusto -d preciojusto --schema-only --no-owner --no-privileges > modelo_fisico.sql

## Ver la base con nombres sencillos

    docker compose exec -T db psql -U preciojusto -d preciojusto < docker/consultas_sencillas.sql

Crea el esquema `consultas` con 18 vistas de nombre simple (`consultas.precios`,
`consultas.lugares_de_venta`, `consultas.listas`…), que en Navicat se ven como
tablas. El sistema no las usa; se quitan con `DROP SCHEMA consultas CASCADE;`.
La lista completa está en `docs/BASE_DE_DATOS.md`.

## Copiar desde Neon

`herramientas\copiar_desde_neon.cmd` lee la cadena de Neon de `backend\.env`,
hace `pg_dump` (Neon solo se lee) y la restaura en `db`. Reemplaza las tablas
que vienen de Neon (productos, mercados, observaciones, corridas); las cuentas
locales se conservan mientras Neon no tenga tabla de usuarios.

## Restaurar un respaldo

    docker compose exec -T respaldos sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner /respaldos/preciojusto_AAAA-MM-DD_HHMM.dump'
    docker compose restart app

## El script de inicio de la base

`docker/init/01_esquema.sql` crea la estructura completa (18 tablas y el esquema `consultas` con sus
vistas). `docker-compose.yml` lo monta en `/docker-entrypoint-initdb.d`, la carpeta que la imagen de
PostgreSQL ejecuta una sola vez cuando el volumen de datos está vacío. Con una base que ya existe no
hace nada. No trae datos ni contraseñas.

Para verla desde un IDE (IntelliJ, DataGrip, VS Code): host `localhost`, puerto `5433`, base y usuario
`preciojusto`, y la contraseña de `POSTGRES_PASSWORD` en `docker/.env`. Hay consultas listas para
mostrar en `docs/consultas_para_mostrar.sql`.
