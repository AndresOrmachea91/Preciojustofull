/**
 * Caso de uso: cuánto sale la lista de compras en cada punto de venta.
 *
 * Es más robusto que consultar precios sueltos: aunque la estimación tenga
 * error, ese error afecta a todos los mercados en la misma dirección, así
 * que el orden entre ellos se mantiene.
 */
import type { CostoCanasta, ItemCanasta } from "@/dominio/modelo";
import type { PrecioRepositorio } from "@/aplicacion/puertos";

export interface ResultadoCanasta {
  readonly opciones: readonly CostoCanasta[];
  readonly masBarato: CostoCanasta | null;
  readonly ahorro: number;
}

export class CalcularCanasta {
  constructor(private readonly repositorio: PrecioRepositorio) {}

  async ejecutar(items: readonly ItemCanasta[], zona?: string): Promise<ResultadoCanasta> {
    if (items.length === 0) {
      return { opciones: [], masBarato: null, ahorro: 0 };
    }
    const resultado = await this.repositorio.calcularCanasta(items, zona);

    // Solo se comparan mercados que cubren toda la lista: comparar una
    // canasta completa contra una incompleta sería engañoso.
    const completos = resultado.filter((c) => c.cobertura === 1);
    const comparables = completos.length >= 2 ? completos : resultado;
    const costos = comparables.map((c) => c.costoTotal);

    return {
      opciones: resultado,
      masBarato: comparables[0] ?? null,
      ahorro:
        costos.length >= 2
          ? Math.round((Math.max(...costos) - Math.min(...costos)) * 100) / 100
          : 0,
    };
  }
}

