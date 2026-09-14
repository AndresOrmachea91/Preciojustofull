/**
 * Regla de negocio del frontend: en qué orden conviene mostrar los mercados.
 *
 * No es solo "el más barato primero". Un mercado que sale Bs 2 menos pero
 * queda a cuarenta minutos no conviene, y un precio con confianza baja no
 * debería competir de igual a igual con uno verificado en campo.
 *
 * Es una función pura: se prueba sin navegador, sin red y sin React.
 */
import type { NivelConfianza, PrecioEnMercado } from "@/dominio/modelo";

export interface OpcionesOrden {
  /** Penalización en bolivianos por cada kilómetro de distancia. */
  readonly costoPorKm?: number;
  /** Distancias conocidas por código de mercado, en kilómetros. */
  readonly distancias?: Readonly<Record<string, number>>;
}

const PENALIZACION_CONFIANZA: Record<NivelConfianza, number> = {
  verificado: 1.0,
  alto: 1.02,
  medio: 1.06,
  bajo: 1.15,
};

export function puntajeConveniencia(
  item: PrecioEnMercado,
  opciones: OpcionesOrden = {},
): number {
  const { costoPorKm = 1.5, distancias = {} } = opciones;
  const distancia = distancias[item.mercado.codigo] ?? 0;
  const base = item.precio.rango.centro * PENALIZACION_CONFIANZA[item.precio.confianza];
  return base + distancia * costoPorKm;
}

export function ordenarPorConveniencia(
  items: readonly PrecioEnMercado[],
  opciones: OpcionesOrden = {},
): PrecioEnMercado[] {
  return [...items].sort(
    (a, b) => puntajeConveniencia(a, opciones) - puntajeConveniencia(b, opciones),
  );
}

/** Cuánto se ahorra eligiendo el primero de la lista en vez del último. */
export function ahorroPosible(items: readonly PrecioEnMercado[]): number {
  if (items.length < 2) return 0;
  const centros = items.map((i) => i.precio.rango.centro);
  return Math.round((Math.max(...centros) - Math.min(...centros)) * 100) / 100;
}

