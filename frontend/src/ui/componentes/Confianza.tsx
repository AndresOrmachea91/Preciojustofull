import type { NivelConfianza } from "@/dominio/modelo";
import { etiquetaConfianza } from "@/dominio/modelo";

/**
 * El nivel de confianza siempre se muestra. Presentar una estimación como
 * si fuera una medición verificada sería deshonesto con el usuario.
 */
export function Confianza({ nivel }: { nivel: NivelConfianza }) {
  return (
    <span className={`confianza confianza--${nivel}`}>{etiquetaConfianza(nivel)}</span>
  );
}

