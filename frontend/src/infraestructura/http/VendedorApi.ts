/** Adaptador HTTP de lo que hace el VENDEDOR: /api/v1/vendedor/precios, /puesto y /ofertas. */
import type {
  DatosDistribuidora,
  DatosPuesto,
  NuevaOferta,
  NuevoCombo,
  NuevoArticulo,
  OfertasVendedorRepositorio,
  PreciosVendedorRepositorio,
} from "@/aplicacion/puertos";
import type {
  ArticuloInventario,
  MiOferta,
  PrecioPublicado,
  Puesto,
  ReporteInventario,
  SugerenciaPrecio,
  UnidadBase,
} from "@/dominio/modelo";

interface ReporteDto {
  renglones: {
    articulo: ArticuloDto;
    sugerencia: {
      tipo: SugerenciaPrecio["tipo"];
      texto: string;
      precio_sugerido: number | null;
      precio_mercado: number | null;
      diferencia: number | null;
    };
    alertas: string[];
  }[];
  productos: number;
  con_cantidad: number;
  valor_total: number;
  agotados: number;
  queda_poco: number;
  para_revisar_precio: number;
  sin_actualizar: number;
  consejos: string[];
}
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
  combo?: string | null;
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
        cantidad: a.cantidad ?? null,
        minimo: a.minimo ?? null,
      }),
    );
  }

  async quitarArticulo(codigoProducto: string): Promise<void> {
    await this.http.delete(`/vendedor/inventario/${encodeURIComponent(codigoProducto)}`);
  }

  async ajustarCantidad(codigoProducto: string, cambio: number): Promise<ArticuloInventario> {
    return aArticulo(
      await this.http.post<ArticuloDto>(`/vendedor/inventario/${encodeURIComponent(codigoProducto)}/ajustar`, { cambio }),
    );
  }

  async reporteInventario(): Promise<ReporteInventario> {
    const d = await this.http.get<ReporteDto>("/vendedor/inventario/reporte");
    return {
      renglones: d.renglones.map((r) => ({
        articulo: aArticulo(r.articulo),
        sugerencia: {
          tipo: r.sugerencia.tipo,
          texto: r.sugerencia.texto,
          precioSugerido: r.sugerencia.precio_sugerido,
          precioMercado: r.sugerencia.precio_mercado,
          diferencia: r.sugerencia.diferencia,
        },
        alertas: r.alertas,
      })),
      productos: d.productos,
      conCantidad: d.con_cantidad,
      valorTotal: d.valor_total,
      agotados: d.agotados,
      quedaPoco: d.queda_poco,
      paraRevisarPrecio: d.para_revisar_precio,
      sinActualizar: d.sin_actualizar,
      consejos: d.consejos,
    };
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
      combo: d.combo ?? null,
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

  async publicarCombo(combo: NuevoCombo): Promise<void> {
    await this.http.post("/vendedor/ofertas/combo", {
      nombre: combo.nombre,
      renglones: combo.renglones.map((r) => ({ codigo_producto: r.codigoProducto, monto: r.monto, presentacion: r.presentacion })),
      horas: combo.horas,
      nota: combo.nota,
    });
  }

  async retirarOferta(id: number): Promise<void> {
    await this.http.post(`/vendedor/ofertas/${id}/retirar`);
  }
}
