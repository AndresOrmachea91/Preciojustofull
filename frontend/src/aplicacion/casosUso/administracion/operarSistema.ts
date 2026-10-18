import type { ResultadoImportacion, SaludSistema } from "@/dominio/modelo";
import type { OperacionRepositorio } from "@/aplicacion/puertos";

/** Las columnas de la planilla de campo, en el orden de la plantilla. Las 5 primeras son obligatorias. */
export const COLUMNAS_CAMPO = [
  "fecha", "mercado", "producto", "monto", "presentacion", "cantidad", "variedad", "observador", "tipo",
] as const;

/**
 * Una planilla de ejemplo, separada por ";" como la guarda Excel en español.
 * Se arma acá para descargarla sin pedirla al servidor.
 */
export const PLANTILLA_CAMPO = [
  COLUMNAS_CAMPO.join(";"),
  "2026-10-18;rodriguez;papa_holandesa;8,50;kilo;;;ana;cotizado",
  "2026-10-18;rodriguez;tomate;60;arroba;;;ana;pagado",
  "",
].join("\n");

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
