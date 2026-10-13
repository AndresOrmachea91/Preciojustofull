import { useId, useMemo, useRef, useState, type KeyboardEvent } from "react";

import { CATEGORIAS, type Producto } from "@/dominio/modelo";
import { Icono } from "@/ui/componentes/Iconos";

interface Props {
  readonly productos: readonly Producto[];
  /** Código del producto elegido, o null/"" si no hay. */
  readonly valor: string | null;
  readonly onElegir: (codigo: string) => void;
  /** Nombre visible del campo; también es su nombre accesible. */
  readonly etiqueta: string;
  readonly ayuda?: string;
  /** Para "agregar a la lista": después de elegir, la caja vuelve a quedar vacía. */
  readonly limpiarAlElegir?: boolean;
}

/** Sin mayúsculas ni tildes: "PAPA" y "papá" encuentran "Papa holandesa". */
function normalizar(texto: string): string {
  return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

const NOMBRE_CATEGORIA = new Map(CATEGORIAS.map((c) => [c.codigo, c.nombre]));

/**
 * Elegir un producto escribiendo: una caja de búsqueda con la lista filtrada
 * debajo, agrupada por categoría. Sigue el patrón "combobox" de ARIA: se usa
 * con el teclado (flechas, Enter, Escape) y con lector de pantalla.
 */
export function SelectorProducto({ productos, valor, onElegir, etiqueta, ayuda, limpiarAlElegir }: Props) {
  const id = useId();
  const [abierta, setAbierta] = useState(false);
  // null: no se está escribiendo, la caja muestra el producto elegido.
  const [consulta, setConsulta] = useState<string | null>(null);
  const [activo, setActivo] = useState(0);
  const lista = useRef<HTMLUListElement>(null);

  const elegido = productos.find((p) => p.codigo === valor) ?? null;
  const filtrados = useMemo(() => {
    const buscado = normalizar(consulta ?? "");
    return productos
      .filter((p) => !buscado || normalizar(`${p.nombre} ${NOMBRE_CATEGORIA.get(p.categoria) ?? ""}`).includes(buscado))
      .sort(
        (a, b) =>
          (NOMBRE_CATEGORIA.get(a.categoria) ?? "").localeCompare(NOMBRE_CATEGORIA.get(b.categoria) ?? "") ||
          a.nombre.localeCompare(b.nombre),
      );
  }, [productos, consulta]);

  function elegir(producto: Producto) {
    onElegir(producto.codigo);
    setConsulta(limpiarAlElegir ? "" : null);
    setAbierta(false);
  }

  function mover(paso: number) {
    if (filtrados.length === 0) return;
    const siguiente = (activo + paso + filtrados.length) % filtrados.length;
    setActivo(siguiente);
    setAbierta(true);
    lista.current?.querySelector(`[data-indice="${siguiente}"]`)?.scrollIntoView?.({ block: "nearest" });
  }

  function alTeclear(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      mover(1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      mover(-1);
    } else if (e.key === "Enter" && abierta && filtrados[activo]) {
      // Enter elige; no envía el formulario que contiene la caja.
      e.preventDefault();
      elegir(filtrados[activo]);
    } else if (e.key === "Escape") {
      setAbierta(false);
      setConsulta(limpiarAlElegir ? "" : null);
    }
  }

  const texto = consulta ?? (limpiarAlElegir ? "" : (elegido?.nombre ?? ""));
  let categoriaAnterior = "";

  return (
    <div className="buscador">
      <label className="buscador__etiqueta" htmlFor={`${id}-caja`}>
        {etiqueta}
      </label>
      <div className="buscador__campo">
        <div className="buscador__caja">
          <Icono nombre="buscar" tamano={18} />
          <input
            id={`${id}-caja`}
            role="combobox"
            aria-expanded={abierta}
            aria-controls={`${id}-lista`}
            aria-autocomplete="list"
            aria-activedescendant={abierta && filtrados[activo] ? `${id}-${filtrados[activo].codigo}` : undefined}
            autoComplete="off"
            placeholder="Buscar producto…"
            value={texto}
            onChange={(e) => {
              setConsulta(e.target.value);
              setActivo(0);
              setAbierta(true);
            }}
            onFocus={(e) => {
              e.target.select();
              setAbierta(true);
            }}
            onBlur={() => {
              setAbierta(false);
              setConsulta(limpiarAlElegir ? "" : null);
            }}
            onKeyDown={alTeclear}
          />
        </div>

        {abierta && (
          <ul ref={lista} id={`${id}-lista`} role="listbox" aria-label={etiqueta} className="buscador__lista">
            {filtrados.length === 0 && <li className="buscador__vacio">Ningún producto coincide.</li>}
            {filtrados.map((p, i) => {
              const categoria = NOMBRE_CATEGORIA.get(p.categoria) ?? "Otro";
              const titulo = categoria !== categoriaAnterior ? categoria : null;
              categoriaAnterior = categoria;
              return [
                titulo && (
                  <li key={`g-${titulo}`} role="presentation" className="buscador__grupo">
                    {titulo}
                  </li>
                ),
                <li
                  key={p.codigo}
                  id={`${id}-${p.codigo}`}
                  role="option"
                  data-indice={i}
                  aria-selected={p.codigo === valor}
                  className={`buscador__opcion${i === activo ? " buscador__opcion--activa" : ""}`}
                  // mousedown y no click: el click llega después del blur que cierra la lista.
                  onMouseDown={(e) => {
                    e.preventDefault();
                    elegir(p);
                  }}
                  onMouseEnter={() => setActivo(i)}
                >
                  <span>{p.nombre}</span>
                  {p.codigo === valor && <Icono nombre="elegido" tamano={16} />}
                </li>,
              ];
            })}
          </ul>
        )}
      </div>
      {ayuda && <small className="tenue">{ayuda}</small>}
    </div>
  );
}
