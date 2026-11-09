import { useEffect, useMemo, useState } from "react";

import { agruparReferencias } from "@/aplicacion/casosUso/publico/verPreciosReferenciales";
import { bs, nombreCategoria, NOMBRE_UNIDAD_BASE, type Precio, type PrecioReferencial } from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { MensajeError, textoDeError } from "@/ui/componentes/Mensajes";

const porUnidad = (p: Precio) => (NOMBRE_UNIDAD_BASE as Record<string, string>)[p.unidad]?.toLowerCase() ?? p.unidad;

/**
 * Precios referenciales de La Paz (C144): todos los productos con el precio
 * oficial de la ciudad, sin el ajuste de ningún mercado. Es la vara con que
 * el sistema estima y compara.
 */
export function PaginaReferencias({ contenedor }: { contenedor: Contenedor }) {
  const [filas, setFilas] = useState<PrecioReferencial[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [texto, setTexto] = useState("");

  useEffect(() => {
    contenedor.referencias.listar().then(setFilas, (e) => setError(textoDeError(e)));
  }, [contenedor]);

  const grupos = useMemo(() => agruparReferencias(filas ?? [], texto), [filas, texto]);
  const fecha = filas
    ?.map((f) => f.consumidor?.fechaObservacionMasReciente ?? null)
    .filter((x): x is string => !!x)
    .sort()
    .at(-1);

  return (
    <section aria-labelledby="titulo-referencias">
      <h2 id="titulo-referencias" className="seccion">
        Precios referenciales de La Paz
      </h2>
      <p className="app__lema">El precio de la ciudad para cada producto, al consumidor y por mayor.</p>
      <p className="tenue">
        Sale de la fuente oficial (boletín de precios), sin el ajuste de ningún mercado. Es la referencia con que el sistema
        estima donde nadie midió todavía, y contra la que se dice si un mercado está más caro o más barato.
        {fecha && ` Dato más reciente: ${fecha}.`}
      </p>

      <div className="barra barra--directorio">
        <input
          className="barra__buscar"
          type="search"
          placeholder="Buscar un producto (papa, arroz, pollo…)"
          aria-label="Buscar un producto"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
        />
      </div>

      <MensajeError texto={error} />
      {!filas && !error && <p className="estado">Cargando los precios…</p>}
      {filas && grupos.length === 0 && <p className="estado">Ningún producto coincide.</p>}

      {grupos.map((g) => (
        <div key={g.categoria} className="tabla-envoltura referencias">
          <table className="tabla">
            <caption className="referencias__categoria">{nombreCategoria(g.categoria)}</caption>
            <thead>
              <tr>
                <th scope="col">Producto</th>
                <th scope="col">Al consumidor</th>
                <th scope="col">Por mayor</th>
              </tr>
            </thead>
            <tbody>
              {g.filas.map((f) => (
                <tr key={f.producto.codigo}>
                  <th scope="row">{f.producto.nombre}</th>
                  <td>
                    <Monto precio={f.consumidor} />
                  </td>
                  <td>
                    <Monto precio={f.mayorista} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </section>
  );
}

function Monto({ precio }: { precio: Precio | null }) {
  if (!precio) return <span className="tenue">sin dato</span>;
  return (
    <span className="referencias__monto">
      <strong>Bs {bs(precio.rango.centro)}</strong>
      <span className="tenue"> /{porUnidad(precio)}</span>
      {precio.rango.maximo > precio.rango.minimo && (
        <span className="tenue referencias__rango">
          {" "}
          ({bs(precio.rango.minimo)} a {bs(precio.rango.maximo)})
        </span>
      )}
    </span>
  );
}
