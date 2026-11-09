/**
 * Los puestos del mercado elegido en el mapa, con su inventario y sus ofertas
 * vigentes (C143): con esto el mapa los abre como ramas alrededor del mercado.
 */
import { useEffect, useState } from "react";

import type { Oferta, PuestoConInventario } from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";

/** La API da hasta 50 productos por puesto: en la ventana del puesto entran todos. */
const ARTICULOS_POR_PUESTO = 50;

export interface PuestosDelElegido {
  readonly codigoMercado: string;
  readonly puestos: readonly PuestoConInventario[];
  /** Todas las ofertas vigentes del mercado, de cualquier producto. */
  readonly ofertas: readonly Oferta[];
  readonly fallo: boolean;
}

export function useRamasDelMercado(
  contenedor: Contenedor,
  codigoMercado: string | null,
  producto: string | null,
): PuestosDelElegido | null {
  const [datos, setDatos] = useState<PuestosDelElegido | null>(null);

  useEffect(() => {
    setDatos(null);
    if (!codigoMercado) return;
    let vigente = true;
    Promise.all([
      contenedor.mercados.puestos(codigoMercado, { producto: producto ?? undefined, articulos: ARTICULOS_POR_PUESTO }),
      // Sin ofertas el puesto igual se muestra: que falle esto no tapa lo demás.
      contenedor.ofertas.vigentes({ mercado: codigoMercado }).catch(() => [] as Oferta[]),
    ]).then(
      ([d, ofertas]) => vigente && setDatos({ codigoMercado, puestos: d.puestos, ofertas, fallo: false }),
      () => vigente && setDatos({ codigoMercado, puestos: [], ofertas: [], fallo: true }),
    );
    return () => {
      vigente = false;
    };
  }, [contenedor, codigoMercado, producto]);

  return datos;
}
