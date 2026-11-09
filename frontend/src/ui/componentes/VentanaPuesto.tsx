import { useEffect } from "react";

import {
  bs,
  dondeEsta,
  nombreCategoria,
  nombreDelPuesto,
  textoDisponibilidad,
  textoVence,
  type Mercado,
  type Oferta,
  type PuestoConInventario,
} from "@/dominio/modelo";
import { Icono } from "@/ui/componentes/Iconos";
import { hrefPuesto } from "@/ui/hooks/useRuta";

interface Props {
  readonly mercado: Mercado;
  readonly datos: PuestoConInventario;
  /** Las ofertas vigentes de ESTE puesto. */
  readonly ofertas: readonly Oferta[];
  /** El producto que se está buscando: va primero y resaltado. */
  readonly codigoProducto: string | null;
  readonly alCambiarTamano?: () => void;
}

/**
 * La ventana de un puesto, al tocar su rama en el mapa (C143): su foto, sus
 * ofertas vigentes y todo lo que tiene con precio y si le queda.
 */
export function VentanaPuesto({ mercado, datos, ofertas, codigoProducto, alCambiarTamano }: Props) {
  const { puesto, articulos } = datos;
  useEffect(() => alCambiarTamano?.(), [datos, ofertas, alCambiarTamano]);

  const ordenados = [...articulos].sort(
    (a, b) => Number(b.codigoProducto === codigoProducto) - Number(a.codigoProducto === codigoProducto),
  );
  const enOferta = new Set(ofertas.map((o) => o.codigoProducto));

  return (
    <div className="ventana ventana--puesto" aria-label={nombreDelPuesto(puesto)}>
      {puesto.foto ? (
        <img className="ventana__portada" src={puesto.foto} alt={`Foto de ${nombreDelPuesto(puesto)}`} />
      ) : (
        <span className="ventana__portada ventana__portada--vacia" aria-hidden="true">
          <Icono nombre="puesto" tamano={28} />
        </span>
      )}
      <header className="ventana__cabeza">
        <strong className="ventana__nombre">{nombreDelPuesto(puesto)}</strong>
        <span className="tenue">{dondeEsta(mercado, puesto)}</span>
        {puesto.referencia && <span className="tenue ventana__referencia">{puesto.referencia}</span>}
      </header>

      {ofertas.length > 0 && (
        <ul className="ventana__ofertas" aria-label="Ofertas de este puesto">
          {ofertas.map((o) => (
            <li key={o.id} className="ventana__oferta">
              <span className="ventana__oferta-cinta">★ −{Math.round(o.ahorroRelativo * 100)} %</span>
              <span className="ventana__oferta-producto">{o.nombreProducto}</span>
              <strong className="ventana__monto">
                Bs {bs(o.monto)}
                <span className="tenue">/{o.presentacion}</span>
              </strong>
              <span className="tenue ventana__oferta-nota">
                {o.nota ? `«${o.nota}» · ` : ""}
                {textoVence(o.hasta)}
              </span>
            </li>
          ))}
        </ul>
      )}

      {ordenados.length > 0 ? (
        <ul className="ventana__articulos ventana__articulos--todos">
          {ordenados.map((a) => (
            <li
              key={a.codigoProducto}
              className={[
                a.codigoProducto === codigoProducto ? "ventana__buscado" : "",
                a.disponibilidad === "agotado" ? "ventana__agotado" : "",
              ]
                .filter(Boolean)
                .join(" ") || undefined}
            >
              <span>
                {enOferta.has(a.codigoProducto) && (
                  <span className="ventana__estrella" aria-label="en oferta">
                    ★{" "}
                  </span>
                )}
                {a.nombreProducto}
              </span>
              <span className="ventana__monto">
                Bs {bs(a.monto)}
                <span className="tenue">/{a.presentacion}</span>
              </span>
              {a.disponibilidad !== "hay" && (
                <span className={`disponible disponible--${a.disponibilidad}`}>{textoDisponibilidad(a.disponibilidad)}</span>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="tenue ventana__estado">
          {puesto.rubros.length > 0 ? `Vende ${puesto.rubros.map(nombreCategoria).join(", ")}; ` : ""}
          todavía no cargó precios.
        </p>
      )}

      <a className="ventana__entrar" href={hrefPuesto(puesto.codigoMercado, puesto.numero)}>
        Ver su puesto completo
        <Icono nombre="flecha" tamano={14} />
      </a>
    </div>
  );
}
