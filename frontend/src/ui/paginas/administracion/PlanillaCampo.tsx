import { useState, type FormEvent } from "react";

import { COLUMNAS_CAMPO, PLANTILLA_CAMPO } from "@/aplicacion/casosUso/administracion/operarSistema";
import type { ResultadoImportacion } from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { MensajeError, textoDeError } from "@/ui/componentes/Mensajes";

const ENLACE_PLANTILLA = `data:text/csv;charset=utf-8,${encodeURIComponent(PLANTILLA_CAMPO)}`;

/**
 * La planilla del levantamiento de campo (C127). Primero se revisa —qué
 * filas entrarían y por qué no las otras— y recién después se importa. Lo
 * importado entra como fuente CAMPO: es el lado "observado" del backtest.
 */
export function PlanillaCampo({ contenedor }: { contenedor: Contenedor }) {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [resultado, setResultado] = useState<ResultadoImportacion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(soloRevisar: boolean) {
    if (!archivo) return;
    setError(null);
    setEnviando(true);
    try {
      const texto = await archivo.text();
      setResultado(await contenedor.operarSistema.importarCampo(texto, archivo.name, soloRevisar));
    } catch (e) {
      setError(textoDeError(e));
    } finally {
      setEnviando(false);
    }
  }

  function revisar(e: FormEvent) {
    e.preventDefault();
    void enviar(true);
  }

  return (
    <section aria-labelledby="titulo-campo">
      <h3 id="titulo-campo" className="subseccion">
        Planilla del levantamiento de campo
      </h3>
      <p className="tenue">
        Una fila por precio anotado en un puesto. Columnas: <code>{COLUMNAS_CAMPO.join(", ")}</code>. Las cinco
        primeras son obligatorias; el monto acepta coma decimal (8,50) y la presentación es kilo, libra, arroba,
        quintal, unidad, docena, maple, litro o atado. En <code>puesto</code> va el número del puesto visitado (14,
        B-3); para un sector, ponga en <code>mercado</code> el código del sector.
      </p>
      <p>
        <a className="boton boton--suave" href={ENLACE_PLANTILLA} download="plantilla_campo.csv">
          Descargar la plantilla
        </a>
      </p>

      <form className="formulario formulario--recuadro" onSubmit={revisar}>
        <label className="campo">
          <span>Archivo CSV</span>
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => {
              setArchivo(e.target.files?.[0] ?? null);
              setResultado(null);
            }}
          />
        </label>
        <div className="formulario__botones">
          <button type="submit" className="boton boton--suave" disabled={!archivo || enviando}>
            Revisar sin guardar
          </button>
          {resultado?.soloRevisar && resultado.validas > 0 && (
            <button type="button" className="boton" disabled={enviando} onClick={() => void enviar(false)}>
              Importar {resultado.validas} {resultado.validas === 1 ? "fila" : "filas"}
            </button>
          )}
        </div>
      </form>

      <MensajeError texto={error} />

      {resultado && (
        <div className="importacion" role="status">
          <p>
            {resultado.soloRevisar ? (
              <>
                De <strong>{resultado.leidas}</strong> filas, <strong>{resultado.validas}</strong> se pueden importar.
              </>
            ) : (
              <>
                Importadas <strong>{resultado.guardadas}</strong> de {resultado.validas} válidas
                {resultado.guardadas < resultado.validas && " (las demás ya estaban cargadas)"}.
              </>
            )}
          </p>
          {resultado.rechazadas.length > 0 && (
            <>
              <h4 className="subseccion">Filas que no entran</h4>
              <ul className="importacion__rechazos">
                {resultado.rechazadas.map((r) => (
                  <li key={`${r.fila}-${r.motivo}`}>
                    {r.fila > 0 && <strong>Fila {r.fila}: </strong>}
                    {r.motivo}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </section>
  );
}
