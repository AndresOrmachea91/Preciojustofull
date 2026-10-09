import type { PrecioPublicado } from "@/dominio/modelo";
import type { PreciosVendedorRepositorio } from "@/aplicacion/puertos";

/** El vendedor publica los precios de su puesto y ve lo último que publicó. */
export class MiPuesto {
  constructor(private readonly repositorio: PreciosVendedorRepositorio) {}

  misPrecios(): Promise<PrecioPublicado[]> {
    return this.repositorio.misPrecios();
  }

  publicar(entrada: { codigoProducto: string; monto: number; presentacion: string }): Promise<void> {
    if (!entrada.codigoProducto) return Promise.reject(new Error("Elija el producto"));
    if (!(entrada.monto > 0)) return Promise.reject(new Error("El precio tiene que ser mayor a cero"));
    return this.repositorio.publicarPrecio(entrada);
  }
}
