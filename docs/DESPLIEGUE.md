# Llevar PrecioJusto a un servidor en la nube

**Decisión:** un **servidor propio (VPS con Linux)** que corre el **mismo
Docker Compose** que la laptop, con **Caddy** al frente para el HTTPS.
No se usan plataformas "backend como servicio" (Supabase, Firebase, etc.): la
base de datos, la API, el recolector y los respaldos son contenedores nuestros,
sobre una máquina alquilada por mes que se puede cambiar de proveedor copiando
dos carpetas.

```
Internet ──443──▶ Caddy (HTTPS automático) ──▶ app (FastAPI + web)
                                                 │
                       recolector (SIIP 11:00) ──┤
                       respaldos (03:00)  ───────┤
                                                 ▼
                                          db (PostgreSQL 18, sin puerto público)
```

## 1. Qué contratar

| Necesidad | Mínimo | Por qué |
|---|---|---|
| Servidor | 2 vCPU, **4 GB de RAM**, 40 GB de disco, Ubuntu 24.04 LTS | En la laptop el sistema completo cabe en 2,5 GB; 4 GB deja margen para construir la imagen |
| Dominio | Uno propio (por ejemplo `.bo` en NIC Bolivia, o `.com`) | Caddy necesita un nombre para pedir el certificado HTTPS |
| Correo saliente | Un SMTP real (el del dominio o uno transaccional) | Para "recuperar contraseña" |

Proveedores de **máquinas virtuales** (no plataformas): Hetzner Cloud, DigitalOcean,
Vultr, Linode/Akamai, AWS Lightsail u Oracle Cloud (tiene una capa gratuita con
máquinas ARM). Todos entregan lo mismo: una máquina Linux con IP pública. Con
cualquiera de ellos estos pasos son idénticos.

## 2. Preparar el servidor (una vez)

```sh
# Entrar por SSH con la clave que dio el proveedor
ssh root@IP-DEL-SERVIDOR

# Usuario sin privilegios para la app, y actualizaciones
adduser preciojusto && usermod -aG sudo preciojusto
apt update && apt upgrade -y

# Cortafuegos: solo SSH, HTTP y HTTPS. La base NO se abre.
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable

# Docker (script oficial) y permiso para el usuario
curl -fsSL https://get.docker.com | sh
usermod -aG docker preciojusto
```

En el panel del dominio: un registro **A** que apunte el nombre (por ejemplo
`preciojusto.ejemplo.bo`) a la IP del servidor.

## 3. Subir el sistema

```sh
# En el servidor, como preciojusto
git clone https://github.com/AndresOrmachea91/Preciojustofull.git preciojusto
cd preciojusto
cp docker/.env.produccion.example docker/.env.produccion
nano docker/.env.produccion      # dominio, contraseñas, JWT_SECRETO, SMTP
mkdir -p respaldos

docker compose -f docker-compose.produccion.yml --env-file docker/.env.produccion up -d --build
docker compose -f docker-compose.produccion.yml ps
```

A los pocos segundos Caddy obtiene el certificado y el sistema queda en
`https://SU-DOMINIO`.

## 4. Llevar los datos de la laptop (A7190)

Desde la laptop, con el servidor ya levantado:

```sh
sh herramientas/llevar_datos_al_servidor.sh preciojusto@IP-DEL-SERVIDOR
```

Saca un respaldo de la base local, lo copia por SSH y lo restaura allá. Los
datos de Neon ya están en la base local (se copiaron con
`herramientas/copiar_desde_neon`), así que no hace falta tocar Neon.

## 5. Actualizar después

```sh
cd preciojusto && git pull
docker compose -f docker-compose.produccion.yml --env-file docker/.env.produccion up -d --build
```

## 6. Respaldos fuera del servidor

El contenedor `respaldos` deja un `pg_dump` diario en `~/preciojusto/respaldos`
(14 días). Un disco que falla se lleva también esos respaldos: conviene
bajarlos a otra máquina, por ejemplo desde la laptop una vez por semana:

```sh
scp "preciojusto@IP-DEL-SERVIDOR:preciojusto/respaldos/*.dump" respaldos/servidor/
```

## Qué cambia respecto a la laptop

| | Laptop (`docker-compose.yml`) | Servidor (`docker-compose.produccion.yml`) |
|---|---|---|
| Entrada | `http://localhost:8088` | `https://dominio` vía Caddy (80/443) |
| Base de datos | puerto 5433 solo en la laptop | sin puerto: solo la ven los contenedores |
| Correo | Mailpit (no sale a internet) | SMTP real |
| Secretos | `docker/.env` | `docker/.env.produccion` (no se sube a GitHub) |
| Cabeceras de seguridad | — | HSTS, nosniff, sin iframes, permisos de ubicación solo propios |
