/** Conecta React con CercaDeMi: guarda la ubicación una vez y ordena lo que haya en el mapa. */
import { useMemo, useState } from "react";

import { masCercanos, type Coordenadas, type MarcadorMapa, type Zona } from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";

export function useCercania(contenedor: Contenedor, marcadores: readonly MarcadorMapa[]) {
  const [ubicacion, setUbicacion] = useState<Coordenadas | null>(null);
  const [buscando, setBuscando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  /** Si la ubicación es una zona elegida a mano (y no el GPS), cuál. */
  const [zona, setZona] = useState<string | null>(null);

  async function buscar() {
    setBuscando(true);
    setError(null);
    try {
      setUbicacion(await contenedor.cercaDeMi.ubicar());
      setZona(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo obtener su ubicación.");
    } finally {
      setBuscando(false);
    }
  }

  const cercanos = useMemo(() => (ubicacion ? masCercanos(marcadores, ubicacion) : []), [marcadores, ubicacion]);

  function elegirZona(z: Zona) {
    setUbicacion({ latitud: z.latitud, longitud: z.longitud });
    setZona(z.nombre);
    setError(null);
  }

  function olvidar() {
    setUbicacion(null);
    setZona(null);
  }

  return { ubicacion, zona, cercanos, buscando, error, buscar, elegirZona, olvidar };
}
