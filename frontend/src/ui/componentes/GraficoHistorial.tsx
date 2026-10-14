import { useEffect, useMemo, useRef, useState, type PointerEvent } from "react";

import type { NivelPrecio, PuntoHistorial } from "@/dominio/modelo";

/**
 * El precio de la ciudad mes a mes, en SVG propio. Una sola escala: las dos
 * series están en Bs por la misma unidad. El color identifica la serie, pero
 * nunca solo: hay leyenda, etiqueta al final de cada línea y una tabla.
 */

const SERIES: { nivel: NivelPrecio; nombre: string }[] = [
  { nivel: "minorista", nombre: "Consumidor final" },
  { nivel: "mayorista", nombre: "Mayorista" },
];

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const ALTO = 240;
const MARGEN = { arriba: 14, derecha: 112, abajo: 28, izquierda: 48 };

function nombreMes(periodo: string): string {
  const [anio, mes] = periodo.split("-");
  return `${MESES[Number(mes) - 1]} ${anio.slice(2)}`;
}

function bs(valor: number): string {
  return `Bs ${valor.toFixed(2)}`;
}

/** Marcas "redondas" del eje: 1, 2, 2,5 o 5 por potencia de 10. */
function marcasDelEje(minimo: number, maximo: number, cuantas = 4): number[] {
  const crudo = (maximo - minimo) / cuantas || 1;
  const potencia = 10 ** Math.floor(Math.log10(crudo));
  const paso = [1, 2, 2.5, 5, 10].map((m) => m * potencia).find((p) => p >= crudo) ?? crudo;
  const desde = Math.floor(minimo / paso) * paso;
  const marcas: number[] = [];
  for (let v = desde; v <= maximo + paso / 2; v += paso) marcas.push(Math.round(v * 100) / 100);
  return marcas;
}

/** Ancho real del contenedor, para que el texto no se achique en el celular. */
function useAncho(inicial = 640) {
  const ref = useRef<HTMLDivElement>(null);
  const [ancho, setAncho] = useState(inicial);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const observador = new ResizeObserver(([e]) => setAncho(Math.max(280, Math.round(e.contentRect.width))));
    observador.observe(el);
    return () => observador.disconnect();
  }, []);
  return [ref, ancho] as const;
}

interface Props {
  readonly puntos: readonly PuntoHistorial[];
  /** "kilo", "arroba"…: en qué está cada precio. */
  readonly unidad: string;
  /** Para llevar el precio por kilo a la presentación elegida (arroba = 11,5). */
  readonly factor: number;
}

