import { useEffect, useState, type FormEvent } from "react";

import type { MarcadorMapa, Oferta, Precio, Presentacion, Producto, Usuario } from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import {
  esPrecioViejo,
  etiquetaNivel,
  etiquetaTipo,
  explicacionProcedencia,
  presentacionBase,
  publicaRango,
  puede,
  textoAntiguedad,
} from "@/dominio/modelo";
import { Confianza } from "@/ui/componentes/Confianza";
import { Icono } from "@/ui/componentes/Iconos";
import { MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { Procedencia } from "@/ui/componentes/Procedencia";
import { TarjetaOferta } from "@/ui/componentes/TarjetaOferta";
import { hrefMercado } from "@/ui/hooks/useRuta";

/** Lo que se sabe del producto en toda la ciudad: se muestra mientras no se elige un punto. */
export interface ResumenDelMapa {
  readonly estimados: number;
  readonly observados: number;
  readonly sinDatos: number;
  /** El precio de un lugar estimado: es la referencia de la ciudad con el ajuste del lugar. */
  readonly referencia: Precio | null;
  readonly ofertas: number;
}

interface Props {
  readonly marcador: MarcadorMapa | null;
  readonly producto: Producto | null;
  /** En qué presentación se están viendo los precios (kilo, libra...). */
  readonly presentacion?: Presentacion | null;
  readonly resumen?: ResumenDelMapa | null;
  /** Ofertas vigentes de este producto en este lugar (C133). */
  readonly ofertas?: readonly Oferta[];
  readonly contenedor?: Contenedor;
  readonly usuario?: Usuario | null;
}

/** Lo que se ve al lado del mapa: el resumen del producto, o el punto elegido con su precio y de dónde sale. */
export function PanelPunto({
  marcador,
  producto,
  presentacion = null,
  resumen = null,
  ofertas = [],
  contenedor,
  usuario = null,
}: Props) {
  if (!marcador) return <PanelResumen producto={producto} resumen={resumen} />;

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
        <section
          className={`panel__precio panel__precio--${precio.procedencia}${esPrecioViejo(precio) ? " precio--viejo" : ""}`}
        >
          <div className="panel__fila">
            <span className="tenue">{producto?.nombre ?? precio.codigoProducto}</span>
            <Procedencia valor={precio.procedencia} />
          </div>
          <p className="panel__monto">
            {rango ? (
              <>
                Bs {precio.rango.minimo.toFixed(2)} <span className="panel__a">a</span> {precio.rango.maximo.toFixed(2)}
              </>
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
            Sin precio para este producto aquí: no hay mediciones en este lugar ni referencia de ciudad de su nivel. No
            se inventa.
          </p>
        </section>
      )}

      {contenedor && producto && mercado.nivelPrecio === "minorista" && (
        <DecirElPrecio
          key={`${mercado.codigo}-${producto.codigo}`}
          contenedor={contenedor}
          usuario={usuario}
          producto={producto}
          codigoMercado={mercado.codigo}
          presentacion={presentacion ?? presentacionBase(producto)}
          sugerido={precio?.rango.centro ?? null}
          esEstimado={!precio || precio.procedencia === "estimado"}
        />
      )}

      {contenedor &&
        ofertas.map((o) => (
          <TarjetaOferta key={o.id} oferta={o} contenedor={contenedor} usuario={usuario} conMercado={false} />
        ))}

      <a className="panel__entrar" href={hrefMercado(mercado.codigo)}>
        Entrar al mercado: todos sus precios y puestos <Icono nombre="flecha" tamano={16} />
      </a>
    </aside>
  );
}

