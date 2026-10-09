/**
 * Caso de uso: el mapa de puntos de venta con el precio de un producto.
 *
 * Junta el catálogo (dónde están los 88 puntos) con la comparación (qué
 * precio tiene cada uno, con su procedencia). El componente del mapa
 * recibe esto ya resuelto: Leaflet dibuja, no decide.
 */
import type { MarcadorMapa, NivelPrecio, PrecioEnMercado } from "@/dominio/modelo";
import type { CatalogoRepositorio, PrecioRepositorio } from "@/aplicacion/puertos";

export interface ResumenMapa {
  readonly observados: number;
  readonly estimados: number;
  readonly sinDatos: number;
  readonly porNivel: Readonly<Record<NivelPrecio, number>>;
}

export interface ResultadoMapa {
  readonly marcadores: readonly MarcadorMapa[];
  readonly resumen: ResumenMapa;
}

export class VerMapa {
  constructor(
    private readonly catalogo: CatalogoRepositorio,
    private readonly precios: PrecioRepositorio,
  ) {}

  async ejecutar(codigoProducto: string): Promise<ResultadoMapa> {
    const [mercados, comparacion] = await Promise.all([
      this.catalogo.mercados(),
      this.precios.compararMercados(codigoProducto),
    ]);
    const precioPor = new Map(comparacion.map((p: PrecioEnMercado) => [p.mercado.codigo, p.precio]));

    const marcadores: MarcadorMapa[] = mercados
      .filter((m) => m.latitud !== undefined && m.longitud !== undefined)
      .map((mercado) => ({ mercado, precio: precioPor.get(mercado.codigo) ?? null }));

    const resumen: ResumenMapa = {
      observados: marcadores.filter((m) => m.precio?.procedencia === "observado").length,
      estimados: marcadores.filter((m) => m.precio?.procedencia === "estimado").length,
      sinDatos: marcadores.filter((m) => m.precio === null).length,
      porNivel: {
        minorista: marcadores.filter((m) => m.precio && m.mercado.nivelPrecio === "minorista").length,
        mayorista: marcadores.filter((m) => m.precio && m.mercado.nivelPrecio === "mayorista").length,
      },
    };
    return { marcadores, resumen };
  }
}
