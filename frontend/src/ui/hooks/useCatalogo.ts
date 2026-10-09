import { useEffect, useState } from "react";

import type { Mercado, Producto } from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";

/** Productos y puntos de venta para los formularios (listas, reportes, precios del vendedor). */
export function useCatalogo(contenedor: Contenedor) {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [mercados, setMercados] = useState<Mercado[]>([]);

  useEffect(() => {
    let vigente = true;
    void Promise.all([contenedor.catalogo.productos(), contenedor.catalogo.mercados()])
      .then(([p, m]) => {
        if (!vigente) return;
        setProductos(p);
        setMercados(m);
      })
      .catch(() => undefined);
    return () => {
      vigente = false;
    };
  }, [contenedor]);

  return { productos, mercados };
}
