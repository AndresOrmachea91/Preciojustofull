/**
 * El hook conecta React con el caso de uso. Es el ÚNICO punto de contacto.
 * Ningún componente conoce repositorios ni HTTP.
 */
import { useCallback, useEffect, useState } from "react";

import type { ResultadoComparativa } from "@/aplicacion/casosUso/compararMercados";
import type { Contenedor } from "@/infraestructura/contenedor";

export function useComparativa(contenedor: Contenedor, codigoProducto: string) {
  const [datos, setDatos] = useState<ResultadoComparativa | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const consultar = useCallback(async () => {
    if (!codigoProducto) return;   // el catálogo todavía no eligió producto
    setCargando(true);
    setError(null);
    setDatos(null);   // nunca mostrar el precio del producto anterior bajo el nombre del nuevo
    try {
      setDatos(await contenedor.compararMercados.ejecutar(codigoProducto));
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo consultar el precio");
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

