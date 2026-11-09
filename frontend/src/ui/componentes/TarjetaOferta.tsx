import { useState } from "react";

import {
  bs,
  puede,
  textoAhorroOferta,
  textoVence,
  tituloPuesto,
  type Oferta,
  type Usuario,
} from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { Icono } from "@/ui/componentes/Iconos";
import { MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { hrefMercado } from "@/ui/hooks/useRuta";

interface Props {
  readonly oferta: Oferta;
  readonly contenedor: Contenedor;
  readonly usuario: Usuario | null;
  /** Dentro de la ficha de ese mismo mercado no hace falta el enlace al mercado. */
  readonly conMercado?: boolean;
}

/**
 * Una oferta del casero (C133), con su candado a la vista: dice que la
 * declara el vendedor, cuánto ahorra frente al precio del SISTEMA y cuándo
 * vence. Abajo, el "¿Lo viste así?": confirmar o desmentir en un toque.
 */
export function TarjetaOferta({ oferta, contenedor, usuario, conMercado = true }: Props) {
  const [cuenta, setCuenta] = useState({ confirmaron: oferta.confirmaron, desmintieron: oferta.desmintieron });
  const [respuesta, setRespuesta] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const titulo = `Oferta de ${oferta.nombreProducto}`;

  async function decir(laVioAsi: boolean) {
    setError(null);
    setEnviando(true);
    try {
      const r = await contenedor.ofertas.confirmar(oferta.id, laVioAsi);
      setCuenta({ confirmaron: r.confirmaron, desmintieron: r.desmintieron });
      setRespuesta(
        r.pausada
          ? "Gracias. Dos personas dijeron que no estaba así: la oferta queda pausada hasta que la revisen."
          : laVioAsi
            ? "Gracias: su confirmación ayuda a otros compradores."
            : "Gracias. Si otra persona tampoco la ve así, la oferta se pausa para revisión.",
      );
      // Una oferta pausada sigue a la vista con su aviso hasta que se recargue
      // la pantalla: desaparecer de golpe se leería como un error.
    } catch (e) {
      setError(textoDeError(e));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <article className="oferta" aria-label={titulo}>
      <header className="oferta__cabeza">
        <span className="oferta__sello" aria-hidden="true">
          <Icono nombre="oferta" tamano={18} />
        </span>
        <div className="oferta__titulo">
          <h3 className="oferta__producto">
            {oferta.combo && <span className="chip chip--combo">{oferta.combo}</span>} {oferta.nombreProducto}
          </h3>
          <p className="oferta__lugar">
            {conMercado ? <a href={hrefMercado(oferta.codigoMercado)}>{oferta.nombreMercado}</a> : null}
            {conMercado && oferta.numeroPuesto ? " · " : null}
            {oferta.numeroPuesto && tituloPuesto(oferta.numeroPuesto, oferta.nombrePuesto)}
          </p>
        </div>
        <p className="oferta__precio">
          Bs {bs(oferta.monto)}
          <span className="tenue"> por {oferta.presentacion}</span>
        </p>
      </header>

      <p className="oferta__ahorro">{textoAhorroOferta(oferta)}.</p>
      <p className="oferta__meta">
        <span className="oferta__declarada">Declarada por el vendedor</span>
        <span>{textoVence(oferta.hasta)}</span>
        {oferta.nota && <span>«{oferta.nota}»</span>}
      </p>

      <footer className="oferta__pie">
        <span className="tenue">
          {cuenta.confirmaron === 0 && cuenta.desmintieron === 0
            ? "Nadie la confirmó todavía"
            : `${cuenta.confirmaron} la ${cuenta.confirmaron === 1 ? "vio" : "vieron"} así` +
              (cuenta.desmintieron ? ` · ${cuenta.desmintieron} ${cuenta.desmintieron === 1 ? "dijo" : "dijeron"} que no` : "")}
        </span>
        {puede(usuario, "reportar_precio") ? (
          respuesta ? null : (
            <span className="oferta__botones" role="group" aria-label={`¿Vio así la ${titulo.toLowerCase()}?`}>
              <span className="tenue">¿La vio así?</span>
              <button type="button" className="boton boton--suave boton--chico" disabled={enviando} onClick={() => void decir(true)}>
                Sí
              </button>
              <button type="button" className="boton boton--suave boton--chico" disabled={enviando} onClick={() => void decir(false)}>
                No estaba así
              </button>
            </span>
          )
        ) : (
          <a className="tenue" href="#/ingresar">
            Ingrese para decir si la vio así
          </a>
        )}
      </footer>
      {respuesta && (
        <p className="oferta__gracias" role="status">
          {respuesta}
        </p>
      )}
      <MensajeError texto={error} />
    </article>
  );
}
