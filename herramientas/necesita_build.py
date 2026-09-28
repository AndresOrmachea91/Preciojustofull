#!/usr/bin/env python3
"""
¿Hay que volver a construir la interfaz antes de servirla?

    python herramientas/necesita_build.py <modo>

Devuelve 1 (sí, reconstruir) o 0 (no hace falta). Lo usa serve.cmd para no
esperar veinte segundos cada vez que se arranca el servidor.

Reconstruye si: no hay build, el build es de otro modo de datos, o algún
archivo del frontend es más nuevo que el build.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FRONTEND = RAIZ / "frontend"
DIST = FRONTEND / "dist"
MARCA_MODO = DIST / ".modo"

# Lo que, al cambiar, invalida el build. node_modules no: es enorme y no
# cambia sin que cambie package.json.
FUENTES = [FRONTEND / "src", FRONTEND / "index.html", FRONTEND / "package.json",
           FRONTEND / "vite.config.ts", FRONTEND / ".env.local"]


def _mas_reciente(ruta: Path) -> float:
    if ruta.is_file():
        return ruta.stat().st_mtime
    if ruta.is_dir():
        return max((f.stat().st_mtime for f in ruta.rglob("*") if f.is_file()), default=0.0)
    return 0.0


def main() -> int:
    modo = (sys.argv[1] if len(sys.argv) > 1 else "http").strip().lower()
    indice = DIST / "index.html"

    if not indice.is_file():
        print("no hay interfaz construida")
        return 1
    if not MARCA_MODO.is_file() or MARCA_MODO.read_text(encoding="utf-8").strip() != modo:
        anterior = MARCA_MODO.read_text(encoding="utf-8").strip() if MARCA_MODO.is_file() else "desconocido"
        print(f"el build es del modo '{anterior}' y se pidio '{modo}'")
        return 1

    construido = indice.stat().st_mtime
    reciente = max(_mas_reciente(f) for f in FUENTES)
    if reciente > construido:
        print("hay cambios en el frontend posteriores al build")
        return 1

    print("el build esta al dia")
    return 0


if __name__ == "__main__":
    sys.exit(main())
