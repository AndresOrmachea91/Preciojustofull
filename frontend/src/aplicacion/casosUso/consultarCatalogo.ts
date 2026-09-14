import type { Mercado, Producto } from "@/dominio/modelo";
import type { CatalogoRepositorio } from "@/aplicacion/puertos";

export class ConsultarCatalogo {
  constructor(private readonly repositorio: CatalogoRepositorio) {}

  productos(): Promise<Producto[]> {
    return this.repositorio.productos();
  }

  mercados(zona?: string): Promise<Mercado[]> {
    return this.repositorio.mercados(zona);
  }
}

