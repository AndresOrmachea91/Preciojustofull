/**
 * El plan de compra de una lista (C144): dónde comprar cada cosa para gastar
 * lo menos posible CONTANDO EL PASAJE.
 *
 * Ir a dos mercados puede bajar lo que se paga por los productos, pero suma
 * minibuses. El plan prueba comprar todo en un lugar, o repartir la lista en
 * dos o tres, y se queda con el que deja más plata en el bolsillo. Dice qué
 * se gana (en precios) y qué se pierde (en pasajes y vueltas) frente a
 * comprar todo en un solo lugar, para que la persona decida con los números.
 *
 * Regla pura: no pide nada a la red. Recibe los precios por lugar y devuelve
 * el plan.
 */
import { distanciaKm, type Coordenadas, type Mercado, type Procedencia } from "@/dominio/modelo";

/** Lo que pide la lista de un producto, ya en su unidad base (2 arrobas = 23 kg). */
export interface Necesidad {
  readonly codigoProducto: string;
  readonly nombre: string;
  readonly cantidadBase: number;
  readonly unidad: string;
}

/** El precio de un producto en un lugar, por unidad base. */
export interface PrecioEnLugar {
  readonly mercado: Mercado;
  readonly precioUnidad: number;
  readonly procedencia: Procedencia;
}

export interface CompraEnParada {
  readonly necesidad: Necesidad;
  readonly precioUnidad: number;
  readonly costo: number;
  readonly procedencia: Procedencia;
}

export interface Parada {
  readonly mercado: Mercado;
  readonly compras: readonly CompraEnParada[];
  readonly subtotal: number;
}

export interface PlanCompra {
  /** En el orden en que conviene recorrerlas. */
  readonly paradas: readonly Parada[];
  readonly costoProductos: number;
  /** Tramos del recorrido (ida, entre mercados y vuelta) y cuántos se pagan en minibús. */
  readonly tramos: number;
  readonly tramosPagados: number;
  /** De los pagados, cuántos entran o salen de la Zona Sur (pasaje más caro). */
  readonly tramosZonaSur: number;
  readonly costoPasajes: number;
  readonly total: number;
  /** Cuántos precios del plan son estimados: nadie los midió en ese lugar. */
  readonly estimados: number;
  /** Lo que se recorre, si se sabe desde dónde sale la persona. */
  readonly distanciaKm: number | null;
}

export interface ResultadoPlan {
  /** El que deja más plata en el bolsillo, ya contando pasajes. */
  readonly mejor: PlanCompra | null;
  /** Todo en un solo lugar: contra esto se dice qué se gana y qué se pierde. */
  readonly unSoloLugar: PlanCompra | null;
  /** El mejor con 1, 2 y 3 paradas, para comparar. */
  readonly porParadas: readonly PlanCompra[];
  /** Lo que ningún lugar tiene con precio. */
  readonly faltantes: readonly Necesidad[];
  /** Frente a un solo lugar: cuánto baja lo que se paga por los productos. */
  readonly ganaEnPrecios: number;
  /** Frente a un solo lugar: cuánto más se paga de pasaje. */
  readonly pierdeEnPasajes: number;
  /** Lo que queda: ganancia menos pérdida (puede ser 0). */
  readonly neto: number;
}

export interface OpcionesPlan {
  /** Lo que cuesta un tramo en minibús, en Bs. */
  readonly pasaje: number;
  /** Un tramo que entra o sale de la Zona Sur (Centro ↔ Sur es más caro). Sin esto, el mismo pasaje. */
  readonly pasajeZonaSur?: number;
  /** Desde dónde sale la persona; sin esto se cuenta ida y vuelta pagadas. */
  readonly origen: Coordenadas | null;
  readonly maxParadas?: number;
  /** Hasta esta distancia, se camina: no se paga pasaje. */
  readonly aPieKm?: number;
  /** Repartir la lista en más lugares tiene que ahorrar al menos esto, o no vale la vuelta. */
  readonly umbralVuelta?: number;
}

const A_PIE_KM = 0.8;
const UMBRAL_VUELTA = 1;
/** Por producto se miran solo los lugares más baratos: con eso alcanza y la búsqueda es corta. */
const CANDIDATOS_POR_PRODUCTO = 8;

const redondear = (x: number) => Math.round(x * 100) / 100;

function conLugar(m: Mercado): m is Mercado & { latitud: number; longitud: number } {
  return m.latitud !== undefined && m.longitud !== undefined;
}

/** Al sur de Obrajes empieza la Zona Sur (Calacoto, Achumani, Irpavi, Mallasa…). */
const LATITUD_ZONA_SUR = -16.522;

