import type { RevisionOfertasRepositorio } from "@/aplicacion/puertos";
import type { OfertaEnRevision } from "@/dominio/modelo";

/** Las ofertas pausadas por dos desmentidos: reactivar si era verdad, retirar si no. */
export class RevisarOfertas {
  constructor(private readonly repositorio: RevisionOfertasRepositorio) {}

  pendientes(): Promise<OfertaEnRevision[]> {
    return this.repositorio.ofertasEnRevision();
  }

  reactivar(id: number): Promise<void> {
    return this.repositorio.reactivarOferta(id);
  }

  retirar(id: number): Promise<void> {
    return this.repositorio.retirarOfertaRevisada(id);
  }
}
