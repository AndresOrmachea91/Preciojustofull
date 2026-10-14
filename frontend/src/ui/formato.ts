/** Formatos de presentación compartidos por las pantallas. */

/** "13/10/26 20:15": fecha y hora cortas, en la forma de Bolivia. */
export function fechaCorta(iso: string): string {
  return new Date(iso).toLocaleString("es-BO", { dateStyle: "short", timeStyle: "short" });
}