export function GraficoHistorial({ puntos, unidad, factor }: Props) {
  const [ref, ancho] = useAncho();
  const [activo, setActivo] = useState<number | null>(null);

  const periodos = useMemo(() => [...new Set(puntos.map((p) => p.periodo))].sort(), [puntos]);
  const valor = useMemo(() => {
    const mapa = new Map(puntos.map((p) => [`${p.nivel}|${p.periodo}`, p.precio * factor]));
    return (nivel: NivelPrecio, periodo: string) => mapa.get(`${nivel}|${periodo}`);
  }, [puntos, factor]);
  const series = SERIES.filter((s) => puntos.some((p) => p.nivel === s.nivel));

  if (periodos.length < 2) return <p className="estado">Todavía no hay suficientes meses para dibujar la evolución.</p>;

  const todos = puntos.map((p) => p.precio * factor);
  const marcas = marcasDelEje(Math.min(...todos), Math.max(...todos));
  const [yMin, yMax] = [marcas[0], marcas[marcas.length - 1]];
  const anchoUtil = ancho - MARGEN.izquierda - MARGEN.derecha;
  const altoUtil = ALTO - MARGEN.arriba - MARGEN.abajo;
  const x = (i: number) => MARGEN.izquierda + (i / (periodos.length - 1)) * anchoUtil;
  const y = (v: number) => MARGEN.arriba + (1 - (v - yMin) / (yMax - yMin || 1)) * altoUtil;

  /** El trazo de una serie; un mes sin dato corta la línea en vez de inventar el tramo. */
  function trazo(nivel: NivelPrecio): string {
    let d = "";
    let abierto = false;
    periodos.forEach((periodo, i) => {
      const v = valor(nivel, periodo);
      if (v === undefined) {
        abierto = false;
        return;
      }
      d += `${abierto ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
      abierto = true;
    });
    return d;
  }

  const paso = Math.max(1, Math.ceil(periodos.length / Math.max(2, Math.floor(anchoUtil / 70))));

  function alMover(e: PointerEvent<SVGRectElement>) {
    const caja = e.currentTarget.getBoundingClientRect();
    const relativo = (e.clientX - caja.left) / caja.width;
    setActivo(Math.min(periodos.length - 1, Math.max(0, Math.round(relativo * (periodos.length - 1)))));
  }

  return (
    <figure className="grafico">
      {series.length > 1 ? (
        <ul className="grafico__leyenda" aria-label="Series">
          {series.map((s) => (
            <li key={s.nivel}>
              <span className={`grafico__clave grafico__clave--${s.nivel}`} aria-hidden="true" />
              {s.nombre}
            </li>
          ))}
        </ul>
      ) : (
        // Con una sola serie no hace falta leyenda: se dice cuál es.
        <p className="grafico__leyenda">Solo hay precio {series[0].nombre.toLowerCase()} para este producto.</p>
      )}

      <div ref={ref} className="grafico__lienzo">
        <svg width={ancho} height={ALTO} role="img" aria-label={`Precio por ${unidad}, mes a mes`}>
          {marcas.map((m) => (
            <g key={m}>
              <line className="grafico__rejilla" x1={MARGEN.izquierda} x2={ancho - MARGEN.derecha} y1={y(m)} y2={y(m)} />
              <text className="grafico__eje" x={MARGEN.izquierda - 8} y={y(m)} dy="0.32em" textAnchor="end">
                {m.toFixed(m < 10 ? 1 : 0)}
              </text>
            </g>
          ))}
          {periodos.map((p, i) =>
            i % paso === 0 || i === periodos.length - 1 ? (
              <text key={p} className="grafico__eje" x={x(i)} y={ALTO - 8} textAnchor="middle">
                {nombreMes(p)}
              </text>
            ) : null,
          )}

          {activo !== null && (
            <line className="grafico__guia" x1={x(activo)} x2={x(activo)} y1={MARGEN.arriba} y2={ALTO - MARGEN.abajo} />
          )}

          {series.map((s) => {
            const ultimo = [...periodos].reverse().find((p) => valor(s.nivel, p) !== undefined)!;
            const i = periodos.indexOf(ultimo);
            const v = valor(s.nivel, ultimo)!;
            return (
              <g key={s.nivel}>
                <path className={`grafico__linea grafico__linea--${s.nivel}`} d={trazo(s.nivel)} />
                <circle className={`grafico__punto grafico__punto--${s.nivel}`} cx={x(i)} cy={y(v)} r={4} />
                <text className="grafico__final" x={x(i) + 10} y={y(v)} dy="0.32em">
                  {bs(v)}
                </text>
              </g>
            );
          })}

          {activo !== null &&
            series.map((s) => {
              const v = valor(s.nivel, periodos[activo]);
              return v === undefined ? null : (
                <circle key={s.nivel} className={`grafico__punto grafico__punto--${s.nivel}`} cx={x(activo)} cy={y(v)} r={4} />
              );
            })}

          <rect
            className="grafico__zona"
            x={MARGEN.izquierda}
            y={MARGEN.arriba}
            width={anchoUtil}
            height={altoUtil}
            onPointerMove={alMover}
            onPointerLeave={() => setActivo(null)}
          />
        </svg>

        {activo !== null && (
          <div
            className="grafico__detalle"
            style={{ left: Math.min(x(activo) + 12, ancho - 180), top: MARGEN.arriba }}
            role="status"
          >
            <strong>{nombreMes(periodos[activo])}</strong>
            {series.map((s) => {
              const v = valor(s.nivel, periodos[activo]);
              return (
                <span key={s.nivel}>
                  <span className={`grafico__clave grafico__clave--${s.nivel}`} aria-hidden="true" />
                  {s.nombre}: {v === undefined ? "sin dato" : bs(v)}
                </span>
              );
            })}
          </div>
        )}
      </div>

      <details className="grafico__tabla">
        <summary>Ver los datos en una tabla</summary>
        <div className="tabla-envoltura">
          <table className="tabla" aria-label="Precio por mes">
            <thead>
              <tr>
                <th>Mes</th>
                {series.map((s) => (
                  <th key={s.nivel}>{s.nombre}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...periodos].reverse().map((p) => (
                <tr key={p}>
                  <td>{nombreMes(p)}</td>
                  {series.map((s) => {
                    const v = valor(s.nivel, p);
                    return (
                      <td key={s.nivel} className="tabla__numero">
                        {v === undefined ? "—" : bs(v)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}
