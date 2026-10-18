import { useCallback, useEffect, useState } from "react";

import { bs, tituloPuesto, type OfertaEnRevision } from "@/dominio/modelo";
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
    </section>
  );
}
