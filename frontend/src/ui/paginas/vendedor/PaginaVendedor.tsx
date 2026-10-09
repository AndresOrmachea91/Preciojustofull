import { useCallback, useEffect, useState, type FormEvent } from "react";

import {
  NOMBRE_UNIDAD_BASE,
  presentacionBase,
  type PrecioPublicado,
  type Producto,
  type Usuario,
} from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { MensajeAviso, MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { useCatalogo } from "@/ui/hooks/useCatalogo";

/** El vendedor publica los precios de su puesto y ve lo último que publicó. */
export function PaginaVendedor({ contenedor, vendedor }: { contenedor: Contenedor; vendedor: Usuario }) {
  const { productos, mercados } = useCatalogo(contenedor);
  const [precios, setPrecios] = useState<PrecioPublicado[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const puesto = mercados.find((m) => m.codigo === vendedor.codigoPuntoVenta);

  const cargar = useCallback(() => {
    contenedor.miPuesto.misPrecios().then(setPrecios, (e) => setError(textoDeError(e)));
  }, [contenedor]);
  useEffect(() => {
    if (vendedor.codigoPuntoVenta) cargar();
  }, [cargar, vendedor.codigoPuntoVenta]);

  if (!vendedor.codigoPuntoVenta) {
    return (
      <section className="estado" aria-labelledby="titulo-puesto">
        <h2 id="titulo-puesto" className="seccion">
          Mi puesto
        </h2>
        <p>Todavía no tiene un puesto asignado. Pídale al administrador que se lo asigne para publicar sus precios.</p>
      </section>
    );
  }

  return (
    <section aria-labelledby="titulo-puesto">
      <h2 id="titulo-puesto" className="seccion">
        Mi puesto{puesto && <span className="tenue"> · {puesto.nombre}</span>}
      </h2>
      <p className="tenue">
        Lo que publique se muestra al instante como <strong>declarado por el vendedor</strong>: el sistema lo compara
        con el boletín oficial y con lo que se mide en el mercado.
      </p>

      <FormularioPrecio
        contenedor={contenedor}
        productos={productos}
        alPublicar={(texto) => {
          setError(null);
          setAviso(texto);
          cargar();
        }}
      />

      <MensajeError texto={error} />
      <MensajeAviso texto={aviso} />

      <h3 className="subseccion">Mis precios publicados</h3>
      {!precios && !error && <p className="estado">Cargando sus precios…</p>}
      {precios && precios.length === 0 && <p className="estado">Todavía no publicó precios.</p>}
      {precios && precios.length > 0 && (
        <div className="tabla-envoltura">
          <table className="tabla" aria-label="Mis precios publicados">
            <thead>
              <tr>
                <th>Producto</th>
                <th>Precio</th>
                <th>Equivale a</th>
                <th>Publicado</th>
              </tr>
            </thead>
            <tbody>
              {precios.map((p) => (
                <tr key={p.codigoProducto}>
                  <td>{p.nombreProducto}</td>
                  <td>
                    Bs {p.monto.toFixed(2)} <span className="tenue">por {p.presentacion}</span>
                  </td>
                  <td className="tenue">
                    Bs {p.precioPorUnidadBase.toFixed(2)} por {NOMBRE_UNIDAD_BASE[p.unidadBase].toLowerCase()}
                  </td>
                  <td className="tenue">{new Date(p.publicadoEn).toLocaleDateString("es-BO")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function FormularioPrecio({
  contenedor,
  productos,
  alPublicar,
}: {
  contenedor: Contenedor;
  productos: readonly Producto[];
  alPublicar: (texto: string) => void;
}) {
  const [codigoProducto, setCodigoProducto] = useState("");
  const [presentacion, setPresentacion] = useState("");
  const [monto, setMonto] = useState("");
  const [error, setError] = useState<string | null>(null);
  const producto = productos.find((p) => p.codigo === codigoProducto);
  const presentacionElegida = presentacion || (producto ? presentacionBase(producto).codigo : "");

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    try {
      await contenedor.miPuesto.publicar({ codigoProducto, monto: Number(monto), presentacion: presentacionElegida });
      alPublicar(`Publicado: ${producto?.nombre} a Bs ${Number(monto).toFixed(2)} por ${presentacionElegida}.`);
      setMonto("");
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  return (
    <form className="formulario formulario--recuadro" onSubmit={(e) => void enviar(e)} aria-label="Publicar un precio">
      <div className="formulario__fila formulario__fila--tres">
        <label className="campo">
          <span>Producto</span>
          <select
            required
            value={codigoProducto}
            onChange={(e) => {
              setCodigoProducto(e.target.value);
              setPresentacion("");
            }}
          >
            <option value="">Elegir…</option>
            {productos.map((p) => (
              <option key={p.codigo} value={p.codigo}>
                {p.nombre}
              </option>
            ))}
          </select>
        </label>
        <label className="campo">
          <span>Por</span>
          <select value={presentacionElegida} disabled={!producto} onChange={(e) => setPresentacion(e.target.value)}>
            {producto?.presentaciones.map((p) => (
              <option key={p.codigo} value={p.codigo}>
                {p.nombre}
              </option>
            ))}
          </select>
        </label>
        <label className="campo">
          <span>Precio (Bs)</span>
          <input required type="number" min={0} step="0.01" value={monto} onChange={(e) => setMonto(e.target.value)} />
        </label>
      </div>
      <MensajeError texto={error} />
      <div className="formulario__botones">
        <button type="submit" className="boton">
          Publicar precio
        </button>
      </div>
    </form>
  );
}
