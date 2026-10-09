import { useEffect, useState } from "react";

import type { ReporteEnRevision } from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { useCatalogo } from "@/ui/hooks/useCatalogo";

const QUE_PASO: Record<ReporteEnRevision["estado"], string> = {
  pendiente: "Esperando revisión",
  aprobado: "Aprobado: ya cuenta en el cálculo",
  rechazado: "Rechazado",
};

/** Los reportes propios y en qué quedó cada uno. */
export function MisReportes({ contenedor }: { contenedor: Contenedor }) {
  const { productos, mercados } = useCatalogo(contenedor);
  const [reportes, setReportes] = useState<ReporteEnRevision[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    contenedor.reportarPrecio.misReportes().then(setReportes, (e) => setError(textoDeError(e)));
  }, [contenedor]);

  const nombre = (lista: { codigo: string; nombre: string }[], codigo: string) =>
    lista.find((x) => x.codigo === codigo)?.nombre ?? codigo;

  return (
    <>
      <MensajeError texto={error} />
      {!reportes && !error && <p className="estado">Cargando sus reportes…</p>}
      {reportes && reportes.length === 0 && <p className="estado">Todavía no reportó ningún precio.</p>}
      <div className="lista">
        {reportes?.map((r) => (
          <article key={r.id} className="tarjeta" aria-label={`Reporte de ${nombre(productos, r.codigoProducto)}`}>
            <div className="tarjeta__cabecera">
              <div>
                <h3 className="tarjeta__nombre">{nombre(productos, r.codigoProducto)}</h3>
                <p className="tarjeta__zona">
                  {nombre(mercados, r.codigoMercado)} · {new Date(r.creadoEn).toLocaleDateString("es-BO")}
                </p>
              </div>
              <span className={`estado-reporte estado-reporte--${r.estado}`}>{QUE_PASO[r.estado]}</span>
            </div>
            <p className="tarjeta__precio">
              Bs {r.monto.toFixed(2)} <span className="tarjeta__unidad">por {r.unidad.toLowerCase()}</span>
            </p>
            {r.motivoRechazo && <p className="tarjeta__nota">Motivo: {r.motivoRechazo}</p>}
          </article>
        ))}
      </div>
    </>
  );
}
