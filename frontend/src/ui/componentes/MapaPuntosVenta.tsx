/**
 * El mapa. Leaflet es una librería de dibujo, no de dominio: este
 * componente recibe los marcadores YA resueltos por el caso de uso VerMapa
 * y solo los pinta. No sabe de HTTP ni de repositorios.
 */
import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import type { MarcadorMapa, TipoPuntoVenta } from "@/dominio/modelo";

/** Centro del municipio de La Paz. */
const CENTRO_LA_PAZ: [number, number] = [-16.505, -68.13];
const ZOOM_INICIAL = 13;

/** Diferenciación visual por tipo: color del relleno. */
const COLOR_TIPO: Record<TipoPuntoVenta, string> = {
  mercado: "#1c6b57",
  supermercado: "#1f5aa6",
  minimarket: "#4c8fd6",
  tienda: "#7a8f88",
  mayorista: "#b0560f",
};

/** Con el dedo un punto de 14 px no se acierta: en pantallas táctiles, más grande. */
const TACTIL = globalThis.matchMedia?.("(pointer: coarse)").matches ?? false;

function radio(activo: boolean): number {
  return (TACTIL ? 10 : 7) + (activo ? 4 : 0);
}

function estiloDe(activo: boolean): L.CircleMarkerOptions {
  return { radius: radio(activo), color: activo ? "#12211d" : "#ffffff", weight: activo ? 3 : 1.5 };
}

interface Props {
  readonly marcadores: readonly MarcadorMapa[];
  readonly seleccionado: string | null;
  readonly onSeleccionar: (codigo: string) => void;
}

export function MapaPuntosVenta({ marcadores, seleccionado, onSeleccionar }: Props) {
  const contenedor = useRef<HTMLDivElement>(null);
  const mapa = useRef<L.Map | null>(null);
  const capa = useRef<L.LayerGroup | null>(null);

  // El mapa se crea una vez; los marcadores se redibujan cuando cambian.
  useEffect(() => {
    if (!contenedor.current || mapa.current) return;
    mapa.current = L.map(contenedor.current, { zoomControl: true }).setView(CENTRO_LA_PAZ, ZOOM_INICIAL);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(mapa.current);
    capa.current = L.layerGroup().addTo(mapa.current);
    return () => {
      mapa.current?.remove();
      mapa.current = null;
      capa.current = null;
    };
  }, []);

  // Los puntos se crean cuando cambian los datos; elegir uno solo cambia el
  // estilo del anterior y del nuevo, no redibuja los 88.
  const puntos = useRef(new Map<string, L.CircleMarker>());
  const elegido = useRef<string | null>(null);

  useEffect(() => {
    const grupo = capa.current;
    if (!grupo) return;
    grupo.clearLayers();
    puntos.current.clear();
    for (const { mercado, precio } of marcadores) {
      if (mercado.latitud === undefined || mercado.longitud === undefined) continue;
      const punto = L.circleMarker([mercado.latitud, mercado.longitud], {
        ...estiloDe(false),
        fillColor: COLOR_TIPO[mercado.tipo],
        // Sin precio: el punto está, pero apagado. No se inventa nada.
        fillOpacity: precio ? 0.9 : 0.35,
        // Un estimado se ve punteado; un observado, sólido.
        dashArray: precio?.procedencia === "estimado" ? "3 3" : undefined,
      });
      punto.bindTooltip(mercado.nombre, { direction: "top", offset: [0, -6] });
      punto.on("click", () => onSeleccionar(mercado.codigo));
      punto.addTo(grupo);
      puntos.current.set(mercado.codigo, punto);
    }
    elegido.current = null;
  }, [marcadores, onSeleccionar]);

  useEffect(() => {
    if (elegido.current === seleccionado) return;
    if (elegido.current) puntos.current.get(elegido.current)?.setStyle(estiloDe(false)).setRadius(radio(false));
    const nuevo = seleccionado ? puntos.current.get(seleccionado) : undefined;
    nuevo?.setStyle(estiloDe(true)).setRadius(radio(true)).bringToFront();
    elegido.current = seleccionado;
  }, [seleccionado, marcadores]);

  return (
    <div
      ref={contenedor}
      className="mapa"
      role="region"
      aria-label="Mapa de puntos de venta de La Paz"
      data-marcadores={marcadores.length}
    />
  );
}
