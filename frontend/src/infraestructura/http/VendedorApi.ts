/** Adaptador HTTP de lo que hace el VENDEDOR: /api/v1/vendedor/precios, /puesto y /ofertas. */
import type {
  DatosDistribuidora,
  DatosPuesto,
  NuevaOferta,
  NuevoArticulo,
  OfertasVendedorRepositorio,
  PreciosVendedorRepositorio,
} from "@/aplicacion/puertos";
import type { ArticuloInventario, MiOferta, PrecioPublicado, Puesto, UnidadBase } from "@/dominio/modelo";
import type { ClienteHttp } from "@/infraestructura/http/clienteHttp";
import { aArticulo, aPuesto, type ArticuloDto, type PuestoDto } from "@/infraestructura/http/MercadosApi";

interface PrecioPublicadoDto {
  codigo_producto: string;
  nombre_producto: string;
  monto: number;
  presentacion: string;
  precio_por_unidad_base: number;
  unidad_base: UnidadBase;
  publicado_en: string;
}

interface MiOfertaDto {
  id: number;
  codigo_producto: string;
  nombre_producto: string;
  monto: number;
  presentacion: string;
  precio_por_unidad_base: number;
  desde: string;
  hasta: string;
  nota: string;
  estado: MiOferta["estado"];
  confirmaron: number;
  desmintieron: number;
}

export class VendedorApi implements PreciosVendedorRepositorio, OfertasVendedorRepositorio {
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

  async miPuesto(): Promise<Puesto | null> {
    const dato = await this.http.get<PuestoDto | null>("/vendedor/puesto");
    return dato ? aPuesto(dato) : null;
  }

  async guardarMiPuesto(datos: DatosPuesto): Promise<Puesto> {
    const { codigoMercado, ...resto } = datos;
    return aPuesto(await this.http.put<PuestoDto>("/vendedor/puesto", { ...resto, codigo_mercado: codigoMercado }));
  }

  async registrarDistribuidora(datos: DatosDistribuidora): Promise<Puesto> {
    return aPuesto(await this.http.put<PuestoDto>("/vendedor/distribuidora", datos));
  }

  async ponerFoto(imagen: string): Promise<Puesto> {
    return aPuesto(await this.http.put<PuestoDto>("/vendedor/puesto/foto", { imagen }));
  }

  async inventario(): Promise<ArticuloInventario[]> {
    return (await this.http.get<ArticuloDto[]>("/vendedor/inventario")).map(aArticulo);
  }

  async guardarArticulo(a: NuevoArticulo): Promise<ArticuloInventario> {
    return aArticulo(
      await this.http.put<ArticuloDto>("/vendedor/inventario", {
        codigo_producto: a.codigoProducto,
        monto: a.monto,
        presentacion: a.presentacion,
        disponibilidad: a.disponibilidad,
      }),
    );
  }

  async quitarArticulo(codigoProducto: string): Promise<void> {
    await this.http.delete(`/vendedor/inventario/${encodeURIComponent(codigoProducto)}`);
  }

  async misOfertas(): Promise<MiOferta[]> {
    const datos = await this.http.get<MiOfertaDto[]>("/vendedor/ofertas");
    return datos.map((d) => ({
      id: d.id,
      codigoProducto: d.codigo_producto,
      nombreProducto: d.nombre_producto,
      monto: d.monto,
      presentacion: d.presentacion,
      precioPorUnidadBase: d.precio_por_unidad_base,
      desde: d.desde,
      hasta: d.hasta,
      nota: d.nota,
      estado: d.estado,
      confirmaron: d.confirmaron,
      desmintieron: d.desmintieron,
    }));
  }

  async publicarOferta(oferta: NuevaOferta): Promise<void> {
    await this.http.post("/vendedor/ofertas", {
      codigo_producto: oferta.codigoProducto,
      monto: oferta.monto,
      presentacion: oferta.presentacion,
      horas: oferta.horas,
      nota: oferta.nota,
    });
  }

  async retirarOferta(id: number): Promise<void> {
    await this.http.post(`/vendedor/ofertas/${id}/retirar`);
  }
}
