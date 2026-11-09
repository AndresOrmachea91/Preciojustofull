/**
 * Cómo le va al puesto (C145): visitas, quiénes vieron sus ofertas y en
 * cuántos planes de compra apareció.
 *
 * POR AHORA SON DATOS DE EJEMPLO: el conteo real necesita registrar cada
 * visita y llega con el piloto. Se calculan de forma fija a partir del
 * puesto (la misma casera ve siempre los mismos números) y crecen con sus
 * ofertas, para mostrarle la idea: más ofertas y combos, más gente.
 * La pantalla siempre lo dice: "datos de ejemplo".
 */

export interface RendimientoPuesto {
  /** Visitas de los últimos 7 días, de lunes a domingo. */
  readonly porDia: readonly number[];
  readonly visitasSemana: number;
  readonly vieronOfertas: number;
  readonly enPlanes: number;
  readonly abrieronWhatsapp: number;
  /** A cuántas personas llegaría una oferta suelta nueva, y un combo. */
  readonly alcanceOferta: number;
  readonly alcanceCombo: number;
}

export const DIAS_CORTOS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"] as const;

/** Un número fijo a partir de un texto (FNV-1a): la misma semilla da siempre lo mismo. */
function hash(texto: string): number {
  let h = 2166136261;
  for (let i = 0; i < texto.length; i++) {
    h ^= texto.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/** Un generador simple y repetible (mulberry32). */
function azar(semilla: number): () => number {
  let a = semilla;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// La feria: el sábado y el domingo se compra más.
const PESO_DIA = [0.8, 0.85, 0.9, 0.95, 1.1, 1.5, 1.3];

export function rendimientoDeEjemplo(
  semilla: string,
  ofertasActivas: { sueltas: number; combos: number } = { sueltas: 0, combos: 0 },
): RendimientoPuesto {
  const r = azar(hash(semilla));
  // Cada oferta suelta suma un 30 % de gente; cada combo, un 55 %: llega a quien busca cualquiera de sus productos.
  const empuje = 1 + 0.3 * ofertasActivas.sueltas + 0.55 * ofertasActivas.combos;
  const base = 4 + r() * 6; // entre 4 y 10 visitas en un día común
  const porDia = PESO_DIA.map((peso) => Math.round(base * peso * empuje * (0.85 + r() * 0.3)));
  const visitasSemana = porDia.reduce((s, x) => s + x, 0);
  const conOfertas = ofertasActivas.sueltas + ofertasActivas.combos > 0;
  return {
    porDia,
    visitasSemana,
    vieronOfertas: conOfertas ? Math.round(visitasSemana * (0.45 + r() * 0.2)) : 0,
    enPlanes: Math.round(visitasSemana * (0.2 + r() * 0.15)),
    abrieronWhatsapp: Math.round(visitasSemana * (0.05 + r() * 0.05)),
    alcanceOferta: Math.round(visitasSemana * 0.3 + 10),
    alcanceCombo: Math.round(visitasSemana * 0.55 + 18),
  };
}
