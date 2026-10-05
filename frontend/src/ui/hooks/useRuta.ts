import { useCallback, useEffect, useState } from "react";

/**
 * Rutas por hash (#/ingresar, #/admin). Alcanzan para tres pantallas, no
 * necesitan que el servidor conozca las rutas (el backend sirve un solo
 * index.html) y no suman una dependencia.
 */
export type Ruta = "precios" | "ingresar" | "admin";

function leer(): Ruta {
  const hash = globalThis.location?.hash ?? "";
  if (hash.startsWith("#/ingresar")) return "ingresar";
  if (hash.startsWith("#/admin")) return "admin";
  return "precios";
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
