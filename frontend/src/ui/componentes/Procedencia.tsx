import type { Procedencia as TipoProcedencia } from "@/dominio/modelo";
import { etiquetaProcedencia } from "@/dominio/modelo";

/**
 * Todo precio dice de dónde sale, de un vistazo y no en letra chica.
 * Un estimado se ve distinto de un observado antes de leer el número.
 */
export function Procedencia({ valor }: { valor: TipoProcedencia }) {
  return (
    <span className={`procedencia procedencia--${valor}`} data-procedencia={valor}>
      {valor === "observado" ? "●" : "◌"} {etiquetaProcedencia(valor)}
    </span>
  );
}
