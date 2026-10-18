#!/bin/sh
# Respaldo diario de la base, dentro del contenedor "respaldos".
#
# A la hora RESPALDO_HORA (hora de Bolivia) hace un pg_dump en formato
# comprimido a /respaldos (la carpeta ./respaldos del proyecto) y borra los
# que tengan más de RESPALDO_DIAS días. Para restaurar uno, ver docker/LEEME.md.
#
# Un respaldo que nunca se restauró no se sabe si sirve (C132). Por eso,
# después de cada pg_dump se RESTAURA de prueba en una base aparte, se
# cuentan las observaciones y se borra esa base. El resultado queda en
# /respaldos/estado.json, que el panel de salud de la web lee.
set -eu

HORA="${RESPALDO_HORA:-03:00}"
DIAS="${RESPALDO_DIAS:-7}"
BASE_PRUEBA="verificacion_respaldo"
export PGPASSWORD="$POSTGRES_PASSWORD"
# Bolivia es UTC-4 todo el año; en notación POSIX eso se escribe "BOT4".
export TZ="BOT4"

escribir_estado() {
  # $1 archivo  $2 verificado (true/false)  $3 filas  $4 detalle
  tamano=0
  [ -f "/respaldos/$1" ] && tamano=$(stat -c %s "/respaldos/$1")
  detalle=$(printf '%s' "$4" | tr '"\\' "''" | tr -d '\n' | cut -c1-300)
  printf '{"fecha": "%s", "archivo": "%s", "tamano_bytes": %s, "verificado": %s, "filas_observaciones": %s, "detalle": "%s"}\n' \
    "$(date +%Y-%m-%dT%H:%M:%S-04:00)" "$1" "$tamano" "$2" "${3:-null}" "$detalle" > /respaldos/estado.json.tmp
  mv /respaldos/estado.json.tmp /respaldos/estado.json
}

verificar() {
  # Restaura el respaldo en una base de prueba y compara las observaciones.
  archivo="$1"
  dropdb -h db -U "$POSTGRES_USER" --if-exists "$BASE_PRUEBA"
  createdb -h db -U "$POSTGRES_USER" "$BASE_PRUEBA"
  if pg_restore -h db -U "$POSTGRES_USER" -d "$BASE_PRUEBA" --no-owner --exit-on-error "/respaldos/$archivo" 2>/tmp/restauracion.log; then
    filas=$(psql -h db -U "$POSTGRES_USER" -d "$BASE_PRUEBA" -tAc "select count(*) from observacion_precio")
    originales=$(psql -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select count(*) from observacion_precio")
    # El original pudo crecer entre el dump y el conteo (el recolector);
    # lo que no puede es que el respaldo tenga MÁS filas o ninguna.
    if [ "$filas" -gt 0 ] && [ "$filas" -le "$originales" ]; then
      escribir_estado "$archivo" true "$filas" "restaurado de prueba: $filas de $originales observaciones"
      echo "$(date '+%F %T') respaldo verificado: $filas observaciones restauradas"
    else
      escribir_estado "$archivo" false "$filas" "la restauración trajo $filas observaciones y la base tiene $originales"
      echo "$(date '+%F %T') ERROR: la restauración de prueba no cuadra ($filas / $originales)" >&2
    fi
  else
    escribir_estado "$archivo" false "" "pg_restore falló: $(tail -n 3 /tmp/restauracion.log)"
    echo "$(date '+%F %T') ERROR: no se pudo restaurar el respaldo de prueba" >&2
  fi
  dropdb -h db -U "$POSTGRES_USER" --if-exists "$BASE_PRUEBA"
}

respaldar() {
  nombre="preciojusto_$(date +%Y-%m-%d_%H%M).dump"
  archivo="/respaldos/$nombre"
  if pg_dump -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f "$archivo.parcial"; then
    mv "$archivo.parcial" "$archivo"
    echo "$(date '+%F %T') respaldo listo: $nombre ($(du -h "$archivo" | cut -f1))"
    verificar "$nombre" || escribir_estado "$nombre" false "" "la verificación no pudo correr"
  else
    rm -f "$archivo.parcial"
    escribir_estado "$nombre" false "" "pg_dump falló"
    echo "$(date '+%F %T') ERROR: el respaldo falló" >&2
  fi
  find /respaldos -name 'preciojusto_*.dump' -mtime +"$DIAS" -print -delete
}

# Un respaldo verificado ahora y salir:
#   docker compose run --rm -e RESPALDO_UNA_VEZ=1 respaldos
if [ "${RESPALDO_UNA_VEZ:-0}" = "1" ]; then
  respaldar
  exit 0
fi

echo "Respaldos: uno por día a las $HORA (hora de Bolivia), se guardan $DIAS días y se restauran de prueba."
[ "${RESPALDO_AL_INICIAR:-0}" = "1" ] && respaldar

# No se espera el minuto exacto: si a la hora del respaldo el equipo estaba
# suspendido o apagado, se respalda apenas despierta. "Ya se hizo hoy" se
# mira en la carpeta, así que reiniciar el contenedor no lo repite.
hora_numero=$(echo "$HORA" | tr -d ':' | sed 's/^0*//')
hecho_hoy() { ls /respaldos/preciojusto_"$(date +%F)"_*.dump >/dev/null 2>&1; }

while true; do
  ahora=$(date +%H%M | sed 's/^0*//')
  if [ "${ahora:-0}" -ge "${hora_numero:-0}" ] && ! hecho_hoy; then
    respaldar
  fi
  sleep 60
done
