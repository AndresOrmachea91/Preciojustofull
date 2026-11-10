import { useEffect, useState } from "react";

import {
  bs,
  etiquetaTipo,
  nombreCategoria,
  nombreDelPuesto,
  publicaRango,
  textoDisponibilidad,
  type MarcadorMapa,
  type Producto,
  type PuestosDeMercado,
} from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { Icono } from "@/ui/componentes/Iconos";
import { ContactoPuesto } from "@/ui/componentes/ContactoPuesto";
import { hrefMercado } from "@/ui/hooks/useRuta";

// En la ventana del mapa entra poco: unos puestos con unos precios. El resto, en la ficha.
const PUESTOS_EN_VENTANA = 3;
const ARTICULOS_POR_PUESTO = 3;

interface Props {
  readonly contenedor: Contenedor;
  readonly marcador: MarcadorMapa;
  readonly producto: Producto | null;
  /** Avisa que cambió el tamaño del contenido, para que el mapa acomode la ventana. */
  readonly alCambiarTamano?: () => void;
}

/**
 * La ventana que se abre al tocar un mercado en el mapa (C137): el precio
 * del producto elegido y sus puestos, con foto y lo que tiene cada uno.
 * No todos los mercados venden lo mismo: cada puesto muestra SU inventario,
 * y primero van los que tienen el producto que se está buscando.
 */
export function VentanaMercado({ contenedor, marcador, producto, alCambiarTamano }: Props) {
  const { mercado, precio } = marcador;
  const [datos, setDatos] = useState<PuestosDeMercado | null>(null);
  const [fallo, setFallo] = useState(false);

  useEffect(() => {
    let vigente = true;
    setDatos(null);
    setFallo(false);
    contenedor.mercados
      .puestos(mercado.codigo, { producto: producto?.codigo, articulos: ARTICULOS_POR_PUESTO })
      .then(
        (d) => vigente && setDatos(d),
        () => vigente && setFallo(true),
      );
    return () => {
      vigente = false;
    };
  }, [contenedor, mercado.codigo, producto?.codigo]);

  useEffect(() => alCambiarTamano?.(), [datos, fallo, alCambiarTamano]);

  const puestos = datos?.puestos ?? [];
  return (
    <div className="ventana" aria-label={`Puestos de ${mercado.nombre}`}>
      <header className="ventana__cabeza">
        <strong className="ventana__nombre">{mercado.nombre}</strong>
        <span className="tenue">
          {etiquetaTipo(mercado.tipo)}
          {mercado.macrodistrito && ` · ${mercado.macrodistrito}`}
        </span>
      </header>

      {precio && producto && (
        <p className={`ventana__precio ventana__precio--${precio.procedencia}`}>
          <span>{producto.nombre}</span>
          <strong>
            {publicaRango(mercado.tipo)
              ? `Bs ${bs(precio.rango.minimo)} a ${bs(precio.rango.maximo)}`
              : `Bs ${bs(precio.rango.centro)}`}
            <span className="tenue"> /{precio.unidad}</span>
          </strong>
          <span className="tenue">{precio.procedencia === "observado" ? "medido aquí" : "estimado"}</span>
        </p>
      )}

      {!datos && !fallo && <p className="tenue ventana__estado">Buscando sus puestos…</p>}
      {fallo && <p className="tenue ventana__estado">No se pudieron cargar los puestos.</p>}
      {datos && puestos.length === 0 && (
        <p className="ventana__estado">
          Todavía ningún casero de aquí cargó su puesto. <a href="#/registrarse">¿Vende aquí? Regístrese gratis</a>
        </p>
      )}

      {puestos.length > 0 && (
        <ul className="ventana__puestos">
          {puestos.slice(0, PUESTOS_EN_VENTANA).map(({ puesto, articulos, total }) => (
            <li key={`${puesto.codigoMercado}-${puesto.numero}`} className="ventana__puesto">
              {puesto.foto ? (
                <img className="ventana__foto" src={puesto.foto} alt="" loading="lazy" />
              ) : (
                <span className="ventana__foto ventana__foto--vacia" aria-hidden="true">
                  {puesto.esLocal ? <Icono nombre="caja" tamano={18} /> : puesto.numero}
                </span>
              )}
              <div className="ventana__detalle">
                <strong>{nombreDelPuesto(puesto)}</strong>
                <ContactoPuesto puesto={puesto} />
                {articulos.length > 0 ? (
                  <ul className="ventana__articulos">
                    {articulos.map((a) => (
                      <li key={a.codigoProducto} className={a.disponibilidad === "agotado" ? "ventana__agotado" : undefined}>
                        <span>{a.nombreProducto}</span>
                        <span className="ventana__monto">
                          Bs {bs(a.monto)}
                          <span className="tenue">/{a.presentacion}</span>
                        </span>
                        {a.disponibilidad !== "hay" && (
                          <span className={`disponible disponible--${a.disponibilidad}`}>{textoDisponibilidad(a.disponibilidad)}</span>
                        )}
                      </li>
                    ))}
                    {total > articulos.length && <li className="tenue">y {total - articulos.length} más</li>}
                  </ul>
                ) : (
                  <span className="tenue">
                    {puesto.rubros.length > 0 ? puesto.rubros.map(nombreCategoria).join(", ") : "Sin precios cargados"}
                  </span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      <a className="ventana__entrar" href={hrefMercado(mercado.codigo)}>
        {puestos.length > PUESTOS_EN_VENTANA
          ? `Ver los ${puestos.length} puestos y todos los precios`
          : "Entrar: todos los precios y puestos"}
        <Icono nombre="flecha" tamano={14} />
      </a>
    </div>
  );
}
