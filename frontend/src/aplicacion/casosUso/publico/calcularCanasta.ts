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

/**
 * Resume una cotización: la más barata y cuánto se ahorra. Lo usan la
 * canasta y las listas de compras del usuario, que cotizan igual.
 */
export function resumirCanasta(resultado: readonly CostoCanasta[]): ResultadoCanasta {
  // Solo se comparan lugares que cubren toda la lista: la diferencia entre
  // una canasta completa y una a la que le falta un producto no es ahorro,
  // es el producto que falta. Con menos de dos completas no se anuncia nada.
  const completos = resultado.filter((c) => c.cobertura === 1);
  const costos = completos.map((c) => c.costoTotal);

  return {
    opciones: resultado,
    masBarato: completos[0] ?? resultado[0] ?? null,
    ahorro:
      costos.length >= 2
        ? Math.round((Math.max(...costos) - Math.min(...costos)) * 100) / 100
        : 0,
  };
}

export class CalcularCanasta {
  constructor(private readonly repositorio: PrecioRepositorio) {}

  async ejecutar(items: readonly ItemCanasta[], zona?: string): Promise<ResultadoCanasta> {
    if (items.length === 0) {
      return { opciones: [], masBarato: null, ahorro: 0 };
    }
    return resumirCanasta(await this.repositorio.calcularCanasta(items, zona));
  }
}
