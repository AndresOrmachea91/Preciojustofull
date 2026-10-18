import type { MarcadorMapa, Oferta, Producto, Usuario } from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import {
  esPrecioViejo,
  etiquetaNivel,
  etiquetaTipo,
  explicacionProcedencia,
  publicaRango,
  textoAntiguedad,
} from "@/dominio/modelo";
import { Confianza } from "@/ui/componentes/Confianza";
import { Icono } from "@/ui/componentes/Iconos";
import { Procedencia } from "@/ui/componentes/Procedencia";
import { TarjetaOferta } from "@/ui/componentes/TarjetaOferta";
import { hrefMercado } from "@/ui/hooks/useRuta";

interface Props {
  readonly marcador: MarcadorMapa | null;
  readonly producto: Producto | null;
  /** Ofertas vigentes de este producto en este lugar (C133). */
  readonly ofertas?: readonly Oferta[];
  readonly contenedor?: Contenedor;
  readonly usuario?: Usuario | null;
}

/** Lo que se ve al hacer clic en un punto: quién es, y qué precio tiene y de dónde sale. */
export function PanelPunto({ marcador, producto, ofertas = [], contenedor, usuario = null }: Props) {
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
        <a className="panel__entrar" href={hrefMercado(mercado.codigo)}>
          Entrar al mercado: todos sus precios y puestos <Icono nombre="flecha" tamano={16} />
        </a>
      </header>

      {precio ? (
        <section
          className={`panel__precio panel__precio--${precio.procedencia}${esPrecioViejo(precio) ? " precio--viejo" : ""}`}
        >
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
          {esPrecioViejo(precio) && (
            <p className="aviso-viejo">El dato es de {textoAntiguedad(precio)}: el precio pudo cambiar.</p>
          )}
          {precio.motivosRango.length > 0 && (
            <p className="tenue panel__motivos">Rango más ancho: {precio.motivosRango.join("; ")}.</p>
          )}
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

      {contenedor &&
        ofertas.map((o) => (
          <TarjetaOferta key={o.id} oferta={o} contenedor={contenedor} usuario={usuario} conMercado={false} />
        ))}
    </aside>
  );
}
