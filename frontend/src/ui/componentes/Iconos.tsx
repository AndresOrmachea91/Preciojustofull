/**
 * Iconos de trazo, dibujados en SVG: no suman una dependencia y heredan el
 * color del texto (currentColor), así que siguen el tema claro y oscuro.
 * Son decorativos: el texto de al lado es el que nombra la acción.
 */
import type { ReactNode } from "react";

export type NombreIcono =
  | "precios" | "listas" | "puesto" | "admin" | "ingresar" | "registrarse"
  | "salir" | "buscar" | "elegido" | "menu" | "ubicacion" | "confiabilidad" | "salud" | "planilla";

const TRAZOS: Record<NombreIcono, ReactNode> = {
  // Etiqueta de precio
  precios: (
    <>
      <path d="M3 12V4a1 1 0 0 1 1-1h8l9 9-9 9z" />
      <circle cx="7.5" cy="7.5" r="1.5" />
    </>
  ),
  // Lista con viñetas
  listas: (
    <>
      <path d="M9 6h11M9 12h11M9 18h11" />
      <path d="M4 6h.01M4 12h.01M4 18h.01" />
    </>
  ),
  // Puesto con toldo
  puesto: (
    <>
      <path d="M3 9l1.5-5h15L21 9" />
      <path d="M3 9a3 3 0 0 0 6 0 3 3 0 0 0 6 0 3 3 0 0 0 6 0" />
      <path d="M5 12v8h14v-8M10 20v-5h4v5" />
    </>
  ),
  // Escudo
  admin: (
    <>
      <path d="M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z" />
      <path d="M9 12l2 2 4-4" />
    </>
  ),
  // Flecha que entra a una puerta
  ingresar: (
    <>
      <path d="M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4" />
      <path d="M3 12h11M10 8l4 4-4 4" />
    </>
  ),
  // Persona con un signo más
  registrarse: (
    <>
      <circle cx="9" cy="8" r="4" />
      <path d="M2 21c0-3.9 3.1-7 7-7s7 3.1 7 7" />
      <path d="M19 8v6M16 11h6" />
    </>
  ),
  // Flecha que sale de una puerta
  salir: (
    <>
      <path d="M10 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4" />
      <path d="M21 12H10M17 8l4 4-4 4" />
    </>
  ),
  buscar: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="M20 20l-4-4" />
    </>
  ),
  elegido: <path d="M5 12l5 5 9-10" />,
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  // Diana: qué tan cerca cae el estimado de lo medido
  confiabilidad: (
    <>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="4" />
      <path d="M12 12h.01" />
    </>
  ),
  // Pulso
  salud: <path d="M3 12h4l3-7 4 14 3-7h4" />,
  // Hoja con filas
  planilla: (
    <>
      <path d="M6 3h9l4 4v14H6z" />
      <path d="M9 11h7M9 15h7M9 19h4" />
    </>
  ),
  // Alfiler de mapa
  ubicacion: (
    <>
      <path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z" />
      <circle cx="12" cy="9.5" r="2.5" />
    </>
  ),
};

export function Icono({ nombre, tamano = 20 }: { nombre: NombreIcono; tamano?: number }) {
  return (
    <svg
      className="icono"
      width={tamano}
      height={tamano}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {TRAZOS[nombre]}
    </svg>
  );
}
