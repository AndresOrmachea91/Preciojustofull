#!/bin/sh
# Lleva la base de la laptop (contenedor "db" de docker-compose.yml) al
# servidor. Se corre en la LAPTOP, desde la carpeta del proyecto:
#
#   sh herramientas/llevar_datos_al_servidor.sh usuario@IP-DEL-SERVIDOR
#
# 1. Saca un respaldo comprimido (pg_dump -Fc) del contenedor local.
# 2. Lo copia al servidor por SSH (scp).
# 3. En el servidor lo restaura en el contenedor "db" de producción.
# La base del servidor se REEMPLAZA: usar una sola vez, antes de abrir al público.
set -eu

DESTINO="${1:?Uso: sh herramientas/llevar_datos_al_servidor.sh usuario@servidor}"
CARPETA_REMOTA="${2:-preciojusto}"
ARCHIVO="preciojusto_para_servidor_$(date +%Y-%m-%d_%H%M).dump"

echo "1/3 Respaldo de la base local…"
docker compose --env-file docker/.env exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "respaldos/$ARCHIVO"
ls -lh "respaldos/$ARCHIVO"

echo "2/3 Copia al servidor ($DESTINO)…"
scp "respaldos/$ARCHIVO" "$DESTINO:$CARPETA_REMOTA/respaldos/$ARCHIVO"

echo "3/3 Restauración en el servidor…"
ssh "$DESTINO" "cd $CARPETA_REMOTA && docker compose -f docker-compose.produccion.yml --env-file docker/.env.produccion exec -T db \
  sh -c 'pg_restore -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" --clean --if-exists --no-owner' < respaldos/$ARCHIVO"

echo "Listo. Revise https://SU-DOMINIO y el panel de auditoría."