export function enZonaSur(lugar: Coordenadas | Mercado | null): boolean {
  if (!lugar) return false;
  if ("macrodistrito" in lugar && lugar.macrodistrito) {
    const macro = lugar.macrodistrito.toLowerCase();
    if (macro === "sur" || macro.includes("zona sur") || macro.includes("mallasa")) return true;
  }
  return lugar.latitud !== undefined && lugar.latitud < LATITUD_ZONA_SUR;
}

function punto(m: Mercado): Coordenadas | null {
  return conLugar(m) ? { latitud: m.latitud, longitud: m.longitud } : null;
}

/**
 * El recorrido más barato por esas paradas (y, empatando, el más corto):
 * cuántos tramos se pagan, cuántos cruzan a la Zona Sur y cuánto cuesta.
 */
function recorrido(
  mercados: readonly Mercado[],
  origen: Coordenadas | null,
  aPieKm: number,
  pasaje: number,
  pasajeSur: number,
): { orden: Mercado[]; tramos: number; pagados: number; alSur: number; costo: number; km: number | null } {
  type Ruta = { orden: Mercado[]; tramos: number; pagados: number; alSur: number; costo: number; km: number | null };
  let mejor: Ruta | null = null;
  for (const orden of permutaciones(mercados)) {
    let pagados = 0;
    let alSur = 0;
    let costo = 0;
    let km = 0;
    let conocido = true;
    // Sin saber de dónde sale, se supone que vive en la zona de la primera parada.
    const salida: Coordenadas | Mercado = origen ?? orden[0]!;
    const paradas: (Coordenadas | Mercado)[] = [salida, ...orden, salida];
    for (let i = 1; i < paradas.length; i++) {
      const a = paradas[i - 1]!;
      const b = paradas[i]!;
      const pa = "codigo" in a ? punto(a) : a;
      const pb = "codigo" in b ? punto(b) : b;
      const extremo = i === 1 || i === paradas.length - 1;
      let d: number | null = null;
      if (pa && pb && (!extremo || origen)) d = distanciaKm(pa, pb);
      else conocido = false;
      if (d !== null) km += d;
      if (d !== null && d <= aPieKm) continue; // se camina
      pagados++;
      const cruzaAlSur = enZonaSur(a) !== enZonaSur(b);
      if (cruzaAlSur) alSur++;
      costo += cruzaAlSur ? pasajeSur : pasaje;
    }
    const candidato: Ruta = { orden, tramos: orden.length + 1, pagados, alSur, costo, km: conocido ? km : null };
    if (
      !mejor ||
      candidato.costo < mejor.costo - 1e-9 ||
      (Math.abs(candidato.costo - mejor.costo) < 1e-9 && (candidato.km ?? 0) < (mejor.km ?? 0))
    ) {
      mejor = candidato;
    }
  }
  return mejor!;
}

function permutaciones<T>(lista: readonly T[]): T[][] {
  if (lista.length <= 1) return [[...lista]];
  return lista.flatMap((x, i) => permutaciones([...lista.slice(0, i), ...lista.slice(i + 1)]).map((r) => [x, ...r]));
}

function combinaciones<T>(lista: readonly T[], k: number): T[][] {
  if (k === 0) return [[]];
  const salida: T[][] = [];
  lista.forEach((x, i) => {
    for (const resto of combinaciones(lista.slice(i + 1), k - 1)) salida.push([x, ...resto]);
  });
  return salida;
}

/**
 * Arma el plan. `precios` trae, por código de producto, el precio en cada
 * lugar que lo tiene. Solo cuentan los lugares de consumidor final: un
 * precio mayorista es por bulto, no compite.
 */
