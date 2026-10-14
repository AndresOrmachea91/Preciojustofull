/** Conecta React con el caso de uso VerHistorial: el gráfico no sabe de HTTP. */
import { useEffect, useState } from "react";

import type { ResultadoHistorial } from "@/aplicacion/casosUso/publico/verHistorial";
import type { Contenedor } from "@/infraestructura/contenedor";

export function useHistorial(contenedor: Contenedor, codigoProducto: string) {
  const [datos, setDatos] = useState<ResultadoHistorial | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!codigoProducto) return;
    let vigente = true;
    setDatos(null);
    setError(null);
    contenedor.verHistorial.ejecutar(codigoProducto).then(
      (d) => vigente && setDatos(d),
      (e) => vigente && setError(e instanceof Error ? e.message : "No se pudo cargar la evolución del precio"),
    );
    // Si se cambia de producto antes de que llegue la respuesta, la vieja se descarta.
    return () => {
      vigente = false;
    };
  }, [contenedor, codigoProducto]);

  return { datos, error };
}
