/**
 * Adaptador HTTP de los mercados por dentro y de las ofertas (C133, C134):
 * /api/v1/mercados/directorio, /mercados/{codigo}/ficha, /ofertas y
 * /admin/ofertas. Traduce snake_case al modelo del dominio.
 */
import type { MercadosRepositorio, OfertasRepositorio, RevisionOfertasRepositorio } from "@/aplicacion/puertos";
import type {
  ArticuloInventario,
  Disponibilidad,
  PuestosDeMercado,
  EntradaDirectorio,
  FichaMercado,
  Oferta,
  OfertaEnRevision,
  PlanDeVerificacion,
  Puesto,
  ResultadoConfirmacion,
  UnidadBase,
} from "@/dominio/modelo";
import type { ClienteHttp } from "@/infraestructura/http/clienteHttp";
import {
  aMercado,
  aPrecio,
  aProducto,
  type MercadoDto,
  type PrecioDto,
  type ProductoDto,
} from "@/infraestructura/http/PreciosApi";

interface PlanDto {
  fecha: string;
  productos: {
    producto: ProductoDto;
    puntaje: number;
    lugares_sin_dato: number;
    lugares_con_dato_viejo: number;
    lugares_al_dia: number;
    cambio_mensual: number | null;
    ancho_relativo: number | null;
    motivos: string[];
  }[];
  lugares: { mercado: MercadoDto; productos_al_dia: number; productos_total: number }[];
  variaciones: {
    producto: ProductoDto;
    cambio_mensual: number;
    mayor_subida: number;
    mayor_bajada: number;
    meses: number;
    nivel: "minorista" | "mayorista";
  }[];
}

export interface PuestoDto {
  id: number | null;
  codigo_mercado: string;
  numero: string;
  nombre: string;
  rubros: string[];
  referencia: string;
  registrado?: boolean;
  foto?: string | null;
  es_local?: boolean;
  celular?: string | null;
}

export interface ArticuloDto {
  codigo_producto: string;
  nombre_producto: string;
  categoria: string;
  monto: number;
  presentacion: string;
  precio_por_unidad_base: number;
  unidad_base: UnidadBase;
  disponibilidad: Disponibilidad;
  actualizado_en: string | null;
  cantidad?: number | null;
  minimo?: number | null;
}

interface PuestosDelMercadoDto {
  mercado: MercadoDto;
  puestos: { puesto: PuestoDto; articulos: ArticuloDto[]; total: number }[];
}

export function aArticulo(d: ArticuloDto): ArticuloInventario {
  return {
    codigoProducto: d.codigo_producto,
    nombreProducto: d.nombre_producto,
    categoria: d.categoria,
    monto: d.monto,
    presentacion: d.presentacion,
    precioPorUnidadBase: d.precio_por_unidad_base,
    unidadBase: d.unidad_base,
    disponibilidad: d.disponibilidad,
    actualizadoEn: d.actualizado_en,
    cantidad: d.cantidad ?? null,
    minimo: d.minimo ?? null,
  };
}

export interface OfertaDto {
  combo?: string | null;
  id: number;
  codigo_producto: string;
  nombre_producto: string;
  unidad_base: UnidadBase;
  codigo_mercado: string;
  nombre_mercado: string;
  numero_puesto: string | null;
  nombre_puesto: string | null;
  monto: number;
  presentacion: string;
  precio_por_unidad_base: number;
  desde: string;
  hasta: string;
  nota: string;
  precio_sistema: number;
  procedencia_sistema: Oferta["procedenciaSistema"];
  ahorro_por_unidad: number;
  ahorro_relativo: number;
  confirmaron: number;
  desmintieron: number;
}

interface FichaDto {
  mercado: MercadoDto;
  padre: MercadoDto | null;
  sectores: MercadoDto[];
  factor_mercado: number;
  precios: {
    codigo_producto: string;
    nombre_producto: string;
    categoria: string;
    precio: PrecioDto;
    ciudad: number | null;
    diferencia: number | null;
  }[];
  puestos: {
    puesto: PuestoDto;
    precios: {
      codigo_producto: string;
      nombre_producto: string;
      monto: number;
      unidad: string;
      precio_por_unidad_base: number;
      unidad_base: UnidadBase;
      fecha: string | null;
      fuente: "vendedor" | "campo";
    }[];
    ofertas: OfertaDto[];
  }[];
  ofertas: OfertaDto[];
  observados: number;
  estimados: number;
  productos_sin_precio: number;
  dato_mas_reciente: string | null;
}

interface EntradaDirectorioDto {
  mercado: MercadoDto;
  puestos: number;
  ofertas: number;
  sectores: number;
}

interface OfertaEnRevisionDto {
  id: number;
  nombre_producto: string;
  nombre_mercado: string;
  numero_puesto: string | null;
  monto: number;
  presentacion: string;
  hasta: string;
  nota: string;
  confirmaron: number;
  desmintieron: number;
}

export function aPuesto(d: PuestoDto): Puesto {
  return {
    id: d.id,
    codigoMercado: d.codigo_mercado,
    numero: d.numero,
    nombre: d.nombre,
    rubros: d.rubros,
    referencia: d.referencia,
    registrado: d.registrado ?? true,
    foto: d.foto ?? null,
    esLocal: d.es_local ?? false,
    celular: d.celular ?? null,
  };
}

