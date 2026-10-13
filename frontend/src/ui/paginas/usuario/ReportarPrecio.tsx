import { useState, type FormEvent } from "react";

import { presentacionBase } from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { SelectorProducto } from "@/ui/componentes/SelectorProducto";
import { useCatalogo } from "@/ui/hooks/useCatalogo";

/** Reportar un precio que se vio. Queda pendiente hasta que un administrador lo revisa. */
export function ReportarPrecio({ contenedor, alEnviar }: { contenedor: Contenedor; alEnviar: () => void }) {
  const { productos, mercados } = useCatalogo(contenedor);
  const [codigoProducto, setCodigoProducto] = useState("");
  const [codigoMercado, setCodigoMercado] = useState("");
  const [monto, setMonto] = useState("");
  const [presentacion, setPresentacion] = useState("");
  const [error, setError] = useState<string | null>(null);

  const producto = productos.find((p) => p.codigo === codigoProducto);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    if (!codigoProducto) {
      setError("Elija un producto de la lista");
      return;
    }
    try {
      await contenedor.reportarPrecio.reportar({
        codigoProducto,
        codigoMercado,
        monto: Number(monto),
        presentacion: presentacion || (producto ? presentacionBase(producto).codigo : ""),
      });
      alEnviar();
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  return (
    <form className="formulario formulario--recuadro" onSubmit={(e) => void enviar(e)} aria-label="Reportar un precio">
      <p className="tenue">
        Su reporte no se publica directo: un administrador lo revisa y, si lo aprueba, entra al cálculo como una
        observación más.
      </p>
      <div className="formulario__fila">
        <SelectorProducto
          productos={productos}
          valor={codigoProducto}
          etiqueta="Producto"
          onElegir={(codigo) => {
            setCodigoProducto(codigo);
            setPresentacion("");
          }}
        />
        <label className="campo">
          <span>Dónde lo vio</span>
          <select required value={codigoMercado} onChange={(e) => setCodigoMercado(e.target.value)}>
            <option value="">Elegir…</option>
            {mercados.map((m) => (
              <option key={m.codigo} value={m.codigo}>
                {m.nombre}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="formulario__fila">
        <label className="campo">
          <span>Precio (Bs)</span>
          <input required type="number" min={0} step="0.01" value={monto} onChange={(e) => setMonto(e.target.value)} />
        </label>
        <label className="campo">
          <span>Por</span>
          <select
            value={presentacion || (producto ? presentacionBase(producto).codigo : "")}
            disabled={!producto}
            onChange={(e) => setPresentacion(e.target.value)}
          >
            {producto?.presentaciones.map((p) => (
              <option key={p.codigo} value={p.codigo}>
                {p.nombre}
              </option>
            ))}
          </select>
        </label>
      </div>
      <MensajeError texto={error} />
      <div className="formulario__botones">
        <button type="submit" className="boton">
          Enviar reporte
        </button>
      </div>
    </form>
  );
}
