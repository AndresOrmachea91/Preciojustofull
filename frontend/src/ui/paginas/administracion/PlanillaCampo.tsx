import { useEffect, useState, type FormEvent } from "react";

import {
  COLUMNAS_CAMPO,
  PLANTILLA_CAMPO,
  planillaDeLaRonda,
} from "@/aplicacion/casosUso/administracion/operarSistema";
import type {
  PlanDeVerificacion,
  ResultadoImportacion,
} from "@/dominio/modelo";
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
      setResultado(
        await contenedor.operarSistema.importarCampo(
          texto,
          archivo.name,
          soloRevisar,
        ),
      );
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
    <>
      <RondaSugerida contenedor={contenedor} />
      <section aria-labelledby="titulo-campo">
        <h3 id="titulo-campo" className="subseccion">
          Planilla del levantamiento de campo
        </h3>
        <p className="tenue">
          Una fila por precio anotado en un puesto. Columnas:{" "}
          <code>{COLUMNAS_CAMPO.join(", ")}</code>. Las cinco primeras son
          obligatorias; el monto acepta coma decimal (8,50) y la presentación es
          kilo, libra, arroba, quintal, unidad, docena, maple, litro o atado. En{" "}
          <code>puesto</code> va el número del puesto visitado (14, B-3); para
          un sector, ponga en <code>mercado</code> el código del sector.
        </p>
        <p>
          <a
            className="boton boton--suave"
            href={ENLACE_PLANTILLA}
            download="plantilla_campo.csv"
          >
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
            <button
              type="submit"
              className="boton boton--suave"
              disabled={!archivo || enviando}
            >
              Revisar sin guardar
            </button>
            {resultado?.soloRevisar && resultado.validas > 0 && (
              <button
                type="button"
                className="boton"
                disabled={enviando}
                onClick={() => void enviar(false)}
              >
                Importar {resultado.validas}{" "}
                {resultado.validas === 1 ? "fila" : "filas"}
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
                  De <strong>{resultado.leidas}</strong> filas,{" "}
                  <strong>{resultado.validas}</strong> se pueden importar.
                </>
              ) : (
                <>
                  Importadas <strong>{resultado.guardadas}</strong> de{" "}
                  {resultado.validas} válidas
                  {resultado.guardadas < resultado.validas &&
                    " (las demás ya estaban cargadas)"}
                  .
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
    </>
  );
}

const PRODUCTOS_POR_RONDA = 10;
const LUGARES_POR_RONDA = 6;

/**
 * La próxima ronda de campo, armada por el sistema (A4230): los productos
 * con más duda en los lugares menos cubiertos, repartidos por macrodistrito.
 * Se descarga como planilla con el monto en blanco y se importa abajo.
 */
function RondaSugerida({ contenedor }: { contenedor: Contenedor }) {
  const [plan, setPlan] = useState<PlanDeVerificacion | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    contenedor.mercados
      .verificaciones()
      .then(setPlan, (e) => setError(textoDeError(e)));
  }, [contenedor]);

  if (error) return <MensajeError texto={error} />;
  if (!plan) return <p className="estado">Armando la próxima ronda…</p>;

  const productos = plan.productos
    .filter((p) => p.puntaje > 0)
    .slice(0, PRODUCTOS_POR_RONDA);
  const lugares = plan.lugares.slice(0, LUGARES_POR_RONDA);
  if (productos.length === 0) {
    return (
      <p className="aviso">
        Todo está medido y al día: no hace falta una ronda nueva.
      </p>
    );
  }
  const csv = planillaDeLaRonda(plan, {
    productos: PRODUCTOS_POR_RONDA,
    lugares: LUGARES_POR_RONDA,
    fecha: plan.fecha,
  });

  return (
    <section aria-labelledby="titulo-ronda" className="ronda">
      <h3 id="titulo-ronda" className="subseccion">
        Próxima ronda sugerida
      </h3>
      <p className="tenue">
        En vez de medir todo por igual: primero lo que nadie midió, lo vencido y
        lo que más se mueve, en los lugares con menos datos y turnándose entre
        macrodistritos. Son {productos.length * lugares.length} precios para
        anotar.
      </p>
      <div className="ronda__columnas">
        <div>
          <h4 className="ronda__titulo">Qué medir</h4>
          <ol className="ronda__lista">
            {productos.map((p) => (
              <li key={p.producto.codigo}>
                {p.producto.nombre}
                {p.motivos[0] && (
                  <span className="tenue"> · {p.motivos[0]}</span>
                )}
              </li>
            ))}
          </ol>
        </div>
        <div>
          <h4 className="ronda__titulo">Dónde</h4>
          <ol className="ronda__lista">
            {lugares.map((x) => (
              <li key={x.mercado.codigo}>
                {x.mercado.nombre}
                <span className="tenue">
                  {" "}
                  · {x.mercado.macrodistrito || x.mercado.zona}
                </span>
              </li>
            ))}
          </ol>
        </div>
      </div>
      <p>
        <a
          className="boton"
          href={`data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`}
          download={`ronda_${plan.fecha}.csv`}
        >
          Descargar la planilla de esta ronda
        </a>
      </p>
    </section>
  );
}
