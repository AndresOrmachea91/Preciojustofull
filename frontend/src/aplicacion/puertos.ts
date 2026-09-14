/**
 * Puertos: lo que la aplicación necesita del mundo exterior.
 *
 * Son interfaces. Los adaptadores de infraestructura las implementan —el de
 * HTTP contra la API real, el de memoria con datos fijos— y la aplicación
 * no sabe cuál está usando.
 */
import type {
  CostoCanasta,
  ItemCanasta,
  Mercado,
  Precio,
  PrecioEnMercado,
  Producto,
} from "@/dominio/modelo";

export interface PrecioRepositorio {
  compararMercados(codigoProducto: string, zona?: string): Promise<PrecioEnMercado[]>;
  precioEnMercado(codigoProducto: string, codigoMercado: string): Promise<Precio>;
  calcularCanasta(items: readonly ItemCanasta[], zona?: string): Promise<CostoCanasta[]>;
}

export interface CatalogoRepositorio {
  productos(): Promise<Producto[]>;
  mercados(zona?: string): Promise<Mercado[]>;
}

export interface ReporteRepositorio {
  reportar(entrada: {
    codigoProducto: string;
    codigoMercado: string;
    monto: number;
    unidad: string;
  }): Promise<void>;
}

