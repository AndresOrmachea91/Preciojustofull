import { useCallback, useEffect, useState } from "react";

/**
 * Rutas por hash (#/ingresar, #/admin...). Alcanzan para estas pantallas, no
 * necesitan que el servidor conozca las rutas (el backend sirve un solo
 * index.html) y no suman una dependencia.
 */
export type Ruta =
  | "precios" | "mercados" | "mercado" | "ofertas" | "confiabilidad" | "ingresar" | "registrarse" | "recuperar"
  | "restablecer" | "mi-cuenta" | "mi-puesto" | "admin";

const RUTAS: readonly Ruta[] = [
  "mercados", "mercado", "ofertas", "confiabilidad", "ingresar", "registrarse", "recuperar", "restablecer",
  "mi-cuenta", "mi-puesto", "admin",
];

/** El enlace de una ruta, para usar en <a href>. */
export function hrefDe(ruta: Ruta): string {
  return ruta === "precios" ? "#/" : `#/${ruta}`;
}

/** El enlace a la ficha de un mercado (C134): #/mercado?codigo=rodriguez. */
export function hrefMercado(codigo: string): string {
  return `#/mercado?codigo=${encodeURIComponent(codigo)}`;
}

/** El enlace a un puesto: abre la ficha del mercado en sus puestos y lo resalta. */
export function hrefPuesto(codigoMercado: string, numero: string): string {
  return `${hrefMercado(codigoMercado)}&puesto=${encodeURIComponent(numero)}`;
}

/** Un parámetro de la ruta actual: "#/restablecer?token=abc" → parametroDeRuta("token") = "abc". */
export function parametroDeRuta(nombre: string): string {
  const hash = globalThis.location?.hash ?? "";
  const consulta = hash.includes("?") ? hash.slice(hash.indexOf("?") + 1) : "";
  return new URLSearchParams(consulta).get(nombre) ?? "";
}

function leer(): Ruta {
  // Se compara la ruta entera, sin la consulta: "mercado" no es "mercados".
  const camino = (globalThis.location?.hash ?? "").replace(/^#\/?/, "").split("?")[0];
  return RUTAS.find((r) => r === camino) ?? "precios";
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

/** Un parámetro de la ruta que se actualiza si cambia el hash (de un mercado a otro, sin cambiar de pantalla). */
export function useParametroDeRuta(nombre: string): string {
  const [valor, setValor] = useState(() => parametroDeRuta(nombre));
  useEffect(() => {
    const alCambiar = () => setValor(parametroDeRuta(nombre));
    globalThis.addEventListener?.("hashchange", alCambiar);
    return () => globalThis.removeEventListener?.("hashchange", alCambiar);
  }, [nombre]);
  return valor;
}
