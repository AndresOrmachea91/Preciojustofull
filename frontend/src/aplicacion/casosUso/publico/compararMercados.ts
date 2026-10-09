/**
 * Caso de uso: comparar un producto entre puntos de venta.
 *
 * Depende del PUERTO, no del adaptador. Por eso se puede ejecutar con el
 * backend apagado enchufándole el repositorio en memoria.
 */
import type { PrecioEnMercado } from "@/dominio/modelo";
import { ahorroPosible, ordenarPorConveniencia } from "@/dominio/servicio/ordenarPorConveniencia";
import type { OpcionesOrden } from "@/dominio/servicio/ordenarPorConveniencia";
import type { PrecioRepositorio } from "@/aplicacion/puertos";

export interface ResultadoComparativa {
  readonly opciones: readonly PrecioEnMercado[];
  readonly masConveniente: PrecioEnMercado | null;
  readonly ahorro: number;
}

export class CompararMercados {
  constructor(private readonly repositorio: PrecioRepositorio) {}

  async ejecutar(
    codigoProducto: string,
    zona?: string,
    opciones: OpcionesOrden = {},
  ): Promise<ResultadoComparativa> {
    const crudo = await this.repositorio.compararMercados(codigoProducto, zona);
    const ordenado = ordenarPorConveniencia(crudo, opciones);
    return {
      opciones: ordenado,
      masConveniente: ordenado[0] ?? null,
      ahorro: ahorroPosible(ordenado),
    };
  }
}

