/**
 * Adaptador HTTP de los puertos PrecioRepositorio y CatalogoRepositorio.
 *
 * Traduce entre la forma que devuelve la API (nombres en snake_case) y el
 * modelo del dominio. Esa traducción vive acá a propósito: si la API cambia
 * su contrato, solo se toca este archivo.
 */
import type {
  CostoCanasta,
  HistorialPrecio,
  ItemCanasta,
  Mercado,
  NivelPrecio,
  Precio,
  PrecioEnMercado,
  Presentacion,
  Producto,
  UnidadBase,
} from "@/dominio/modelo";
import { PRESENTACIONES_POR_UNIDAD } from "@/dominio/modelo";
import type {
  CatalogoRepositorio,
  HistorialRepositorio,
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
  procedencia: Precio["procedencia"];
  observaciones_usadas: number;
  fecha_observacion_mas_reciente: string | null;
  conflictos: string[];
  voces?: Record<string, number>;
  factor_mercado?: number | null;
  antiguedad_dias?: number | null;
  motivos_rango?: string[];
}

interface PrecioEnMercadoDto {
  codigo_mercado: string;
  nombre_mercado: string;
  tipo: Mercado["tipo"];
  zona: string;
  nivel_precio: Mercado["nivelPrecio"];
  precio: PrecioDto;
}

interface MercadoDto {
  codigo: string;
  nombre: string;
  tipo: Mercado["tipo"];
  zona: string;
  macrodistrito: string;
  codigo_padre: string | null;
  nivel_precio: Mercado["nivelPrecio"];
  latitud: number | null;
  longitud: number | null;
}

interface ProductoDto {
  codigo: string;
  nombre: string;
  categoria: string;
  es_perecedero: boolean;
  unidad_base?: UnidadBase;
  dias_conservacion?: number;
  presentaciones?: Presentacion[];
}

/** Traducción de un producto de la API al dominio. La usa también el adaptador del administrador. */
export function aProducto(d: ProductoDto): Producto {
  const unidadBase = d.unidad_base ?? "kg";
  return {
    codigo: d.codigo,
    nombre: d.nombre,
    categoria: d.categoria,
    esPerecedero: d.es_perecedero,
    unidadBase,
    diasConservacion: d.dias_conservacion ?? 30,
    presentaciones: d.presentaciones?.length ? d.presentaciones : PRESENTACIONES_POR_UNIDAD[unidadBase],
  };
}

/** Traducción de una cotización (canasta o lista de compras) al dominio. */
export function aCostoCanasta(d: CanastaDto): CostoCanasta {
  return {
    codigoMercado: d.codigo_mercado,
    nombreMercado: d.nombre_mercado,
    zona: d.zona,
    costoTotal: d.costo_total,
    productosCubiertos: d.productos_cubiertos,
    productosPedidos: d.productos_pedidos,
    cobertura: d.cobertura,
    faltantes: d.faltantes ?? [],
    productosEstimados: d.productos_estimados ?? 0,
    nivelPrecio: d.nivel_precio ?? "minorista",
    costoMinimo: d.costo_minimo ?? 0,
    costoMaximo: d.costo_maximo ?? 0,
  };
}

export type { CanastaDto, ProductoDto, MercadoDto };

interface CanastaDto {
  codigo_mercado: string;
  nombre_mercado: string;
  zona: string;
  costo_total: number;
  productos_cubiertos: number;
  productos_pedidos: number;
  cobertura: number;
  faltantes: string[];
  productos_estimados?: number;
  nivel_precio?: NivelPrecio;
  costo_minimo?: number;
  costo_maximo?: number;
}

function aPrecio(d: PrecioDto): Precio {
  return {
    codigoProducto: d.codigo_producto,
    codigoMercado: d.codigo_mercado,
    periodo: d.periodo,
    rango: d.rango,
    unidad: d.unidad,
    confianza: d.confianza,
    procedencia: d.procedencia,
    observacionesUsadas: d.observaciones_usadas,
    fechaObservacionMasReciente: d.fecha_observacion_mas_reciente ?? null,
    conflictos: d.conflictos ?? [],
    voces: d.voces ?? {},
    factorMercado: d.factor_mercado ?? null,
    antiguedadDias: d.antiguedad_dias ?? null,
    motivosRango: d.motivos_rango ?? [],
  };
}

export function aMercado(d: MercadoDto): Mercado {
  return {
    codigo: d.codigo,
    nombre: d.nombre,
    tipo: d.tipo,
    zona: d.zona,
    macrodistrito: d.macrodistrito,
    codigoPadre: d.codigo_padre ?? null,
    nivelPrecio: d.nivel_precio,
    latitud: d.latitud ?? undefined,
    longitud: d.longitud ?? undefined,
  };
}

interface HistorialDto {
  unidad: UnidadBase;
  puntos: { periodo: string; nivel: NivelPrecio; precio: number; observaciones: number }[];
}

export class PreciosApi
  implements PrecioRepositorio, CatalogoRepositorio, ReporteRepositorio, HistorialRepositorio
{
  constructor(private readonly http: ClienteHttp) {}

  async compararMercados(codigoProducto: string, zona?: string): Promise<PrecioEnMercado[]> {
    const datos = await this.http.get<PrecioEnMercadoDto[]>(
      `/precios/${encodeURIComponent(codigoProducto)}/comparar`,
      { zona },
    );
    return datos.map((d) => ({
      mercado: {
        codigo: d.codigo_mercado,
        nombre: d.nombre_mercado,
        tipo: d.tipo,
        zona: d.zona,
        macrodistrito: d.zona,
        codigoPadre: null,
        nivelPrecio: d.nivel_precio,
      },
      precio: aPrecio(d.precio),
    }));
  }

  async historial(codigoProducto: string, meses = 24): Promise<HistorialPrecio> {
    const d = await this.http.get<HistorialDto>(`/precios/${encodeURIComponent(codigoProducto)}/historial`, {
      meses: String(meses),
    });
    return { unidad: d.unidad, puntos: d.puntos };
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
    return datos.map(aCostoCanasta);
  }

  async productos(): Promise<Producto[]> {
    const datos = await this.http.get<ProductoDto[]>("/productos");
    return datos.map(aProducto);
  }

  async mercados(zona?: string): Promise<Mercado[]> {
    const datos = await this.http.get<MercadoDto[]>("/mercados", { zona });
    return datos.map(aMercado);
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

