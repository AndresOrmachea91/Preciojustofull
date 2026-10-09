/**
 * Adaptador HTTP del catálogo del administrador: /api/v1/admin/mercados y
 * /api/v1/admin/productos. Traduce entre el modelo y los DTO en snake_case.
 */
import type { CatalogoAdminRepositorio, DatosProducto, DatosPuntoVenta } from "@/aplicacion/puertos";
import type { Mercado, Producto } from "@/dominio/modelo";
import type { ClienteHttp } from "@/infraestructura/http/clienteHttp";
import { aMercado, aProducto, type MercadoDto, type ProductoDto } from "@/infraestructura/http/PreciosApi";

function puntoADto(d: DatosPuntoVenta) {
  return {
    nombre: d.nombre,
    tipo: d.tipo,
    zona: d.zona,
    macrodistrito: d.macrodistrito,
    latitud: d.latitud,
    longitud: d.longitud,
    codigo_padre: d.codigoPadre,
  };
}

function productoADto(d: DatosProducto) {
  return {
    nombre: d.nombre,
    categoria: d.categoria,
    unidad_base: d.unidadBase,
    presentaciones: d.presentaciones,
    dias_conservacion: d.diasConservacion,
  };
}

export class CatalogoAdminApi implements CatalogoAdminRepositorio {
  constructor(private readonly http: ClienteHttp) {}

  async crearPuntoVenta(datos: DatosPuntoVenta): Promise<Mercado> {
    return aMercado(await this.http.post<MercadoDto>("/admin/mercados", puntoADto(datos)));
  }

  async actualizarPuntoVenta(codigo: string, datos: DatosPuntoVenta): Promise<Mercado> {
    return aMercado(await this.http.put<MercadoDto>(`/admin/mercados/${encodeURIComponent(codigo)}`, puntoADto(datos)));
  }

  eliminarPuntoVenta(codigo: string): Promise<void> {
    return this.http.delete(`/admin/mercados/${encodeURIComponent(codigo)}`);
  }

  async crearProducto(datos: DatosProducto): Promise<Producto> {
    return aProducto(await this.http.post<ProductoDto>("/admin/productos", productoADto(datos)));
  }

  async actualizarProducto(codigo: string, datos: DatosProducto): Promise<Producto> {
    return aProducto(await this.http.put<ProductoDto>(`/admin/productos/${encodeURIComponent(codigo)}`, productoADto(datos)));
  }

  eliminarProducto(codigo: string): Promise<void> {
    return this.http.delete(`/admin/productos/${encodeURIComponent(codigo)}`);
  }
}
