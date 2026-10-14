import { useEffect, useState } from "react";

import type { Referencias as DatosReferencias } from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { Confianza } from "@/ui/componentes/Confianza";
import { MensajeError, textoDeError } from "@/ui/componentes/Mensajes";

/**
 * Los roles con lo que puede hacer cada uno, y de dónde salen los precios
 * con la confianza que el motor les da. Solo lectura: lo decide el sistema.
 */
export function Referencias({ contenedor }: { contenedor: Contenedor }) {
  const [datos, setDatos] = useState<DatosReferencias | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    contenedor.verAuditoria.referencias().then(setDatos, (e) => setError(textoDeError(e)));
  }, [contenedor]);

  if (error) return <MensajeError texto={error} />;
  if (!datos) return <p className="estado">Cargando…</p>;

  const nombreFuente = new Map(datos.fuentes.map((f) => [f.codigo, f.nombre]));

  return (
    <>
      <h3 className="subseccion">Roles y lo que puede hacer cada uno</h3>
      <div className="roles">
        {datos.roles.map((r) => (
          <section key={r.codigo} className="rol" aria-labelledby={`rol-${r.codigo}`}>
            <h4 id={`rol-${r.codigo}`} className="rol__nombre">
              {r.nombre}
            </h4>
            {r.descripcion && <p className="tenue rol__descripcion">{r.descripcion}</p>}
            <ul className="rol__permisos">
              {r.permisos.map((p) => (
                <li key={p.codigo}>{p.descripcion}</li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      <h3 className="subseccion">De dónde salen los precios</h3>
      <div className="tabla-envoltura">
        <table className="tabla" aria-label="Fuentes de precios">
          <thead>
            <tr>
              <th>Fuente</th>
              <th>Confianza</th>
              <th>Cómo llega</th>
            </tr>
          </thead>
          <tbody>
            {datos.fuentes.map((f) => (
              <tr key={f.codigo}>
                <td>
                  <span className="auditoria-celda">
                    <strong>{f.nombre}</strong>
                    <span className="tenue">{f.descripcion}</span>
                  </span>
                </td>
                <td>
                  <Confianza nivel={f.confianzaBase} />
                </td>
                <td>
                  {f.automatica ? "El recolector, cada día" : "La registra una persona"}
                  {f.derivaDe && (
                    <span className="tenue"> · copia a {nombreFuente.get(f.derivaDe) ?? f.derivaDe}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
