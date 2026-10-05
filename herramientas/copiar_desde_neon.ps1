# Copia la base de Neon a la base del contenedor "db" (docker compose).
# Neon solo se LEE. La base local se reemplaza por la copia.
#
#   herramientas\copiar_desde_neon.cmd
#
# Lee la cadena de Neon de backend\.env (BASE_DATOS_URL), para no tener que
# escribirla en la terminal ni dejarla en el historial.
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$linea = Get-Content "$raiz\backend\.env" | Where-Object { $_ -match '^\s*BASE_DATOS_URL\s*=' } | Select-Object -First 1
if (-not $linea) { throw "No hay BASE_DATOS_URL en backend\.env" }
$neon = ($linea -split '=', 2)[1].Trim()
if ($neon -notmatch 'neon\.tech') { throw "BASE_DATOS_URL de backend\.env no parece ser de Neon" }

Push-Location $raiz
try {
  docker compose run --rm --no-deps --entrypoint sh -e NEON_URL="$neon" respaldos /scripts/copiar_desde_neon.sh
  if ($LASTEXITCODE -ne 0) { throw "La copia falló (código $LASTEXITCODE)" }
  # La API vuelve a verificar el esquema y el administrador inicial.
  docker compose restart app | Out-Null
  Write-Host "Listo. La aplicación en contenedores ya usa la copia: http://localhost:8088"
} finally { Pop-Location }
