import type { EvaluacionEstimador } from "@/dominio/modelo";
import type { ConfiabilidadRepositorio } from "@/aplicacion/puertos";

/**
 * ¿Qué tan confiable es el estimado? El backtest lo calcula el backend
 * comparando lo estimado con lo que se midió; acá solo se pide. Es público:
 * cualquiera puede ver cuánto se equivoca el sistema.
 */
export class VerConfiabilidad {
  constructor(private readonly repositorio: ConfiabilidadRepositorio) {}

  ejecutar(): Promise<EvaluacionEstimador> {
    return this.repositorio.evaluacion();
  }
}
