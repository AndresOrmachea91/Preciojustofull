import type { MercadosRepositorio } from "@/aplicacion/puertos";
import type { EntradaDirectorio, FichaMercado, PlanDeVerificacion } from "@/dominio/modelo";

/** Entrar a un mercado (C134): el directorio de lugares y la ficha de cada uno. */
export class ExplorarMercados {
  constructor(private readonly repositorio: MercadosRepositorio) {}

  directorio(): Promise<EntradaDirectorio[]> {
    return this.repositorio.directorio();
  }

  ficha(codigoMercado: string): Promise<FichaMercado> {
    if (!codigoMercado) return Promise.reject(new Error("Elija un mercado"));
    return this.repositorio.ficha(codigoMercado);
  }

  /** Dónde el sistema todavía estima: qué medir primero y cuánto se mueve cada precio. */
  verificaciones(): Promise<PlanDeVerificacion> {
    return this.repositorio.verificaciones();
  }
}
