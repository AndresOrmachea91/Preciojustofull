import type { OfertasRepositorio } from "@/aplicacion/puertos";
import type { Oferta, ResultadoConfirmacion } from "@/dominio/modelo";

/**
 * Las ofertas de los caseros (C133). Ver es público; decir si estaba así
 * pide sesión (lo exige la API). El orden lo da el backend: el mayor ahorro
 * real frente al precio del sistema.
 */
export class VerOfertas {
  constructor(private readonly repositorio: OfertasRepositorio) {}

  vigentes(filtro?: { mercado?: string; producto?: string }): Promise<Oferta[]> {
    return this.repositorio.vigentes(filtro);
  }

  confirmar(idOferta: number, laVioAsi: boolean): Promise<ResultadoConfirmacion> {
    return this.repositorio.confirmar(idOferta, laVioAsi);
  }
}
