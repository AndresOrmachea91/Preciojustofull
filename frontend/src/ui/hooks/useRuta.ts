import { useCallback, useEffect, useState } from "react";

/**
 * Rutas por hash (#/ingresar, #/admin...). Alcanzan para estas pantallas, no
 * necesitan que el servidor conozca las rutas (el backend sirve un solo
 * index.html) y no suman una dependencia.
 */
export type Ruta = "precios" | "ingresar" | "mi-cuenta" | "mi-puesto" | "admin";

const RUTAS: readonly Ruta[] = ["ingresar", "mi-cuenta", "mi-puesto", "admin"];

function leer(): Ruta {
  const hash = globalThis.location?.hash ?? "";
  return RUTAS.find((r) => hash.startsWith(`#/${r}`)) ?? "precios";
}

export function useRuta(): [Ruta, (ruta: Ruta) => void] {
  const [ruta, setRuta] = useState<Ruta>(leer);

  useEffect(() => {
    const alCambiar = () => setRuta(leer());
    globalThis.addEventListener?.("hashchange", alCambiar);
    return () => globalThis.removeEventListener?.("hashchange", alCambiar);
  }, []);

  const ir = useCallback((destino: Ruta) => {
    const hash = destino === "precios" ? "#/" : `#/${destino}`;
    if (globalThis.location) globalThis.location.hash = hash;
    setRuta(destino);
  }, []);

  return [ruta, ir];
}
