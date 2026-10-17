import { useCallback, useEffect, useState } from "react";

/**
 * Rutas por hash (#/ingresar, #/admin...). Alcanzan para estas pantallas, no
 * necesitan que el servidor conozca las rutas (el backend sirve un solo
 * index.html) y no suman una dependencia.
 */
export type Ruta =
  | "precios" | "ingresar" | "registrarse" | "recuperar" | "restablecer" | "mi-cuenta" | "mi-puesto" | "admin";

const RUTAS: readonly Ruta[] = ["ingresar", "registrarse", "recuperar", "restablecer", "mi-cuenta", "mi-puesto", "admin"];

/** El enlace de una ruta, para usar en <a href>. */
export function hrefDe(ruta: Ruta): string {
  return ruta === "precios" ? "#/" : `#/${ruta}`;
}

/** Un parámetro de la ruta actual: "#/restablecer?token=abc" → parametroDeRuta("token") = "abc". */
export function parametroDeRuta(nombre: string): string {
  const hash = globalThis.location?.hash ?? "";
  const consulta = hash.includes("?") ? hash.slice(hash.indexOf("?") + 1) : "";
  return new URLSearchParams(consulta).get(nombre) ?? "";
}

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
    if (globalThis.location) globalThis.location.hash = hrefDe(destino);
    setRuta(destino);
  }, []);

  return [ruta, ir];
}
