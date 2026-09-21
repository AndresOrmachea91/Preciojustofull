/**
 * Conecta React con el caso de uso VerMapa. Único punto de contacto: el
 * componente del mapa no conoce repositorios ni HTTP.
 */
import { useCallback, useEffect, useState } from "react";

import type { ResultadoMapa } from "@/aplicacion/casosUso/verMapa";
import type { Contenedor } from "@/infraestructura/contenedor";

export function useMapa(contenedor: Contenedor, codigoProducto: string) {
  const [datos, setDatos] = useState<ResultadoMapa | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const consultar = useCallback(async () => {
    if (!codigoProducto) return;   // el catálogo todavía no eligió producto
    setCargando(true);
    setError(null);
    setDatos(null);   // nunca mostrar el precio del producto anterior bajo el nombre del nuevo
    try {
      setDatos(await contenedor.verMapa.ejecutar(codigoProducto));
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo cargar el mapa");
      setDatos(null);
    } finally {
      setCargando(false);
    }
  }, [contenedor, codigoProducto]);

  useEffect(() => {
    void consultar();
  }, [consultar]);

  return { datos, cargando, error, reintentar: consultar };
}
