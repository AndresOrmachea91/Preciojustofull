import { useEffect, useState } from "react";

import { lecturaDelSesgo, porcentaje, type EvaluacionEstimador } from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { fechaCorta } from "@/ui/formato";

/**
 * ¿Qué tan confiable es el estimado? (C130). Donde nadie midió, el sistema
 * estima con el precio de la ciudad y un factor del mercado. Esta página
 * muestra, con los precios que sí se midieron, cuánto se equivoca esa
 * estimación. Es pública a propósito: un sistema que no publica su error
 * pide que le crean a ciegas.
 */
export function PaginaConfiabilidad({ contenedor }: { contenedor: Contenedor }) {
  const [ev, setEv] = useState<EvaluacionEstimador | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    contenedor.verConfiabilidad.ejecutar().then(setEv, (e) => setError(textoDeError(e)));
  }, [contenedor]);

  return (
    <section aria-labelledby="titulo-confiabilidad" className="confiabilidad">
      <h2 id="titulo-confiabilidad" className="seccion">
        ¿Qué tan confiable es el estimado?
      </h2>
      <p className="confiabilidad__intro">
        Cuando nadie midió un precio en un lugar, PrecioJusto lo <strong>estima</strong>: toma el precio oficial de
        la ciudad (SIIP) y lo ajusta por cómo suele estar ese mercado. Para saber cuánto se equivoca, se toma cada
        precio que alguien <strong>sí midió</strong>, se calcula lo que el sistema habría estimado sin mirarlo, y se
        comparan los dos.
      </p>

      <MensajeError texto={error} />
      {!ev && !error && <p className="estado">Calculando…</p>}

      {ev && ev.casos === 0 && (
        <p className="estado">
          Todavía no hay precios medidos del mismo mes que la referencia de la ciudad para comparar. La comparación
          aparece sola cuando se cargue el levantamiento de campo.
        </p>
      )}

      {ev && ev.casos > 0 && ev.errorMedio !== null && ev.cobertura !== null && ev.sesgo !== null && (
        <>
          <div className="cifras">
            <div className="cifra">
              <span className="cifra__valor">{porcentaje(ev.errorMedio)}</span>
              <span className="cifra__nombre">error medio del estimado</span>
            </div>
            <div className="cifra">
              <span className="cifra__valor">{porcentaje(ev.cobertura, 0)}</span>
              <span className="cifra__nombre">de los precios medidos cayó dentro del rango mostrado</span>
            </div>
            <div className="cifra">
              <span className="cifra__valor">{ev.casos}</span>
              <span className="cifra__nombre">
                comparaciones en {ev.mercados} {ev.mercados === 1 ? "lugar" : "lugares"} y {ev.productos}{" "}
                {ev.productos === 1 ? "producto" : "productos"}
              </span>
            </div>
          </div>

          <p>
            En promedio el estimado {lecturaDelSesgo(ev.sesgo)}.
            {ev.errorMedioSinFactor !== null && (
              <>
                {" "}
                Si no se ajustara por mercado (el mismo precio de la ciudad para todos), el error sería{" "}
                <strong>{porcentaje(ev.errorMedioSinFactor)}</strong>:{" "}
                {ev.elFactorAyuda ? "el ajuste por mercado mejora la estimación." : "el ajuste por mercado todavía no mejora la estimación; hay que recalibrarlo con más mediciones."}
              </>
            )}
          </p>

          {ev.porProducto.length > 0 && (
            <>
              <h3 className="subseccion">Por producto</h3>
              <div className="tabla-envoltura">
                <table className="tabla">
                  <thead>
                    <tr>
                      <th scope="col">Producto</th>
                      <th scope="col">Comparaciones</th>
                      <th scope="col">Error medio</th>
                      <th scope="col">Dentro del rango</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ev.porProducto.map((p) => (
                      <tr key={p.codigoProducto}>
                        <td>{p.nombreProducto}</td>
                        <td>{p.casos}</td>
                        <td>{porcentaje(p.errorMedio)}</td>
                        <td>{porcentaje(p.cobertura, 0)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {ev.detalle.length > 0 && (
            <details className="confiabilidad__detalle">
              <summary>Los casos con más error</summary>
              <div className="tabla-envoltura">
                <table className="tabla">
                  <thead>
                    <tr>
                      <th scope="col">Producto</th>
                      <th scope="col">Lugar</th>
                      <th scope="col">Mes</th>
                      <th scope="col">Medido</th>
                      <th scope="col">Estimado</th>
                      <th scope="col">Error</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ev.detalle.slice(0, 20).map((c) => (
                      <tr key={`${c.nombreProducto}-${c.nombreMercado}-${c.periodo}`}>
                        <td>{c.nombreProducto}</td>
                        <td>{c.nombreMercado}</td>
                        <td>{c.periodo}</td>
                        <td>Bs {c.observado.toFixed(2)}</td>
                        <td>
                          Bs {c.estimado.toFixed(2)}
                          <span className="tenue">
                            {" "}
                            ({c.estimadoMinimo.toFixed(2)}–{c.estimadoMaximo.toFixed(2)})
                          </span>
                        </td>
                        <td className={c.dentroDelRango ? undefined : "confiabilidad__fuera"}>
                          {c.error > 0 ? "+" : "−"}
                          {porcentaje(Math.abs(c.error))}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          )}

          <p className="tenue">
            Calculado el {fechaCorta(ev.calculadoEn)}. El factor de cada mercado se aprendió con datos de campo
            anteriores; las mediciones nuevas son la prueba fuera de muestra.
          </p>
        </>
      )}
    </section>
  );
}
