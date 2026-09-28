#!/usr/bin/env python3
"""
Adaptador de entrada por línea de comandos: la comprobación previa.

    python -m src.infraestructura.adaptadores.entrada.cli.estado

Dice, antes de una demo, si la configuración sirve y si los datos están
donde tienen que estar. No escribe nada: solo lee.

Códigos de salida:
    0  todo listo
    1  hay base configurada pero no responde
    2  no hay BASE_DATOS_URL: la API arrancaría con datos de ejemplo
"""
from __future__ import annotations

import sys

from sqlalchemy import text

from src.configuracion import ARCHIVO_ENV, config
from src.infraestructura.adaptadores.salida.persistencia.sesion import crear_motor


def _servidor(url: str) -> str:
    """El host, sin usuario ni contraseña: esto se muestra en pantalla."""
    try:
        return url.split("@", 1)[1].split(".", 1)[0]
    except IndexError:
        return "desconocido"


def main() -> int:
    print(f"\nConfiguración: {ARCHIVO_ENV}")
    print(f"  existe: {'sí' if ARCHIVO_ENV.exists() else 'NO'}")

    if not config.base_datos_url:
        print("\n  [!] BASE_DATOS_URL está vacía.")
        print("      La API arranca igual, pero con datos de ejemplo en memoria")
        print("      (4 mercados), no con los 88 puntos de venta reales.")
        print(f"      Para usar la base: copiar la cadena de Neon en {ARCHIVO_ENV}\n")
        return 2

    print(f"  servidor: {_servidor(config.base_datos_url)}")
    print(f"  CORS para: {', '.join(config.origenes)}")

    try:
        with crear_motor(config.base_datos_url).connect() as conexion:
            contar = lambda tabla: conexion.execute(text(f"select count(*) from {tabla}")).scalar()  # noqa: E731
            observaciones, mercados, productos = (
                contar("observacion_precio"), contar("mercado"), contar("producto")
            )
    except Exception as e:   # noqa: BLE001 - se reporta, no se oculta
        print(f"\n  [X] La base no responde: {type(e).__name__}")
        print(f"      {str(e).splitlines()[0][:160]}")
        print("\n      Causas típicas:")
        print("      - la cadena está vieja (la contraseña se rota): copiarla de Neon > Connect")
        print("      - sin internet: usar el PLAN B (frontend/.env.local con VITE_ORIGEN_DATOS=memoria)\n")
        return 1

    print("\n  [OK] La base responde.")
    print(f"       observaciones de precio: {observaciones}")
    print(f"       puntos de venta:         {mercados}")
    print(f"       productos:               {productos}")

    if not mercados or not productos:
        print("\n  [!] El catálogo está vacío: el mapa no tendría puntos.")
        print("      Sembrarlo con:  python -m src.infraestructura.adaptadores.entrada.cli.sembrar")
        return 1

    print("\n  Todo listo para la demo.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
