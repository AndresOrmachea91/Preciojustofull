/** Pestañas accesibles (role="tablist"). Las usan las páginas de cada rol. */
export interface Pestana<T extends string> {
  readonly id: T;
  readonly texto: string;
  readonly visible?: boolean;
  /** Cuántas cosas esperan ahí (reportes por revisar, ofertas pausadas). Con 0 no se muestra. */
  readonly pendientes?: number;
}

interface Props<T extends string> {
  readonly pestanas: readonly Pestana<T>[];
  readonly activa: T;
  readonly onCambiar: (id: T) => void;
}

export function Pestanas<T extends string>({ pestanas, activa, onCambiar }: Props<T>) {
  return (
    <div className="pestanas" role="tablist">
      {pestanas
        .filter((p) => p.visible !== false)
        .map((p) => (
          <button
            key={p.id}
            type="button"
            role="tab"
            aria-selected={activa === p.id}
            className="pestanas__pestana"
            onClick={() => onCambiar(p.id)}
          >
            {p.texto}
            {!!p.pendientes && (
              <span className="pestanas__pendientes" aria-hidden="true" title={`${p.pendientes} por revisar`}>
                {p.pendientes}
              </span>
            )}
          </button>
        ))}
    </div>
  );
}
