/** Adaptador HTTP de lo que hace el VENDEDOR: /api/v1/vendedor/precios. */
import type { PreciosVendedorRepositorio } from "@/aplicacion/puertos";
import type { PrecioPublicado, UnidadBase } from "@/dominio/modelo";
import type { ClienteHttp } from "@/infraestructura/http/clienteHttp";

interface PrecioPublicadoDto {
  codigo_producto: string;
  nombre_producto: string;
  monto: number;
  presentacion: string;
  precio_por_unidad_base: number;
  unidad_base: UnidadBase;
  publicado_en: string;
}

export class VendedorApi implements PreciosVendedorRepositorio {
  constructor(private readonly http: ClienteHttp) {}

  async misPrecios(): Promise<PrecioPublicado[]> {
    const datos = await this.http.get<PrecioPublicadoDto[]>("/vendedor/precios");
    return datos.map((d) => ({
      codigoProducto: d.codigo_producto,
      nombreProducto: d.nombre_producto,
      monto: d.monto,
      presentacion: d.presentacion,
      precioPorUnidadBase: d.precio_por_unidad_base,
      unidadBase: d.unidad_base,
      publicadoEn: d.publicado_en,
    }));
  }

  async publicarPrecio(entrada: { codigoProducto: string; monto: number; presentacion: string }): Promise<void> {
    await this.http.post("/vendedor/precios", {
      codigo_producto: entrada.codigoProducto,
      monto: entrada.monto,
      presentacion: entrada.presentacion,
    });
  }
}
