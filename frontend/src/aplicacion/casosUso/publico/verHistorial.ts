import { variacionPorcentual, type HistorialPrecio } from "@/dominio/modelo";
import type { HistorialRepositorio } from "@/aplicacion/puertos";

export interface ResultadoHistorial extends HistorialPrecio {
  /** Cambio del precio al consumidor en el periodo mostrado, en %. */
  readonly variacionMinorista: number | null;
}

/** Caso de uso: cómo cambió el precio de un producto en la ciudad. */
export class VerHistorial {
  constructor(private readonly repositorio: HistorialRepositorio) {}

  async ejecutar(codigoProducto: string, meses = 24): Promise<ResultadoHistorial> {
    const historial = await this.repositorio.historial(codigoProducto, meses);
    return { ...historial, variacionMinorista: variacionPorcentual(historial.puntos, "minorista") };
  }
}
