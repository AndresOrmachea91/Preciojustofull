import type { MarcadorMapa, Producto } from "@/dominio/modelo";
import { etiquetaNivel, etiquetaTipo, explicacionProcedencia, publicaRango } from "@/dominio/modelo";
import { Confianza } from "@/ui/componentes/Confianza";
import { Procedencia } from "@/ui/componentes/Procedencia";

interface Props {
  readonly marcador: MarcadorMapa | null;
  readonly producto: Producto | null;
}

/** Lo que se ve al hacer clic en un punto: quién es, y qué precio tiene y de dónde sale. */
export function PanelPunto({ marcador, producto }: Props) {
  if (!marcador) {
    return (
      <aside className="panel panel--vacio">
        <p>Tocá un punto del mapa para ver su precio y de dónde sale.</p>
      </aside>
    );
  }
  const { mercado, precio } = marcador;
  const rango = publicaRango(mercado.tipo);

  return (
    <aside className="panel" aria-live="polite">
      <header>
        <h2 className="panel__nombre">{mercado.nombre}</h2>
        <p className="panel__meta">
          {etiquetaTipo(mercado.tipo)} · {mercado.macrodistrito}
          {mercado.codigoPadre && <> · sector de {mercado.codigoPadre}</>}
        </p>
        <p className={`panel__nivel panel__nivel--${mercado.nivelPrecio}`}>{etiquetaNivel(mercado.nivelPrecio)}</p>
      </header>

      {precio ? (
        <section className={`panel__precio panel__precio--${precio.procedencia}`}>
          <Procedencia valor={precio.procedencia} />
          <p className="panel__monto">
            {producto?.nombre ?? precio.codigoProducto}:{" "}
            {rango ? (
              <>Bs {precio.rango.minimo.toFixed(2)} a {precio.rango.maximo.toFixed(2)}</>
            ) : (
              <>Bs {precio.rango.centro.toFixed(2)}</>
            )}
            <span className="tenue"> por {precio.unidad}</span>
          </p>
          <p className="panel__explicacion">{explicacionProcedencia(precio, mercado)}</p>
          <p className="panel__pie">
            <Confianza nivel={precio.confianza} />
            <span className="tenue">
              {precio.fechaObservacionMasReciente
                ? `Dato más reciente: ${precio.fechaObservacionMasReciente}`
                : `Período ${precio.periodo}`}
            </span>
          </p>
        </section>
      ) : (
        <section className="panel__precio panel__precio--sin-datos">
          <p>
            Sin precio para este producto acá: no hay mediciones en este lugar ni referencia de
            ciudad de su nivel. No se inventa.
          </p>
        </section>
      )}
    </aside>
  );
}
