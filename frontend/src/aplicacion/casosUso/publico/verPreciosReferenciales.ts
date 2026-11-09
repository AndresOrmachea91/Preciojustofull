import type { ReferenciasRepositorio } from "@/aplicacion/puertos";
import { sinTildes, type PrecioReferencial } from "@/dominio/modelo";

export interface GrupoReferencial {
  readonly categoria: string;
  readonly filas: readonly PrecioReferencial[];
}

/**
 * Caso de uso (C144): los precios referenciales de La Paz, todos los
 * productos con el precio de la ciudad al consumidor y por mayor.
 */
export class VerPreciosReferenciales {
  constructor(private readonly repositorio: ReferenciasRepositorio) {}

  listar(): Promise<PrecioReferencial[]> {
    return this.repositorio.referencias();
  }
}

/** Filtra por nombre (sin tildes) y agrupa por categoría, en el orden en que llegan. */
export function agruparReferencias(filas: readonly PrecioReferencial[], texto = ""): GrupoReferencial[] {
  const buscado = sinTildes(texto.trim());
  const grupos = new Map<string, PrecioReferencial[]>();
  for (const f of filas) {
    if (buscado && !sinTildes(f.producto.nombre).includes(buscado)) continue;
    const lista = grupos.get(f.producto.categoria) ?? [];
    lista.push(f);
    grupos.set(f.producto.categoria, lista);
  }
  return [...grupos.entries()].map(([categoria, lista]) => ({ categoria, filas: lista }));
}
