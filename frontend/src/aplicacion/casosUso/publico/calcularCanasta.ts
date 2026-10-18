/**
 * Caso de uso: cuánto sale la lista de compras en cada punto de venta.
 *
 * Es más robusto que consultar precios sueltos: aunque la estimación tenga
 * error, ese error afecta a todos los mercados en la misma dirección, así
 * que el orden entre ellos se mantiene.
 */
import type { CostoCanasta, ItemCanasta } from "@/dominio/modelo";
import { empatan, rangoDeCosto } from "@/dominio/modelo";
import type { PrecioRepositorio } from "@/aplicacion/puertos";

export interface ResultadoCanasta {
  readonly opciones: readonly CostoCanasta[];
  readonly masBarato: CostoCanasta | null;
  /** El lugar completo más caro: contra él se dice cuánto se ahorra. */
  readonly masCaro: CostoCanasta | null;
  readonly ahorro: number;
  /** Lugares completos que no se distinguen del más barato con el margen de error. */
  readonly empatanConElMejor: readonly CostoCanasta[];
}

/**
 * Resume una cotización: la más barata y cuánto se ahorra. Lo usan la
 * canasta y las listas de compras del usuario, que cotizan igual.
 */
export function resumirCanasta(resultado: readonly CostoCanasta[]): ResultadoCanasta {
  // Solo se comparan lugares que cubren toda la lista: la diferencia entre
  // una canasta completa y una a la que le falta un producto no es ahorro,
  // es el producto que falta. Con menos de dos completas no se anuncia nada.
  const completos = [...resultado.filter((c) => c.cobertura === 1)].sort((a, b) => a.costoTotal - b.costoTotal);
  const mejor = completos[0] ?? null;
  const masCaro = completos.length >= 2 ? completos[completos.length - 1] : null;

  return {
    opciones: resultado,
    masBarato: mejor ?? resultado[0] ?? null,
    masCaro,
    ahorro: mejor && masCaro ? Math.round((masCaro.costoTotal - mejor.costoTotal) * 100) / 100 : 0,
    // Los que no se pueden separar del mejor: la diferencia es menor que el
    // margen de error. Se dicen juntos, no se elige un ganador a dedo.
    empatanConElMejor: mejor
      ? completos.slice(1).filter((c) => empatan(rangoDeCosto(mejor), rangoDeCosto(c)))
      : [],
  };
}

export class CalcularCanasta {
  constructor(private readonly repositorio: PrecioRepositorio) {}

  async ejecutar(items: readonly ItemCanasta[], zona?: string): Promise<ResultadoCanasta> {
    if (items.length === 0) {
      return { opciones: [], masBarato: null, masCaro: null, ahorro: 0, empatanConElMejor: [] };
    }
    return resumirCanasta(await this.repositorio.calcularCanasta(items, zona));
  }
}
