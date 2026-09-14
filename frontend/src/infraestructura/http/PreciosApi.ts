/**
 * Adaptador HTTP de los puertos PrecioRepositorio y CatalogoRepositorio.
 *
 * Traduce entre la forma que devuelve la API (nombres en snake_case) y el
 * modelo del dominio. Esa traducción vive acá a propósito: si la API cambia
 * su contrato, solo se toca este archivo.
 */
import type {
  CostoCanasta,
  ItemCanasta,
  Mercado,
  Precio,
  PrecioEnMercado,
  Producto,
} from "@/dominio/modelo";
import type {
  CatalogoRepositorio,
  PrecioRepositorio,
  ReporteRepositorio,
} from "@/aplicacion/puertos";
import { ClienteHttp } from "@/infraestructura/http/clienteHttp";

interface PrecioDto {
  codigo_producto: string;
  codigo_mercado: string;
  periodo: string;
  rango: { minimo: number; maximo: number; centro: number };
  unidad: string;
  confianza: Precio["confianza"];
  observaciones_usadas: number;
  conflictos: string[];
}

interface PrecioEnMercadoDto {
  codigo_mercado: string;
  nombre_mercado: string;
  tipo: Mercado["tipo"];
  zona: string;
  precio: PrecioDto;
}

interface MercadoDto {
  codigo: string;
  nombre: string;
  tipo: Mercado["tipo"];
  zona: string;
  latitud: number | null;
  longitud: number | null;
}

interface ProductoDto {
  codigo: string;
  nombre: string;
  categoria: string;
  es_perecedero: boolean;
}

interface CanastaDto {
  codigo_mercado: string;
  nombre_mercado: string;
  zona: string;
  costo_total: number;
  productos_cubiertos: number;
  productos_pedidos: number;
  cobertura: number;
  faltantes: string[];
}

function aPrecio(d: PrecioDto): Precio {
  return {
    codigoProducto: d.codigo_producto,
    codigoMercado: d.codigo_mercado,
    periodo: d.periodo,
    rango: d.rango,
    unidad: d.unidad,
    confianza: d.confianza,
    observacionesUsadas: d.observaciones_usadas,
    conflictos: d.conflictos ?? [],
  };
}

export class PreciosApi
  implements PrecioRepositorio, CatalogoRepositorio, ReporteRepositorio
{
  constructor(private readonly http: ClienteHttp) {}

  async compararMercados(codigoProducto: string, zona?: string): Promise<PrecioEnMercado[]> {
    const datos = await this.http.get<PrecioEnMercadoDto[]>(
      `/precios/${encodeURIComponent(codigoProducto)}/comparar`,
      { zona },
    );
    return datos.map((d) => ({
      mercado: { codigo: d.codigo_mercado, nombre: d.nombre_mercado, tipo: d.tipo, zona: d.zona },
      precio: aPrecio(d.precio),
    }));
  }

  async precioEnMercado(codigoProducto: string, codigoMercado: string): Promise<Precio> {
    const d = await this.http.get<PrecioDto>(
      `/precios/${encodeURIComponent(codigoProducto)}/mercado/${encodeURIComponent(codigoMercado)}`,
    );
    return aPrecio(d);
  }

  async calcularCanasta(items: readonly ItemCanasta[], zona?: string): Promise<CostoCanasta[]> {
    const datos = await this.http.post<CanastaDto[]>("/canasta/calcular", {
      items: items.map((i) => ({ codigo_producto: i.codigoProducto, cantidad: i.cantidad })),
      zona: zona ?? null,
    });
    return datos.map((d) => ({
      codigoMercado: d.codigo_mercado,
      nombreMercado: d.nombre_mercado,
      zona: d.zona,
      costoTotal: d.costo_total,
      productosCubiertos: d.productos_cubiertos,
      productosPedidos: d.productos_pedidos,
      cobertura: d.cobertura,
      faltantes: d.faltantes ?? [],
    }));
  }

  async productos(): Promise<Producto[]> {
    const datos = await this.http.get<ProductoDto[]>("/productos");
    return datos.map((d) => ({
      codigo: d.codigo,
      nombre: d.nombre,
      categoria: d.categoria,
      esPerecedero: d.es_perecedero,
    }));
  }

  async mercados(zona?: string): Promise<Mercado[]> {
    const datos = await this.http.get<MercadoDto[]>("/mercados", { zona });
    return datos.map((d) => ({
      codigo: d.codigo,
      nombre: d.nombre,
      tipo: d.tipo,
      zona: d.zona,
      latitud: d.latitud ?? undefined,
      longitud: d.longitud ?? undefined,
    }));
  }

  async reportar(entrada: {
    codigoProducto: string;
    codigoMercado: string;
    monto: number;
    unidad: string;
  }): Promise<void> {
    await this.http.post("/reportes", {
      codigo_producto: entrada.codigoProducto,
      codigo_mercado: entrada.codigoMercado,
      monto: entrada.monto,
      unidad: entrada.unidad,
    });
  }
}

