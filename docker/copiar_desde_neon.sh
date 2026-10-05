#!/bin/sh
# Copia la base de Neon a la base del contenedor "db".
#
# Neon NO se modifica: solo se lee (pg_dump). La base local se reemplaza por
# la copia. Se usa así, desde la raíz del proyecto:
#
#   docker compose run --rm --no-deps --entrypoint sh -e NEON_URL="postgresql://..." respaldos /scripts/copiar_desde_neon.sh
#
# (herramientas/copiar_desde_neon.cmd lo hace leyendo la cadena de backend/.env)
set -eu
: "${NEON_URL:?Falta NEON_URL}"

# pg_dump necesita la conexión DIRECTA de Neon, no la del pooler.
ORIGEN="$(echo "$NEON_URL" | sed 's/-pooler\././')"
export PGPASSWORD="$POSTGRES_PASSWORD"

echo "Leyendo Neon y copiando a la base local..."
pg_dump "$ORIGEN" -Fc --no-owner --no-privileges -f /tmp/neon.dump
pg_restore -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges /tmp/neon.dump
rm -f /tmp/neon.dump

echo "Copia terminada. Filas por tabla en la base local:"
psql -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "
  SELECT 'producto', count(*) FROM producto UNION ALL
  SELECT 'mercado', count(*) FROM mercado UNION ALL
  SELECT 'observacion_precio', count(*) FROM observacion_precio" | tr '|' ' '
