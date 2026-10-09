/** Mensajes de error y de confirmación, iguales en todas las pantallas. */
export function MensajeError({ texto }: { texto: string | null }) {
  if (!texto) return null;
  return (
    <p className="estado estado--error" role="alert">
      {texto}
    </p>
  );
}

export function MensajeAviso({ texto }: { texto: string | null }) {
  if (!texto) return null;
  return (
    <p className="aviso" role="status">
      {texto}
    </p>
  );
}

/** El texto de un error para mostrarlo a la persona. */
export function textoDeError(e: unknown): string {
  return e instanceof Error ? e.message : "No se pudo completar la operación";
}
