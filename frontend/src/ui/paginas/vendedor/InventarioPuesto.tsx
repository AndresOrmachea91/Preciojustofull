import { useCallback, useEffect, useState, type FormEvent } from "react";

import {
  DISPONIBILIDADES,
  bs,
  iconoProducto,
  nivelExistencia,
  presentacionBase,
  textoCantidad,
  type ArticuloInventario,
  type Disponibilidad,
  type Producto,
  type ReporteInventario,
  type SugerenciaPrecio,
} from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { MensajeAviso, MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { SelectorProducto } from "@/ui/componentes/SelectorProducto";

interface Cambios {
  monto?: number;
  disponibilidad?: Disponibilidad;
  cantidad?: number | null;
  minimo?: number | null;
}

/**
 * El inventario del puesto desde el celular (C137, C148). Arriba, cómo está el
 * puesto hoy y qué conviene hacer. En cada producto: cuánto le queda con
 * botones de «vendí» y «llegaron», el estado que se calcula solo y una
 * sugerencia de precio comparada con su mismo mercado.
 */
export function InventarioPuesto({ contenedor, productos }: { contenedor: Contenedor; productos: readonly Producto[] }) {
  const [articulos, setArticulos] = useState<ArticuloInventario[] | null>(null);
  const [reporte, setReporte] = useState<ReporteInventario | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const cargarReporte = useCallback(() => {
    // El reporte es una ayuda: si falla, el inventario igual se usa.
    contenedor.miPuesto.reporteInventario().then(setReporte, () => setReporte(null));
  }, [contenedor]);
  const cargar = useCallback(() => {
    contenedor.miPuesto.inventario().then(setArticulos, (e) => setError(textoDeError(e)));
    cargarReporte();
  }, [contenedor, cargarReporte]);
  useEffect(cargar, [cargar]);

  function reemplazar(nuevo: ArticuloInventario) {
    setArticulos((lista) => lista?.map((a) => (a.codigoProducto === nuevo.codigoProducto ? nuevo : a)) ?? null);
    cargarReporte();
  }

  async function guardar(articulo: ArticuloInventario, cambios: Cambios) {
    setError(null);
    setAviso(null);
    try {
      const nuevo = await contenedor.miPuesto.guardarArticulo({
        codigoProducto: articulo.codigoProducto,
        presentacion: articulo.presentacion,
        monto: cambios.monto ?? articulo.monto,
        disponibilidad: cambios.disponibilidad ?? articulo.disponibilidad,
        cantidad: cambios.cantidad !== undefined ? cambios.cantidad : articulo.cantidad,
        minimo: cambios.minimo !== undefined ? cambios.minimo : articulo.minimo,
      });
      reemplazar(nuevo);
      if (cambios.monto !== undefined) setAviso(`${nuevo.nombreProducto}: ahora a Bs ${bs(nuevo.monto)} por ${nuevo.presentacion}.`);
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  async function ajustar(articulo: ArticuloInventario, cambio: number) {
    setError(null);
    setAviso(null);
    try {
      const nuevo = await contenedor.miPuesto.ajustarCantidad(articulo.codigoProducto, cambio);
      reemplazar(nuevo);
      if (nuevo.disponibilidad === "agotado") setAviso(`${nuevo.nombreProducto} se acabó: los compradores ya lo ven agotado.`);
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
      cargarReporte();
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  const sugerencias = new Map(reporte?.renglones.map((r) => [r.articulo.codigoProducto, r]) ?? []);

  return (
    <div className="inventario">
      {reporte && reporte.productos > 0 && <ResumenDelPuesto reporte={reporte} />}

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
              sugerencia={sugerencias.get(a.codigoProducto)?.sugerencia ?? null}
              alertas={sugerencias.get(a.codigoProducto)?.alertas ?? []}
              alCambiar={(cambios) => void guardar(a, cambios)}
              alAjustar={(cambio) => void ajustar(a, cambio)}
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
          cargarReporte();
        }}
      />
    </div>
  );
}

/** Cómo está el puesto hoy, en cuatro números y dos o tres consejos. */
function ResumenDelPuesto({ reporte }: { reporte: ReporteInventario }) {
  return (
    <section className="resumen-puesto" aria-labelledby="titulo-resumen-puesto">
      <h3 id="titulo-resumen-puesto" className="resumen-puesto__titulo">
        Su puesto hoy
      </h3>
      <div className="resumen-puesto__cifras">
        <div className="resumen-puesto__cifra">
          <span className="resumen-puesto__valor">{reporte.productos}</span>
          <span>productos a la venta</span>
        </div>
        <div className="resumen-puesto__cifra">
          <span className="resumen-puesto__valor">{reporte.conCantidad > 0 ? `Bs ${bs(reporte.valorTotal)}` : "—"}</span>
          <span>{reporte.conCantidad > 0 ? "vale lo que le queda" : "anote cantidades para ver cuánto vale"}</span>
        </div>
        <div className={`resumen-puesto__cifra${reporte.agotados + reporte.quedaPoco > 0 ? " resumen-puesto__cifra--alerta" : ""}`}>
          <span className="resumen-puesto__valor">{reporte.agotados + reporte.quedaPoco}</span>
          <span>
            {reporte.agotados + reporte.quedaPoco === 0
              ? "nada se está acabando"
              : `${reporte.agotados > 0 ? `${reporte.agotados} agotados, ` : ""}${reporte.quedaPoco} ${reporte.quedaPoco === 1 ? "se acaba" : "se acaban"}`}
          </span>
        </div>
        <div className={`resumen-puesto__cifra${reporte.paraRevisarPrecio > 0 ? " resumen-puesto__cifra--aviso" : ""}`}>
          <span className="resumen-puesto__valor">{reporte.paraRevisarPrecio}</span>
          <span>precios para revisar</span>
        </div>
      </div>
      {reporte.consejos.length > 0 && (
        <ul className="resumen-puesto__consejos">
          {reporte.consejos.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

function FilaInventario({
  articulo,
  sugerencia,
  alertas,
  alCambiar,
  alAjustar,
  alQuitar,
}: {
  articulo: ArticuloInventario;
  sugerencia: SugerenciaPrecio | null;
  alertas: readonly string[];
  alCambiar: (cambios: Cambios) => void;
  alAjustar: (cambio: number) => void;
  alQuitar: () => void;
}) {
  const [editando, setEditando] = useState(false);
  const [monto, setMonto] = useState(bs(articulo.monto));
  const [anotando, setAnotando] = useState(false);
  const [cantidad, setCantidad] = useState(articulo.cantidad !== null ? String(articulo.cantidad) : "");
  const [minimo, setMinimo] = useState(articulo.minimo !== null ? String(articulo.minimo) : "");
  const titulo = articulo.nombreProducto;
  const nivel = nivelExistencia(articulo);
  const numero = (texto: string) => Number(texto.replace(",", "."));

  function confirmarPrecio(evento: FormEvent) {
    evento.preventDefault();
    const valor = numero(monto);
    if (valor > 0) alCambiar({ monto: valor });
    setEditando(false);
  }

  function confirmarCantidad(evento: FormEvent) {
    evento.preventDefault();
    const c = numero(cantidad);
    if (!(c >= 0)) return;
    const m = minimo.trim() === "" ? Math.max(1, Math.round(c / 4)) : numero(minimo);
    alCambiar({ cantidad: c, minimo: m >= 0 ? m : null });
    setAnotando(false);
  }

  return (
    <li className={`articulo articulo--${articulo.disponibilidad}`}>
      <div className="articulo__cabeza">
        <span className="articulo__dibujo" aria-hidden="true">
          {iconoProducto(articulo.codigoProducto, articulo.categoria)}
        </span>
        <div className="articulo__titulo">
          <strong className="articulo__nombre">{titulo}</strong>
          <span className={`estado-chip estado-chip--${articulo.disponibilidad}`}>
            {DISPONIBILIDADES.find((d) => d.valor === articulo.disponibilidad)?.texto}
          </span>
        </div>
        {editando ? (
          <form className="articulo__precio-form" onSubmit={confirmarPrecio}>
            <span className="tenue">Bs</span>
            <input autoFocus inputMode="decimal" aria-label={`Nuevo precio de ${titulo}`} value={monto} onChange={(e) => setMonto(e.target.value)} />
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
              setMonto(bs(articulo.monto));
              setEditando(true);
            }}
          >
            Bs {bs(articulo.monto)} <span className="tenue">/{articulo.presentacion}</span>
          </button>
        )}
      </div>

      {articulo.cantidad !== null && !anotando ? (
        <div className="existencias">
          <div className="existencias__texto">
            <span>
              Le quedan <strong>{textoCantidad(articulo.cantidad, articulo.presentacion)}</strong>
            </span>
            <button type="button" className="enlace" onClick={() => setAnotando(true)}>
              Corregir
            </button>
          </div>
          {nivel !== null && (
            <span className="existencia existencia--grande" aria-hidden="true">
              <span className="existencia__barra" style={{ width: `${Math.round(nivel * 100)}%` }} />
              {articulo.minimo !== null && <span className="existencia__aviso" title="Desde aquí le avisa" />}
            </span>
          )}
          <div className="existencias__botones" role="group" aria-label={`Cambiar cuánto le queda de ${titulo}`}>
            <button type="button" className="boton boton--suave" onClick={() => alAjustar(-1)} disabled={articulo.cantidad <= 0}>
              Vendí 1
            </button>
            <button type="button" className="boton boton--suave" onClick={() => alAjustar(-5)} disabled={articulo.cantidad <= 0}>
              Vendí 5
            </button>
            <button type="button" className="boton boton--suave existencias__llego" onClick={() => alAjustar(10)}>
              Llegaron 10
            </button>
          </div>
        </div>
      ) : anotando || articulo.cantidad === null ? (
        anotando ? (
          <form className="existencias existencias--form" onSubmit={confirmarCantidad}>
            <label className="campo">
              <span>¿Cuánto le queda? ({articulo.presentacion})</span>
              <input autoFocus inputMode="decimal" value={cantidad} onChange={(e) => setCantidad(e.target.value)} placeholder="12" />
            </label>
            <label className="campo">
              <span>Avisarme cuando queden</span>
              <input inputMode="decimal" value={minimo} onChange={(e) => setMinimo(e.target.value)} placeholder="3" />
            </label>
            <div className="formulario__botones">
              <button type="submit" className="boton boton--chico">
                Guardar
              </button>
              <button type="button" className="boton boton--suave boton--chico" onClick={() => setAnotando(false)}>
                Cancelar
              </button>
            </div>
          </form>
        ) : (
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
            <button type="button" className="enlace" onClick={() => setAnotando(true)}>
              Anotar cuánto me queda
            </button>
          </div>
        )
      ) : null}

      {sugerencia && sugerencia.tipo !== "sin_referencia" && (
        <div className={`sugerencia sugerencia--${sugerencia.tipo}`}>
          <span className="sugerencia__icono" aria-hidden="true">
            {sugerencia.tipo === "bajar" ? "↓" : sugerencia.tipo === "subir" ? "↑" : "✓"}
          </span>
          <span className="sugerencia__texto">
            {sugerencia.texto}
            {sugerencia.precioMercado !== null && (
              <span className="tenue"> En su mercado: Bs {bs(sugerencia.precioMercado)}.</span>
            )}
          </span>
          {sugerencia.precioSugerido !== null && sugerencia.precioSugerido !== articulo.monto && (
            <button type="button" className="boton boton--chico" onClick={() => alCambiar({ monto: sugerencia.precioSugerido! })}>
              Usar Bs {bs(sugerencia.precioSugerido)}
            </button>
          )}
        </div>
      )}
      {alertas
        .filter((a) => a.startsWith("No lo actualiza"))
        .map((a) => (
          <p key={a} className="articulo__alerta">
            {a}
          </p>
        ))}

      <div className="articulo__final">
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
  const [cantidad, setCantidad] = useState("");
  const [error, setError] = useState<string | null>(null);
  const producto = productos.find((p) => p.codigo === codigoProducto);
  const presentacionElegida = presentacion || (producto ? presentacionBase(producto).codigo : "");
  const nombrePresentacion = producto?.presentaciones.find((p) => p.codigo === presentacionElegida)?.nombre.toLowerCase() ?? "";

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    const c = cantidad.trim() === "" ? null : Number(cantidad.replace(",", "."));
    try {
      const nuevo = await contenedor.miPuesto.guardarArticulo({
        codigoProducto,
        presentacion: presentacionElegida,
        monto: Number(monto.replace(",", ".")),
        disponibilidad: "hay",
        cantidad: c,
        minimo: c === null ? null : Math.max(1, Math.round(c / 4)),
      });
      alAgregar(nuevo);
      setCodigoProducto("");
      setPresentacion("");
      setMonto("");
      setCantidad("");
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
        <label className="campo">
          <span>¿Cuánto tiene?{nombrePresentacion && ` (${nombrePresentacion})`}</span>
          <input inputMode="decimal" value={cantidad} onChange={(e) => setCantidad(e.target.value)} placeholder="opcional" />
        </label>
      </div>
      <p className="tenue">Si anota cuánto tiene, el sistema le avisa cuando se esté acabando.</p>
      <MensajeError texto={error} />
      <div className="formulario__botones">
        <button type="submit" className="boton" disabled={!codigoProducto}>
          Agregar a mi puesto
        </button>
      </div>
    </form>
  );
}
