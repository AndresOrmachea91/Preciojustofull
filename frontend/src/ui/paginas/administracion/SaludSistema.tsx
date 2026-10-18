import { useCallback, useEffect, useState } from "react";

import { porcentaje, type EstadoSalud, type SaludSistema as Salud } from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { fechaCorta } from "@/ui/formato";

const TEXTO_ESTADO: Record<EstadoSalud, string> = { bien: "Bien", revisar: "Revisar", sin_datos: "Sin datos" };

function tamano(bytes: number | null): string {
  if (bytes === null) return "—";
  return bytes > 1_000_000 ? `${(bytes / 1_000_000).toFixed(1)} MB` : `${Math.round(bytes / 1000)} KB`;
}

/**
 * Salud del sistema (C132): si la recolección corre, si el último respaldo
 * se pudo restaurar de prueba y qué parte de los datos es medida y no
 * estimada. Cada punto dice su estado con palabras, no solo con color.
 */
export function SaludSistema({ contenedor }: { contenedor: Contenedor }) {
  const [salud, setSalud] = useState<Salud | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(() => {
    setError(null);
    contenedor.operarSistema.salud().then(setSalud, (e) => setError(textoDeError(e)));
  }, [contenedor]);

  useEffect(cargar, [cargar]);

  if (error) return <MensajeError texto={error} />;
  if (!salud) return <p className="estado">Revisando el sistema…</p>;

  return (
    <section aria-labelledby="titulo-salud">
      <div className="salud__cabecera">
        <h3 id="titulo-salud" className="subseccion">
          Salud del sistema
        </h3>
        <span className={`salud__estado salud__estado--${salud.estadoGeneral}`}>{TEXTO_ESTADO[salud.estadoGeneral]}</span>
        <button type="button" className="boton boton--suave" onClick={cargar}>
          Volver a revisar
        </button>
      </div>

      <ul className="salud__puntos">
        {salud.puntos.map((p) => (
          <li key={p.nombre} className={`salud__punto salud__punto--${p.estado}`}>
            <span className="salud__marca" aria-hidden="true" />
            <div>
              <strong>{p.nombre}</strong> <span className="salud__etiqueta">· {TEXTO_ESTADO[p.estado]}</span>
              <p className="tenue">{p.detalle}</p>
            </div>
          </li>
        ))}
      </ul>

      {salud.respaldo && (
        <>
          <h4 className="subseccion">Último respaldo</h4>
          <p>
            {salud.respaldo.fecha ? fechaCorta(salud.respaldo.fecha) : "—"} · {salud.respaldo.archivo ?? "—"} ·{" "}
            {tamano(salud.respaldo.tamanoBytes)} ·{" "}
            {salud.respaldo.verificado ? "restaurado de prueba con éxito" : "NO se pudo restaurar de prueba"}
          </p>
        </>
      )}

      {salud.recolecciones.length > 0 && (
        <>
          <h4 className="subseccion">Recolección por fuente</h4>
          <div className="tabla-envoltura">
            <table className="tabla">
              <thead>
                <tr>
                  <th scope="col">Fuente</th>
                  <th scope="col">Último éxito</th>
                  <th scope="col">Precios nuevos en 24 h</th>
                </tr>
              </thead>
              <tbody>
                {salud.recolecciones.map((r) => (
                  <tr key={r.fuente}>
                    <td>{r.fuente}</td>
                    <td>{r.exito ? fechaCorta(r.ocurridoEn) : `nunca (último intento ${fechaCorta(r.ocurridoEn)})`}</td>
                    <td>{r.hechosNuevos24h}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {salud.fuentes.length > 0 && (
        <>
          <h4 className="subseccion">Observaciones guardadas</h4>
          <div className="tabla-envoltura">
            <table className="tabla">
              <thead>
                <tr>
                  <th scope="col">Fuente</th>
                  <th scope="col">Observaciones</th>
                  <th scope="col">Última captura</th>
                </tr>
              </thead>
              <tbody>
                {salud.fuentes.map((f) => (
                  <tr key={f.fuente}>
                    <td>{f.fuente}</td>
                    <td>{f.observaciones.toLocaleString("es-BO")}</td>
                    <td>{f.ultimaCaptura ? fechaCorta(f.ultimaCaptura) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {salud.coberturaObservada !== null && (
        <p className="tenue">
          {porcentaje(salud.coberturaObservada)} de los pares mercado-producto tienen un precio medido en los últimos{" "}
          {salud.ventanaDias} días; el resto se muestra como estimado.
        </p>
      )}
    </section>
  );
}
