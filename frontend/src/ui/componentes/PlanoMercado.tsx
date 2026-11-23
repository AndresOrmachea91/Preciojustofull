import { useEffect, useMemo, useRef } from "react";

import {
  bs,
  fechaDiaMes,
  iconoProducto,
  nivelExistencia,
  nombreCategoria,
  nombreDelPuesto,
  textoCantidad,
  textoDisponibilidad,
  type ArticuloInventario,
  type Oferta,
  type PrecioDelPuesto,
  type Puesto,
  type PuestoConInventario,
  type Usuario,
} from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { ContactoPuesto } from "@/ui/componentes/ContactoPuesto";
import { TarjetaOferta } from "@/ui/componentes/TarjetaOferta";

/** El color del toldo según lo que vende el puesto: así se ubica el pasillo de un vistazo. */
const COLOR_RUBRO: Record<string, string> = {
  hortaliza: "#2f9e5b", tuberculo: "#9a6b3c", fruta: "#ef8a1a", carne: "#d64545", pescado: "#2f7fc1",
  lacteo: "#5aa9d6", abarrote: "#c99a1e", otro: "#7b8794",
};
const NOMBRE_PASILLO: Record<string, string> = {
  hortaliza: "Pasillo de verduras", tuberculo: "Pasillo de papas", fruta: "Pasillo de frutas", carne: "Pasillo de carnes",
  pescado: "Pasillo de pescados", lacteo: "Pasillo de lácteos", abarrote: "Pasillo de abarrotes", otro: "Otros puestos",
};

export function colorRubro(rubro: string | undefined): string {
  return COLOR_RUBRO[rubro ?? "otro"] ?? COLOR_RUBRO.otro!;
}

/** De qué pasillo es: el rubro del puesto o, si no dijo, el de la mayoría de sus productos. */
function rubroPrincipal(puesto: Puesto, articulos: readonly ArticuloInventario[]): string {
  if (puesto.rubros[0]) return puesto.rubros[0];
  const cuenta = new Map<string, number>();
  for (const a of articulos) cuenta.set(a.categoria, (cuenta.get(a.categoria) ?? 0) + 1);
  return [...cuenta.entries()].sort((x, y) => y[1] - x[1])[0]?.[0] ?? "otro";
}

export interface PuestoDelPlano extends PuestoConInventario {
  readonly ofertas: readonly Oferta[];
  readonly precios?: readonly PrecioDelPuesto[];
}

/** Cuántos productos le quedan, cuántos se están acabando y si tiene oferta. */
function resumen(p: PuestoDelPlano) {
  const hay = p.articulos.filter((a) => a.disponibilidad !== "agotado").length;
  const poco = p.articulos.filter((a) => a.disponibilidad === "poco").length;
  const agotados = p.articulos.filter((a) => a.disponibilidad === "agotado").length;
  return { hay, poco, agotados, total: Math.max(p.total, p.articulos.length) };
}

/**
 * El mercado como se ve al caminarlo (C148): pasillos por rubro y, en cada
 * uno, sus puestos con el toldo del color de lo que venden. Cada puesto dice
 * cuántos productos tiene, cuáles se acaban y si tiene oferta.
 */
