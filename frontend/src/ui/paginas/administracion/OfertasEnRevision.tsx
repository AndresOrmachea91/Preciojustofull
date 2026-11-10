import { useCallback, useEffect, useState } from "react";

import { bs, sinTildes, textoVence, tituloPuesto, type Oferta, type OfertaEnRevision } from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { MensajeAviso, MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { fechaCorta } from "@/ui/formato";

/**
 * Ofertas que dos compradores distintos desmintieron (C133). No se muestran
 * hasta que alguien las mire: reactivar si era verdad, retirar si no.
 * Ninguna de las dos borra nada.
 */
export function OfertasEnRevision({ contenedor }: { contenedor: Contenedor }) {
  const [lista, setLista] = useState<OfertaEnRevision[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const cargar = useCallback(() => {
    contenedor.revisarOfertas.pendientes().then(setLista, (e) => setError(textoDeError(e)));
  }, [contenedor]);
  useEffect(cargar, [cargar]);

  async function decidir(o: OfertaEnRevision, reactivar: boolean) {
    setError(null);
    try {
      await (reactivar ? contenedor.revisarOfertas.reactivar(o.id) : contenedor.revisarOfertas.retirar(o.id));
      setAviso(`${o.nombreProducto} en ${o.nombreMercado}: ${reactivar ? "vuelve a mostrarse" : "retirada"}.`);
      cargar();
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  return (
    <section aria-labelledby="titulo-ofertas-revision">
      <h3 id="titulo-ofertas-revision" className="subseccion">
        Ofertas pausadas por los compradores
      </h3>
      <p className="tenue">
        Dos personas distintas dijeron que la oferta no estaba así. Si se confirma que era verdad (por ejemplo, con una
        visita), reactívela; si no, retírela. La oferta y lo que dijeron quedan en la auditoría.
      </p>
      <MensajeError texto={error} />
      <MensajeAviso texto={aviso} />
      {!lista && !error && <p className="estado">Cargando…</p>}
      {lista && lista.length === 0 && <p className="estado">No hay ofertas pausadas.</p>}
      {lista && lista.length > 0 && (
        <div className="tabla-envoltura">
          <table className="tabla" aria-label="Ofertas en revisión">
            <thead>
              <tr>
                <th>Oferta</th>
                <th>Dónde</th>
                <th>Compradores</th>
                <th>Vence</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {lista.map((o) => (
                <tr key={o.id}>
                  <td>
                    {o.nombreProducto} a Bs {bs(o.monto)} <span className="tenue">por {o.presentacion}</span>
                    {o.nota && <div className="tenue">«{o.nota}»</div>}
                  </td>
                  <td>
                    {o.nombreMercado}
                    {o.numeroPuesto && <div className="tenue">{tituloPuesto(o.numeroPuesto)}</div>}
                  </td>
                  <td>
                    {o.desmintieron} dijeron que no · {o.confirmaron} que sí
                  </td>
                  <td className="tenue">{fechaCorta(o.hasta)}</td>
                  <td>
                    <div className="tabla__acciones">
                      <button type="button" className="boton boton--suave" onClick={() => void decidir(o, true)}>
                        Reactivar
                      </button>
                      <button type="button" className="boton boton--peligro" onClick={() => void decidir(o, false)}>
                        Retirar
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <OfertasVigentes contenedor={contenedor} alCambiar={cargar} />
    </section>
  );
}

/**
 * Todas las ofertas que se están mostrando ahora (C146). El administrador
 * puede dar de baja cualquiera que vea engañosa, aunque nadie la haya
 * desmentido. Se marca «retirada»: no se borra y queda en la auditoría.
 */
function OfertasVigentes({ contenedor, alCambiar }: { contenedor: Contenedor; alCambiar: () => void }) {
  const [lista, setLista] = useState<Oferta[] | null>(null);
  const [texto, setTexto] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const cargar = useCallback(() => {
    contenedor.ofertas.vigentes().then(setLista, (e) => setError(textoDeError(e)));
  }, [contenedor]);
  useEffect(cargar, [cargar]);

  async function darDeBaja(o: Oferta) {
    setError(null);
    try {
      await contenedor.revisarOfertas.retirar(o.id);
      setAviso(`Dada de baja: ${o.nombreProducto} en ${o.nombreMercado}. Ya no se muestra.`);
      cargar();
      alCambiar();
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  const buscado = sinTildes(texto.trim());
  const visibles = (lista ?? []).filter(
    (o) => !buscado || sinTildes(`${o.nombreProducto} ${o.nombreMercado} ${o.nombrePuesto ?? ""} ${o.combo ?? ""}`).includes(buscado),
  );

  return (
    <>
      <h3 className="subseccion">Ofertas vigentes</h3>
      <p className="tenue">
        Las que se ven ahora en el mapa y en Ofertas de hoy. Si una es engañosa, désela de baja: deja de mostrarse en
        el momento y queda guardada como «retirada».
      </p>
      <input
        className="barra__buscar"
        type="search"
        placeholder="Buscar por producto, mercado, puesto o combo"
        aria-label="Buscar ofertas vigentes"
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
      />
      <MensajeError texto={error} />
      <MensajeAviso texto={aviso} />
      {!lista && !error && <p className="estado">Cargando…</p>}
      {lista && visibles.length === 0 && <p className="estado">No hay ofertas vigentes que coincidan.</p>}
      {visibles.length > 0 && (
        <div className="tabla-envoltura">
          <table className="tabla" aria-label="Ofertas vigentes">
            <thead>
              <tr>
                <th>Oferta</th>
                <th>Dónde</th>
                <th>Ahorro</th>
                <th>Vence</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {visibles.map((o) => (
                <tr key={o.id}>
                  <td>
                    {o.combo && <span className="chip chip--combo">{o.combo}</span>} {o.nombreProducto} a Bs {bs(o.monto)}{" "}
                    <span className="tenue">por {o.presentacion}</span>
                  </td>
                  <td>
                    {o.nombreMercado}
                    {o.numeroPuesto && <div className="tenue">{tituloPuesto(o.numeroPuesto, o.nombrePuesto)}</div>}
                  </td>
                  <td>−{Math.round(o.ahorroRelativo * 100)} %</td>
                  <td className="tenue">{textoVence(o.hasta)}</td>
                  <td>
                    <button type="button" className="boton boton--peligro" onClick={() => void darDeBaja(o)}>
                      Dar de baja
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
