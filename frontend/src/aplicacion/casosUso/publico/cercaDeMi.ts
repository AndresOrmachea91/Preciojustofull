import { ubicacionValida, type Coordenadas } from "@/dominio/modelo";
import type { UbicacionRepositorio } from "@/aplicacion/puertos";

/**
 * Caso de uso: dónde está la persona, para mostrarle lo más cercano.
 * Se pide UNA vez: ordenar por distancia (masCercanos, en el dominio) no
 * necesita volver a preguntar al GPS cuando se cambia de producto.
 */
export class CercaDeMi {
  constructor(private readonly ubicacion: UbicacionRepositorio) {}

  async ubicar(): Promise<Coordenadas> {
    const aqui = await this.ubicacion.actual();
    if (!ubicacionValida(aqui.latitud, aqui.longitud)) {
      throw new Error("Su ubicación está fuera de La Paz y El Alto: no hay mercados cercanos que mostrar.");
    }
    return aqui;
  }
}
