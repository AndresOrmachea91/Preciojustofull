import { useCallback, useEffect, useState, type FormEvent } from "react";

import {
  DISPONIBILIDADES,
  bs,
  presentacionBase,
  type ArticuloInventario,
  type Disponibilidad,
  type Producto,
} from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { MensajeAviso, MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { SelectorProducto } from "@/ui/componentes/SelectorProducto";

/**
 * El inventario del puesto desde el celular (C137). Lo que más se usa va a
 * un toque: "hay / queda poco / se acabó". Cambiar el precio es tocar el
 * número. Si el precio cambia, se publica como declarado por el vendedor.
 */
export function InventarioPuesto({ contenedor, productos }: { contenedor: Contenedor; productos: readonly Producto[] }) {
  const [articulos, setArticulos] = useState<ArticuloInventario[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const cargar = useCallback(() => {
    contenedor.miPuesto.inventario().then(setArticulos, (e) => setError(textoDeError(e)));
  }, [contenedor]);
  useEffect(cargar, [cargar]);

  async function guardar(articulo: ArticuloInventario, cambios: { monto?: number; disponibilidad?: Disponibilidad }) {
    setError(null);
    setAviso(null);
    try {
      const nuevo = await contenedor.miPuesto.guardarArticulo({
        codigoProducto: articulo.codigoProducto,
        presentacion: articulo.presentacion,
        monto: cambios.monto ?? articulo.monto,
        disponibilidad: cambios.disponibilidad ?? articulo.disponibilidad,
      });
      setArticulos((lista) => lista?.map((a) => (a.codigoProducto === nuevo.codigoProducto ? nuevo : a)) ?? null);
      if (cambios.monto !== undefined) setAviso(`${nuevo.nombreProducto}: Bs ${bs(nuevo.monto)} por ${nuevo.presentacion}.`);
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  async function quitar(articulo: ArticuloInventario) {
    setError(null);
    try {
      await contenedor.miPuesto.quitarArticulo(articulo.codigoProducto);
      setArticulos((lista) => lista?.filter((a) => a.codigoProducto !== articulo.codigoProducto) ?? null);
      setAviso(`${articulo.nombreProducto} ya no aparece en su puesto.`);
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  return (
    <div className="inventario">
      <p className="tenue">
        Lo que tiene hoy y a cuánto. Los compradores lo ven en el mapa al tocar su mercado. Cambiar el precio lo publica
        como <strong>declarado por el vendedor</strong>.
      </p>

      <MensajeError texto={error} />
      <MensajeAviso texto={aviso} />

      {!articulos && !error && <p className="estado">Cargando su inventario…</p>}
      {articulos && articulos.length === 0 && (
        <p className="estado">Todavía no cargó productos. Agregue lo que vende: con dos o tres ya aparece en el mapa.</p>
      )}
      {articulos && articulos.length > 0 && (
        <ul className="inventario__lista" aria-label="Mi inventario">
          {articulos.map((a) => (
            <FilaInventario
              key={a.codigoProducto}
              articulo={a}
              alCambiar={(cambios) => void guardar(a, cambios)}
              alQuitar={() => void quitar(a)}
            />
          ))}
        </ul>
      )}

      <AgregarArticulo
        contenedor={contenedor}
        productos={productos.filter((p) => !articulos?.some((a) => a.codigoProducto === p.codigo))}
        alAgregar={(nuevo) => {
          setArticulos((lista) => [...(lista ?? []), nuevo].sort((x, y) => x.nombreProducto.localeCompare(y.nombreProducto)));
          setAviso(`Agregado: ${nuevo.nombreProducto} a Bs ${bs(nuevo.monto)} por ${nuevo.presentacion}.`);
        }}
      />
    </div>
  );
}

function FilaInventario({
  articulo,
  alCambiar,
  alQuitar,
}: {
  articulo: ArticuloInventario;
  alCambiar: (cambios: { monto?: number; disponibilidad?: Disponibilidad }) => void;
  alQuitar: () => void;
}) {
  const [editando, setEditando] = useState(false);
  const [monto, setMonto] = useState(articulo.monto.toFixed(2));
  const titulo = articulo.nombreProducto;

  function confirmar(evento: FormEvent) {
    evento.preventDefault();
    const valor = Number(monto.replace(",", "."));
    if (valor > 0) alCambiar({ monto: valor });
    setEditando(false);
  }

  return (
    <li className={`articulo articulo--${articulo.disponibilidad}`}>
      <div className="articulo__cabeza">
        <strong className="articulo__nombre">{titulo}</strong>
        {editando ? (
          <form className="articulo__precio-form" onSubmit={confirmar}>
            <span className="tenue">Bs</span>
            <input
              autoFocus
              inputMode="decimal"
              aria-label={`Nuevo precio de ${titulo}`}
              value={monto}
              onChange={(e) => setMonto(e.target.value)}
            />
            <button type="submit" className="boton boton--chico">
              Listo
            </button>
          </form>
        ) : (
          <button
            type="button"
            className="articulo__precio"
            aria-label={`Precio de ${titulo}: Bs ${bs(articulo.monto)} por ${articulo.presentacion}. Tocar para cambiar`}
            onClick={() => {
              setMonto(articulo.monto.toFixed(2));
              setEditando(true);
            }}
          >
            Bs {bs(articulo.monto)} <span className="tenue">/{articulo.presentacion}</span>
          </button>
        )}
      </div>
      <div className="articulo__pie">
        <div className="segmentado segmentado--chico" role="group" aria-label={`¿Le queda ${titulo}?`}>
          {DISPONIBILIDADES.map((d) => (
            <button
              key={d.valor}
              type="button"
              className={`segmentado__opcion disponibilidad--${d.valor}`}
              aria-pressed={articulo.disponibilidad === d.valor}
              onClick={() => articulo.disponibilidad !== d.valor && alCambiar({ disponibilidad: d.valor })}
            >
              {d.texto}
            </button>
          ))}
        </div>
        <button type="button" className="enlace articulo__quitar" onClick={alQuitar}>
          Ya no lo vendo
        </button>
      </div>
    </li>
  );
}

function AgregarArticulo({
  contenedor,
  productos,
  alAgregar,
}: {
  contenedor: Contenedor;
  productos: readonly Producto[];
  alAgregar: (a: ArticuloInventario) => void;
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
      const nuevo = await contenedor.miPuesto.guardarArticulo({
        codigoProducto,
        presentacion: presentacionElegida,
        monto: Number(monto.replace(",", ".")),
        disponibilidad: "hay",
      });
      alAgregar(nuevo);
      setCodigoProducto("");
      setPresentacion("");
      setMonto("");
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  return (
    <form className="formulario formulario--recuadro" onSubmit={(e) => void enviar(e)} aria-label="Agregar un producto">
      <h3 className="subseccion">Agregar un producto</h3>
      <SelectorProducto
        productos={productos}
        valor={codigoProducto}
        etiqueta="Producto"
        onElegir={(codigo) => {
          setCodigoProducto(codigo);
          setPresentacion("");
        }}
      />
      <div className="formulario__fila">
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
          <input required inputMode="decimal" value={monto} onChange={(e) => setMonto(e.target.value)} placeholder="12,50" />
        </label>
      </div>
      <MensajeError texto={error} />
      <div className="formulario__botones">
        <button type="submit" className="boton" disabled={!codigoProducto}>
          Agregar a mi puesto
        </button>
      </div>
    </form>
  );
}