/** Antes de elegir un punto: qué tan medido está este producto y cómo usar el mapa. */
function PanelResumen({ producto, resumen }: { producto: Producto | null; resumen: ResumenDelMapa | null }) {
  const total = resumen ? resumen.estimados + resumen.observados : 0;
  const referencia = resumen?.referencia ?? null;
  return (
    <aside className="panel panel--resumen" aria-live="polite">
      <h2 className="panel__nombre">{producto?.nombre ?? "Precios de La Paz"}</h2>
      {referencia && (
        <p className="panel__monto">
          Bs {referencia.rango.minimo.toFixed(2)} <span className="panel__a">a</span> {referencia.rango.maximo.toFixed(2)}
          <span className="tenue"> por {referencia.unidad}</span>
        </p>
      )}
      {referencia && <p className="tenue panel__subtitulo">Lo que suele costar en un mercado de La Paz.</p>}

      {resumen && total > 0 && (
        <div className="medidor" aria-label={`${resumen.observados} de ${total} lugares con precio medido`}>
          <div className="medidor__barra" aria-hidden="true">
            <span className="medidor__lleno" style={{ width: `${(resumen.observados / total) * 100}%` }} />
          </div>
          <p className="medidor__texto">
            <strong>{resumen.observados}</strong> de {total} lugares con precio medido ahí
            {resumen.observados === 0 && ": el resto se estima desde el boletín oficial de la ciudad"}.
          </p>
        </div>
      )}

      <ol className="panel__pasos">
        <li>Toque un punto del mapa para ver su precio y de dónde sale.</li>
        <li>Si lo vio en ese lugar, diga a cuánto: así deja de ser un estimado.</li>
      </ol>

      {resumen && resumen.ofertas > 0 && (
        <p className="panel__ofertas">
          <Icono nombre="oferta" tamano={16} /> {resumen.ofertas === 1 ? "Un casero tiene" : `${resumen.ofertas} caseros tienen`} una
          oferta hoy: búsquelos por el anillo dorado. <a href="#/ofertas">Ver ofertas</a>
        </p>
      )}
    </aside>
  );
}

interface DecirElPrecioProps {
  readonly contenedor: Contenedor;
  readonly usuario: Usuario | null;
  readonly producto: Producto;
  readonly codigoMercado: string;
  readonly presentacion: Presentacion;
  readonly sugerido: number | null;
  readonly esEstimado: boolean;
}

/**
 * "¿A cuánto lo vio?": el precio que ya se muestra viene escrito, así que
 * confirmarlo es un toque y corregirlo, cambiar un número. Entra como un
 * reporte más: queda pendiente hasta que un administrador lo revise, igual
 * que en «Reportar un precio».
 */
function DecirElPrecio({ contenedor, usuario, producto, codigoMercado, presentacion, sugerido, esEstimado }: DecirElPrecioProps) {
  const [monto, setMonto] = useState(sugerido !== null ? sugerido.toFixed(2) : "");
  const [enviando, setEnviando] = useState(false);
  const [hecho, setHecho] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => setMonto(sugerido !== null ? sugerido.toFixed(2) : ""), [sugerido]);

  if (!puede(usuario, "reportar_precio")) {
    return (
      <p className="decir decir--invitacion">
        ¿Lo vio aquí? <a href="#/ingresar">Ingrese</a> y diga a cuánto: {esEstimado ? "así deja de ser un estimado." : "así el dato se mantiene al día."}
      </p>
    );
  }
  if (hecho) {
    return (
      <p className="decir decir--hecho" role="status">
        Gracias. Su precio queda pendiente hasta que un administrador lo revise; puede seguirlo en «Mis reportes».
      </p>
    );
  }

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await contenedor.reportarPrecio.reportar({
        codigoProducto: producto.codigo,
        codigoMercado,
        monto: Number(monto.replace(",", ".")),
        presentacion: presentacion.codigo,
      });
      setHecho(true);
    } catch (err) {
      setError(textoDeError(err));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="decir" onSubmit={(e) => void enviar(e)} aria-label={`Decir a cuánto vio ${producto.nombre} aquí`}>
      <label className="decir__pregunta" htmlFor="decir-monto">
        ¿Lo vio aquí? Diga a cuánto
      </label>
      <div className="decir__fila">
        <span className="decir__caja">
          <span className="tenue">Bs</span>
          <input
            id="decir-monto"
            inputMode="decimal"
            required
            value={monto}
            onChange={(e) => setMonto(e.target.value)}
            aria-describedby="decir-ayuda"
          />
          <span className="tenue">por {presentacion.nombre.toLowerCase()}</span>
        </span>
        <button type="submit" className="boton" disabled={enviando || !monto}>
          {enviando ? "Enviando…" : "Enviar"}
        </button>
      </div>
      <p id="decir-ayuda" className="tenue decir__ayuda">
        Viene escrito el precio que muestra el sistema: si es ese, solo envíelo.
      </p>
      <MensajeError texto={error} />
    </form>
  );
}