export function aOferta(d: OfertaDto): Oferta {
  return {
    id: d.id,
    codigoProducto: d.codigo_producto,
    nombreProducto: d.nombre_producto,
    unidadBase: d.unidad_base,
    codigoMercado: d.codigo_mercado,
    nombreMercado: d.nombre_mercado,
    numeroPuesto: d.numero_puesto,
    nombrePuesto: d.nombre_puesto,
    monto: d.monto,
    presentacion: d.presentacion,
    precioPorUnidadBase: d.precio_por_unidad_base,
    desde: d.desde,
    hasta: d.hasta,
    nota: d.nota,
    combo: d.combo ?? null,
    precioSistema: d.precio_sistema,
    procedenciaSistema: d.procedencia_sistema,
    ahorroPorUnidad: d.ahorro_por_unidad,
    ahorroRelativo: d.ahorro_relativo,
    confirmaron: d.confirmaron,
    desmintieron: d.desmintieron,
  };
}

function aFicha(d: FichaDto): FichaMercado {
  return {
    mercado: aMercado(d.mercado),
    padre: d.padre ? aMercado(d.padre) : null,
    sectores: d.sectores.map(aMercado),
    factorMercado: d.factor_mercado,
    precios: d.precios.map((p) => ({
      codigoProducto: p.codigo_producto,
      nombreProducto: p.nombre_producto,
      categoria: p.categoria,
      precio: aPrecio(p.precio),
      ciudad: p.ciudad,
      diferencia: p.diferencia,
    })),
    puestos: d.puestos.map((x) => ({
      puesto: aPuesto(x.puesto),
      precios: x.precios.map((p) => ({
        codigoProducto: p.codigo_producto,
        nombreProducto: p.nombre_producto,
        monto: p.monto,
        unidad: p.unidad,
        precioPorUnidadBase: p.precio_por_unidad_base,
        unidadBase: p.unidad_base,
        fecha: p.fecha,
        fuente: p.fuente,
      })),
      ofertas: x.ofertas.map(aOferta),
    })),
    ofertas: d.ofertas.map(aOferta),
    observados: d.observados,
    estimados: d.estimados,
    productosSinPrecio: d.productos_sin_precio,
    datoMasReciente: d.dato_mas_reciente,
  };
}

export class MercadosApi implements MercadosRepositorio, OfertasRepositorio, RevisionOfertasRepositorio {
  constructor(private readonly http: ClienteHttp) {}

  async directorio(): Promise<EntradaDirectorio[]> {
    const datos = await this.http.get<EntradaDirectorioDto[]>("/mercados/directorio");
    return datos.map((d) => ({ mercado: aMercado(d.mercado), puestos: d.puestos, ofertas: d.ofertas, sectores: d.sectores }));
  }

  async ficha(codigoMercado: string): Promise<FichaMercado> {
    return aFicha(await this.http.get<FichaDto>(`/mercados/${encodeURIComponent(codigoMercado)}/ficha`));
  }

  async puestos(codigoMercado: string, filtro?: { producto?: string; articulos?: number }): Promise<PuestosDeMercado> {
    const d = await this.http.get<PuestosDelMercadoDto>(`/mercados/${encodeURIComponent(codigoMercado)}/puestos`, {
      producto: filtro?.producto,
      articulos: filtro?.articulos !== undefined ? String(filtro.articulos) : undefined,
    });
    return {
      mercado: aMercado(d.mercado),
      puestos: d.puestos.map((x) => ({ puesto: aPuesto(x.puesto), articulos: x.articulos.map(aArticulo), total: x.total })),
    };
  }

  async verificaciones(): Promise<PlanDeVerificacion> {
    const d = await this.http.get<PlanDto>("/verificaciones");
    return {
      fecha: d.fecha,
      productos: d.productos.map((p) => ({
        producto: aProducto(p.producto),
        puntaje: p.puntaje,
        lugaresSinDato: p.lugares_sin_dato,
        lugaresConDatoViejo: p.lugares_con_dato_viejo,
        lugaresAlDia: p.lugares_al_dia,
        cambioMensual: p.cambio_mensual,
        anchoRelativo: p.ancho_relativo,
        motivos: p.motivos,
      })),
      lugares: d.lugares.map((x) => ({
        mercado: aMercado(x.mercado),
        productosAlDia: x.productos_al_dia,
        productosTotal: x.productos_total,
      })),
      variaciones: d.variaciones.map((v) => ({
        producto: aProducto(v.producto),
        cambioMensual: v.cambio_mensual,
        mayorSubida: v.mayor_subida,
        mayorBajada: v.mayor_bajada,
        meses: v.meses,
        nivel: v.nivel,
      })),
    };
  }

  async vigentes(filtro?: { mercado?: string; producto?: string }): Promise<Oferta[]> {
    const datos = await this.http.get<OfertaDto[]>("/ofertas", { mercado: filtro?.mercado, producto: filtro?.producto });
    return datos.map(aOferta);
  }

  confirmar(idOferta: number, laVioAsi: boolean): Promise<ResultadoConfirmacion> {
    return this.http.post<ResultadoConfirmacion>(`/ofertas/${idOferta}/confirmar`, { la_vio_asi: laVioAsi });
  }

  async ofertasEnRevision(): Promise<OfertaEnRevision[]> {
    const datos = await this.http.get<OfertaEnRevisionDto[]>("/admin/ofertas/revision");
    return datos.map((d) => ({
      id: d.id,
      nombreProducto: d.nombre_producto,
      nombreMercado: d.nombre_mercado,
      numeroPuesto: d.numero_puesto,
      monto: d.monto,
      presentacion: d.presentacion,
      hasta: d.hasta,
      nota: d.nota,
      confirmaron: d.confirmaron,
      desmintieron: d.desmintieron,
    }));
  }

  async reactivarOferta(id: number): Promise<void> {
    await this.http.post(`/admin/ofertas/${id}/reactivar`);
  }

  async retirarOfertaRevisada(id: number): Promise<void> {
    await this.http.post(`/admin/ofertas/${id}/retirar`);
  }
}
