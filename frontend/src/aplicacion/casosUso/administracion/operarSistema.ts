import { presentacionBase, type PlanDeVerificacion, type ResultadoImportacion, type SaludSistema } from "@/dominio/modelo";
import type { OperacionRepositorio } from "@/aplicacion/puertos";

/** Las columnas de la planilla de campo, en el orden de la plantilla. Las 5 primeras son obligatorias. */
export const COLUMNAS_CAMPO = [
  "fecha", "mercado", "producto", "monto", "presentacion", "cantidad", "variedad", "observador", "tipo", "puesto",
] as const;

/**
 * Una planilla de ejemplo, separada por ";" como la guarda Excel en español.
 * Se arma acá para descargarla sin pedirla al servidor.
 */
export const PLANTILLA_CAMPO = [
  COLUMNAS_CAMPO.join(";"),
  "2026-10-18;rodriguez;papa_holandesa;8,50;kilo;;;ana;cotizado;14",
  "2026-10-18;rodriguez;tomate;60;arroba;;;ana;pagado;22",
  "",
].join("\n");

/**
 * La planilla de la próxima ronda (A4230): los productos que más conviene
 * medir en los lugares menos cubiertos, con el monto en blanco para llenarlo
 * en el mercado. Se importa con la misma planilla de campo.
 */
export function planillaDeLaRonda(
  plan: PlanDeVerificacion,
  { productos = 10, lugares = 6, fecha }: { productos?: number; lugares?: number; fecha: string },
): string {
  const filas = [COLUMNAS_CAMPO.join(";")];
  const elegidos = plan.productos.filter((p) => p.puntaje > 0).slice(0, productos);
  for (const lugar of plan.lugares.slice(0, lugares)) {
    for (const p of elegidos) {
      const presentacion = presentacionBase(p.producto).codigo;
      filas.push([fecha, lugar.mercado.codigo, p.producto.codigo, "", presentacion, "", "", "", "cotizado", ""].join(";"));
    }
  }
  return `${filas.join("\n")}\n`;
}

const LIMITE_BYTES = 2_000_000;

/**
 * Lo que el administrador opera del sistema: cargar el levantamiento de
 * campo y mirar si todo está sano. Las reglas de cada fila las aplica el
 * backend; acá se frena lo que ya se sabe que no va a pasar.
 */
export class OperarSistema {
  constructor(private readonly repositorio: OperacionRepositorio) {}

  importarCampo(texto: string, archivo: string, soloRevisar: boolean): Promise<ResultadoImportacion> {
    if (!texto.trim()) return Promise.reject(new Error("La planilla está vacía"));
    if (texto.length > LIMITE_BYTES) return Promise.reject(new Error("La planilla es muy grande: divídala en partes"));
    const encabezado = texto.replace(/^﻿/, "").split(/\r?\n/, 1)[0].toLowerCase();
    const faltan = COLUMNAS_CAMPO.slice(0, 5).filter((c) => !encabezado.includes(c));
    if (faltan.length) return Promise.reject(new Error(`A la planilla le faltan las columnas: ${faltan.join(", ")}`));
    return this.repositorio.importarCampo(texto, archivo, soloRevisar);
  }

  salud(): Promise<SaludSistema> {
    return this.repositorio.salud();
  }
}