export function planificarCompra(
  necesidades: readonly Necesidad[],
  precios: ReadonlyMap<string, readonly PrecioEnLugar[]>,
  opciones: OpcionesPlan,
): ResultadoPlan {
  const aPieKm = opciones.aPieKm ?? A_PIE_KM;
  const umbral = opciones.umbralVuelta ?? UMBRAL_VUELTA;
  const maxParadas = Math.max(1, Math.min(3, opciones.maxParadas ?? 3));

  // Precio por lugar y producto, solo de consumidor final.
  const tabla = new Map<string, Map<string, PrecioEnLugar>>();
  const lugares = new Map<string, Mercado>();
  for (const n of necesidades) {
    const porLugar = new Map<string, PrecioEnLugar>();
    for (const p of precios.get(n.codigoProducto) ?? []) {
      if (p.mercado.nivelPrecio !== "minorista" || !(p.precioUnidad > 0)) continue;
      porLugar.set(p.mercado.codigo, p);
      lugares.set(p.mercado.codigo, p.mercado);
    }
    tabla.set(n.codigoProducto, porLugar);
  }
  const faltantes = necesidades.filter((n) => (tabla.get(n.codigoProducto)?.size ?? 0) === 0);
  const pedidas = necesidades.filter((n) => !faltantes.includes(n));
  const vacio: ResultadoPlan = {
    mejor: null, unSoloLugar: null, porParadas: [], faltantes, ganaEnPrecios: 0, pierdeEnPasajes: 0, neto: 0,
  };
  if (pedidas.length === 0) return vacio;

  const armar = (mercados: readonly Mercado[]): PlanCompra | null => {
    const compras = new Map<string, CompraEnParada[]>();
    let costoProductos = 0;
    let estimados = 0;
    for (const n of pedidas) {
      let elegido: PrecioEnLugar | null = null;
      for (const m of mercados) {
        const p = tabla.get(n.codigoProducto)!.get(m.codigo);
        if (p && (!elegido || p.precioUnidad < elegido.precioUnidad)) elegido = p;
      }
      if (!elegido) return null; // este juego de lugares no cubre la lista
      const costo = elegido.precioUnidad * n.cantidadBase;
      costoProductos += costo;
      if (elegido.procedencia === "estimado") estimados++;
      const lista = compras.get(elegido.mercado.codigo) ?? [];
      lista.push({ necesidad: n, precioUnidad: elegido.precioUnidad, costo: redondear(costo), procedencia: elegido.procedencia });
      compras.set(elegido.mercado.codigo, lista);
    }
    // Un lugar donde no se compra nada no es parada.
    const usados = mercados.filter((m) => compras.has(m.codigo));
    const ruta = recorrido(usados, opciones.origen, aPieKm, opciones.pasaje, opciones.pasajeZonaSur ?? opciones.pasaje);
    const costoPasajes = ruta.costo;
    return {
      paradas: ruta.orden.map((m) => {
        const c = compras.get(m.codigo)!;
        return { mercado: m, compras: c, subtotal: redondear(c.reduce((s, x) => s + x.costo, 0)) };
      }),
      costoProductos: redondear(costoProductos),
      tramos: ruta.tramos,
      tramosPagados: ruta.pagados,
      tramosZonaSur: ruta.alSur,
      costoPasajes: redondear(costoPasajes),
      total: redondear(costoProductos + costoPasajes),
      estimados,
      distanciaKm: ruta.km === null ? null : Math.round(ruta.km * 10) / 10,
    };
  };

  // Un solo lugar: se prueban todos los que cubren la lista entera.
  const mejorDe = (planes: (PlanCompra | null)[]) =>
    planes.reduce<PlanCompra | null>((a, b) => (!b ? a : !a || b.total < a.total ? b : a), null);
  const unSoloLugar = mejorDe([...lugares.values()].map((m) => armar([m])));

  // Repartir: entre los más baratos de cada producto (más el mejor lugar único).
  const candidatos = new Map<string, Mercado>();
  for (const n of pedidas) {
    [...tabla.get(n.codigoProducto)!.values()]
      .sort((a, b) => a.precioUnidad - b.precioUnidad)
      .slice(0, CANDIDATOS_POR_PRODUCTO)
      .forEach((p) => candidatos.set(p.mercado.codigo, p.mercado));
  }
  if (unSoloLugar) unSoloLugar.paradas.forEach((p) => candidatos.set(p.mercado.codigo, p.mercado));

  const porParadas: PlanCompra[] = [];
  if (unSoloLugar) porParadas.push(unSoloLugar);
  for (let k = 2; k <= maxParadas; k++) {
    const mejorK = mejorDe(combinaciones([...candidatos.values()], k).map(armar));
    // Si con k lugares el plan termina usando menos, ya está contado antes.
    if (mejorK && mejorK.paradas.length === k) porParadas.push(mejorK);
  }

  // El mejor: el de menor total; pero más paradas tienen que ahorrar de verdad.
  let mejor: PlanCompra | null = null;
  for (const plan of [...porParadas].sort((a, b) => a.paradas.length - b.paradas.length)) {
    if (!mejor || plan.total < mejor.total - umbral) mejor = plan;
  }
  if (!mejor) return { ...vacio, porParadas };

  const base = unSoloLugar ?? mejor;
  const ganaEnPrecios = redondear(Math.max(0, base.costoProductos - mejor.costoProductos));
  const pierdeEnPasajes = redondear(Math.max(0, mejor.costoPasajes - base.costoPasajes));
  return {
    mejor,
    unSoloLugar,
    porParadas,
    faltantes,
    ganaEnPrecios,
    pierdeEnPasajes,
    neto: redondear(Math.max(0, base.total - mejor.total)),
  };
}
