import { useEffect, useState } from "react";

import {
  bs,
  etiquetaTipo,
  publicaRango,
  type MarcadorMapa,
  type Producto,
  type PuestosDeMercado,
} from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { Icono } from "@/ui/componentes/Iconos";
import { PlanoMercado } from "@/ui/componentes/PlanoMercado";
import { hrefMercado } from "@/ui/hooks/useRuta";

// En la ventana del mapa va el mercado en miniatura; el detalle de cada puesto, en la ficha.
const ARTICULOS_POR_PUESTO = 5;

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
  const conProducto = producto
    ? puestos.filter((p) => p.articulos.some((a) => a.codigoProducto === producto.codigo && a.disponibilidad !== "agotado")).length
    : 0;
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
        <>
          <p className="ventana__resumen">
            {puestos.length} {puestos.length === 1 ? "puesto" : "puestos"}
            {producto && conProducto > 0 && ` · ${conProducto} con ${producto.nombre.toLowerCase()}`}
          </p>
          <PlanoMercado
            compacto
            puestos={puestos.map((p) => ({ ...p, ofertas: [] }))}
            seleccionado={null}
            alElegir={(numero) => {
              location.hash = `#/mercado?codigo=${encodeURIComponent(mercado.codigo)}&puesto=${encodeURIComponent(numero)}`;
            }}
          />
        </>
      )}

      <a className="ventana__entrar" href={hrefMercado(mercado.codigo)}>
        {puestos.length > 0 ? "Entrar al mercado: sus puestos y precios" : "Entrar: todos los precios"}
        <Icono nombre="flecha" tamano={14} />
      </a>
    </div>
  );
}
