#!/bin/sh
# Respaldo diario de la base, dentro del contenedor "respaldos".
#
# A la hora RESPALDO_HORA (hora de Bolivia) hace un pg_dump en formato
# comprimido a /respaldos (la carpeta ./respaldos del proyecto) y borra los
# que tengan más de RESPALDO_DIAS días. Para restaurar uno, ver docker/LEEME.md.
set -eu

HORA="${RESPALDO_HORA:-03:00}"
DIAS="${RESPALDO_DIAS:-7}"
export PGPASSWORD="$POSTGRES_PASSWORD"
# Bolivia es UTC-4 todo el año; en notación POSIX eso se escribe "BOT4".
export TZ="BOT4"

respaldar() {
  archivo="/respaldos/preciojusto_$(date +%Y-%m-%d_%H%M).dump"
  if pg_dump -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f "$archivo.parcial"; then
    mv "$archivo.parcial" "$archivo"
    echo "$(date '+%F %T') respaldo listo: $(basename "$archivo") ($(du -h "$archivo" | cut -f1))"
  else
    rm -f "$archivo.parcial"
    echo "$(date '+%F %T') ERROR: el respaldo falló" >&2
  fi
  find /respaldos -name 'preciojusto_*.dump' -mtime +"$DIAS" -print -delete
}

echo "Respaldos: uno por día a las $HORA (hora de Bolivia), se guardan $DIAS días."
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