export function PlanoMercado({
  puestos,
  seleccionado,
  alElegir,
  compacto = false,
}: {
  puestos: readonly PuestoDelPlano[];
  seleccionado: string | null;
  alElegir: (numero: string) => void;
  compacto?: boolean;
}) {
  const pasillos = useMemo(() => {
    const grupos = new Map<string, PuestoDelPlano[]>();
    for (const p of puestos) {
      const r = rubroPrincipal(p.puesto, p.articulos);
      grupos.set(r, [...(grupos.get(r) ?? []), p]);
    }
    const orden = Object.keys(NOMBRE_PASILLO);
    return [...grupos.entries()].sort((a, b) => orden.indexOf(a[0]) - orden.indexOf(b[0]));
  }, [puestos]);

  return (
    <div className={`plano${compacto ? " plano--compacto" : ""}`} aria-label="Puestos del mercado">
      {pasillos.map(([rubro, lista]) => (
        <section key={rubro} className="pasillo" style={{ ["--toldo" as string]: colorRubro(rubro) }}>
          {!compacto && (
            <h3 className="pasillo__nombre">
              <span aria-hidden="true">{iconoProducto("", rubro)}</span> {NOMBRE_PASILLO[rubro] ?? nombreCategoria(rubro)}
              <span className="tenue"> · {lista.length} {lista.length === 1 ? "puesto" : "puestos"}</span>
            </h3>
          )}
          <ul className="pasillo__puestos">
            {lista.map((p) => (
              <li key={p.puesto.numero}>
                <Toldo
                  item={p}
                  rubro={rubro}
                  activo={seleccionado === p.puesto.numero}
                  compacto={compacto}
                  alElegir={() => alElegir(p.puesto.numero)}
                />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

function Toldo({
  item,
  rubro,
  activo,
  compacto,
  alElegir,
}: {
  item: PuestoDelPlano;
  rubro: string;
  activo: boolean;
  compacto: boolean;
  alElegir: () => void;
}) {
  const { puesto, articulos, ofertas } = item;
  const r = resumen(item);
  const estrella = articulos[0] ? iconoProducto(articulos[0].codigoProducto, articulos[0].categoria) : iconoProducto("", rubro);
  const titulo = nombreDelPuesto(puesto);
  return (
    <button
      type="button"
      className={`toldo${activo ? " toldo--activo" : ""}${r.total > 0 && r.hay === 0 ? " toldo--cerrado" : ""}`}
      style={{ ["--toldo" as string]: colorRubro(rubro) }}
      aria-pressed={activo}
      aria-label={`${titulo}: ${r.hay} de ${r.total} productos disponibles${ofertas.length ? ", con oferta" : ""}`}
      onClick={alElegir}
    >
      <span className="toldo__tela" aria-hidden="true" />
      {ofertas.length > 0 && (
        <span className="toldo__oferta" aria-hidden="true">
          ★ oferta
        </span>
      )}
      <span className="toldo__frente">
        {puesto.foto ? (
          <img className="toldo__foto" src={puesto.foto} alt="" loading="lazy" />
        ) : (
          <span className="toldo__dibujo" aria-hidden="true">
            {estrella}
          </span>
        )}
        <span className="toldo__numero">{puesto.esLocal ? "Local" : `N.º ${puesto.numero}`}</span>
      </span>
      {!compacto && (
        <span className="toldo__texto">
          <strong className="toldo__nombre">{puesto.nombre || titulo}</strong>
          <span className="toldo__estado">
            {r.total === 0
              ? "Sin productos cargados"
              : `${r.hay} de ${r.total} ${r.total === 1 ? "producto" : "productos"}`}
            {r.poco > 0 && <span className="toldo__poco"> · {r.poco} {r.poco === 1 ? "se acaba" : "se acaban"}</span>}
          </span>
          {articulos.length > 0 && (
            <span className="toldo__iconos" aria-hidden="true">
              {articulos.slice(0, 5).map((a) => (
                <span key={a.codigoProducto} className={`toldo__icono toldo__icono--${a.disponibilidad}`}>
                  {iconoProducto(a.codigoProducto, a.categoria)}
                </span>
              ))}
            </span>
          )}
        </span>
      )}
    </button>
  );
}

/** Lo que tiene un puesto: cada producto con su dibujo, su precio y cuánto le queda. */
export function DetallePuesto({
  item,
  contenedor,
  usuario,
  alCerrar,
}: {
  item: PuestoDelPlano;
  contenedor: Contenedor;
  usuario: Usuario | null;
  alCerrar: () => void;
}) {
  const { puesto, articulos, ofertas, precios = [] } = item;
  const titulo = nombreDelPuesto(puesto);
  const caja = useRef<HTMLElement>(null);
  const r = resumen(item);
  useEffect(() => {
    caja.current?.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
  }, [puesto.numero]);
  const ordenados = [...articulos].sort(
    (a, b) => Number(a.disponibilidad === "agotado") - Number(b.disponibilidad === "agotado") || a.nombreProducto.localeCompare(b.nombreProducto),
  );

  return (
    <article ref={caja} className="detalle-puesto" aria-label={`Detalle de ${titulo}`}>
      <header className="detalle-puesto__cabeza" style={{ ["--toldo" as string]: colorRubro(puesto.rubros[0]) }}>
        {puesto.foto ? (
          <img className="detalle-puesto__foto" src={puesto.foto} alt={`Foto de ${titulo}`} />
        ) : (
          <span className="detalle-puesto__foto detalle-puesto__foto--vacia" aria-hidden="true">
            {articulos[0] ? iconoProducto(articulos[0].codigoProducto, articulos[0].categoria) : "🏪"}
          </span>
        )}
        <div className="detalle-puesto__datos">
          <h3 className="detalle-puesto__nombre">{titulo}</h3>
          {puesto.referencia && <p className="tenue">📍 {puesto.referencia}</p>}
          <p className="detalle-puesto__resumen">
            {r.total > 0 ? `${r.hay} de ${r.total} productos disponibles` : "Todavía no cargó productos"}
            {r.poco > 0 && ` · ${r.poco} se están acabando`}
            {r.agotados > 0 && ` · ${r.agotados} agotados`}
          </p>
          <ContactoPuesto puesto={puesto} />
        </div>
        <button type="button" className="boton boton--suave detalle-puesto__cerrar" onClick={alCerrar} aria-label="Cerrar el detalle">
          ✕
        </button>
      </header>

      {ordenados.length > 0 && (
        <ul className="productos-puesto" aria-label={`Lo que tiene hoy ${titulo}`}>
          {ordenados.map((a) => {
            const nivel = nivelExistencia(a);
            return (
              <li key={a.codigoProducto} className={`producto-puesto producto-puesto--${a.disponibilidad}`}>
                <span className="producto-puesto__dibujo" aria-hidden="true">
                  {iconoProducto(a.codigoProducto, a.categoria)}
                </span>
                <span className="producto-puesto__nombre">{a.nombreProducto}</span>
                <span className="producto-puesto__precio">
                  Bs {bs(a.monto)} <span className="tenue">/{a.presentacion}</span>
                </span>
                <span className="producto-puesto__queda">
                  {a.disponibilidad === "agotado"
                    ? "Se acabó"
                    : a.cantidad !== null
                      ? `Le quedan ${textoCantidad(a.cantidad, a.presentacion)}`
                      : textoDisponibilidad(a.disponibilidad)}
                </span>
                {nivel !== null && (
                  <span className="existencia" aria-hidden="true">
                    <span className="existencia__barra" style={{ width: `${Math.round(nivel * 100)}%` }} />
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {ordenados.length === 0 && precios.length > 0 && (
        <ul className="productos-puesto">
          {precios.map((p) => (
            <li key={p.codigoProducto} className="producto-puesto">
              <span className="producto-puesto__dibujo" aria-hidden="true">
                {iconoProducto(p.codigoProducto)}
              </span>
              <span className="producto-puesto__nombre">{p.nombreProducto}</span>
              <span className="producto-puesto__precio">
                Bs {bs(p.monto)} <span className="tenue">/{p.unidad}</span>
              </span>
              <span className="producto-puesto__queda tenue">
                {p.fuente === "campo" ? "medido en campo" : "declarado"}
                {p.fecha && ` el ${fechaDiaMes(p.fecha)}`}
              </span>
            </li>
          ))}
        </ul>
      )}

      {ofertas.length > 0 && (
        <div className="detalle-puesto__ofertas">
          <h4 className="subseccion">Sus ofertas de hoy</h4>
          {ofertas.map((o) => (
            <TarjetaOferta key={o.id} oferta={o} contenedor={contenedor} usuario={usuario} conMercado={false} />
          ))}
        </div>
      )}
      <p className="tenue detalle-puesto__nota">Los precios y cantidades los pone la casera desde su celular.</p>
    </article>
  );
}
