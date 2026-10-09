/**
 * Mapa para MARCAR una ubicación: un clic pone (o mueve) el punto. Lo usa
 * el administrador al crear o editar un mercado o una tienda. Como el otro
 * mapa, solo dibuja: la regla de qué ubicación es válida está en el dominio.
 */
import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const CENTRO_LA_PAZ: [number, number] = [-16.505, -68.13];

interface Props {
  readonly latitud: number | null;
  readonly longitud: number | null;
  readonly onCambiar: (latitud: number, longitud: number) => void;
}

export function MapaSelectorUbicacion({ latitud, longitud, onCambiar }: Props) {
  const contenedor = useRef<HTMLDivElement>(null);
  const mapa = useRef<L.Map | null>(null);
  const marca = useRef<L.CircleMarker | null>(null);
  // El último callback, sin recrear el mapa cada vez que cambia.
  const alCambiar = useRef(onCambiar);
  alCambiar.current = onCambiar;

  useEffect(() => {
    if (!contenedor.current || mapa.current) return;
    const centro: [number, number] = latitud !== null && longitud !== null ? [latitud, longitud] : CENTRO_LA_PAZ;
    mapa.current = L.map(contenedor.current).setView(centro, latitud !== null ? 16 : 13);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(mapa.current);
    mapa.current.on("click", (e: L.LeafletMouseEvent) => {
      // 6 decimales: unos 10 cm. Más no aporta y ensucia la base.
      alCambiar.current(Number(e.latlng.lat.toFixed(6)), Number(e.latlng.lng.toFixed(6)));
    });
    return () => {
      mapa.current?.remove();
      mapa.current = null;
      marca.current = null;
    };
    // El mapa se crea una sola vez; la marca se mueve en el efecto de abajo.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!mapa.current) return;
    if (latitud === null || longitud === null) {
      marca.current?.remove();
      marca.current = null;
      return;
    }
    if (marca.current) {
      marca.current.setLatLng([latitud, longitud]);
    } else {
      marca.current = L.circleMarker([latitud, longitud], {
        radius: 9, color: "#12211d", weight: 3, fillColor: "#1c6b57", fillOpacity: 0.9,
      }).addTo(mapa.current);
    }
  }, [latitud, longitud]);

  return (
    <div
      ref={contenedor}
      className="mapa mapa--selector"
      role="region"
      aria-label="Mapa para marcar la ubicación: haga clic donde está el punto de venta"
    />
  );
}
