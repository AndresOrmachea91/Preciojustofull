import { useCallback, useEffect, useState, type FormEvent } from "react";

import type { CotizacionLista } from "@/aplicacion/casosUso/usuario/listasCompras";
import {
  bs,
  describirItem,
  ofertasParaLista,
  presentacionBase,
  textoVence,
  tituloPuesto,
  type Oferta,
  type CostoCanasta,
  type ItemLista,
  type ListaCompras,
  type Producto,
} from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { MensajeAviso, MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { SelectorProducto } from "@/ui/componentes/SelectorProducto";
import { useCatalogo } from "@/ui/hooks/useCatalogo";
import { hrefMercado } from "@/ui/hooks/useRuta";

/** Las listas de compras: armarlas y ver en qué mercado sale más barata cada una. */
export function MisListas({ contenedor }: { contenedor: Contenedor }) {
  const { productos } = useCatalogo(contenedor);
  const [listas, setListas] = useState<ListaCompras[] | null>(null);
  const [editando, setEditando] = useState<ListaCompras | "nueva" | null>(null);
  const [cotizando, setCotizando] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const cargar = useCallback(() => {
    contenedor.listas.listas().then(setListas, (e) => setError(textoDeError(e)));
  }, [contenedor]);
  useEffect(cargar, [cargar]);

  async function eliminar(lista: ListaCompras) {
    setError(null);
    try {
      await contenedor.listas.eliminar(lista.id);
      setAviso(`Se eliminó «${lista.nombre}».`);
      if (cotizando === lista.id) setCotizando(null);
      cargar();
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  if (editando) {
    return (
      <FormularioLista
        contenedor={contenedor}
        productos={productos}
        lista={editando === "nueva" ? null : editando}
        alTerminar={(guardada) => {
          setEditando(null);
          if (guardada) {
            setAviso(`«${guardada.nombre}» quedó guardada.`);
            cargar();
          }
        }}
      />
    );
  }

  return (
    <>
      <p className="tenue">
        Arme su lista con las cantidades que compra («2 arrobas de papa, 1 quintal de arroz») y vea en qué mercado
        le sale más barata completa.
      </p>
      <button type="button" className="boton" onClick={() => setEditando("nueva")}>
        Nueva lista
      </button>
      <MensajeError texto={error} />
      <MensajeAviso texto={aviso} />
      {!listas && !error && <p className="estado">Cargando sus listas…</p>}
      {listas && listas.length === 0 && <p className="estado">Todavía no tiene listas.</p>}

      <div className="lista">
        {listas?.map((l) => (
          <article key={l.id} className="tarjeta" aria-label={`Lista ${l.nombre}`}>
            <div className="tarjeta__cabecera">
              <div>
                <h3 className="tarjeta__nombre">{l.nombre}</h3>
                <p className="tarjeta__zona">
                  {l.items.length === 1 ? "1 producto" : `${l.items.length} productos`}
                </p>
              </div>
              <div className="formulario__botones">
                <button type="button" className="boton" onClick={() => setCotizando(cotizando === l.id ? null : l.id)}>
                  {cotizando === l.id ? "Ocultar precios" : "¿Dónde conviene?"}
                </button>
                <button type="button" className="boton boton--suave" onClick={() => setEditando(l)}>
                  Editar
                </button>
                <button
                  type="button"
                  className="boton boton--suave"
                  aria-label={`Eliminar ${l.nombre}`}
                  onClick={() => void eliminar(l)}
                >
                  Eliminar
                </button>
              </div>
            </div>
            <ul className="renglones">
              {l.items.map((i) => (
                <li key={i.codigoProducto}>{describirItem(i, productos.find((p) => p.codigo === i.codigoProducto))}</li>
              ))}
            </ul>
            {cotizando === l.id && <Cotizacion contenedor={contenedor} lista={l} productos={productos} />}
          </article>
        ))}
      </div>
    </>
  );
}

function Cotizacion({ contenedor, lista, productos }: { contenedor: Contenedor; lista: ListaCompras; productos: Producto[] }) {
  const [resultado, setResultado] = useState<CotizacionLista | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    contenedor.listas.cotizar(lista.id).then(setResultado, (e) => setError(textoDeError(e)));
  }, [contenedor, lista]);

  if (error) return <MensajeError texto={error} />;
  if (!resultado) return <p className="estado">Cotizando…</p>;
  const { minoristas, mayoristas } = resultado;
  if (minoristas.opciones.length === 0 && mayoristas.length === 0) {
    return <p className="estado">No hay precios para estos productos todavía.</p>;
  }
  const nombre = (codigo: string) => productos.find((p) => p.codigo === codigo)?.nombre ?? codigo;

  return (
    <div className="cotizacion" aria-label="Dónde conviene comprar esta lista">
      <ResumenAhorro resultado={minoristas} />
      <OfertasDeLaLista contenedor={contenedor} lista={lista} productos={productos} />
      <Ranking costos={minoristas.opciones.slice(0, 5)} nombre={nombre} />
      {mayoristas.length > 0 && (
        <>
          <h4 className="subseccion">Precio mayorista</h4>
          <p className="tenue">Es otro nivel de la cadena: se compra por bulto, para revender. No compite con los de arriba.</p>
          <Ranking costos={mayoristas} nombre={nombre} etiqueta="Precio mayorista de esta lista" />
        </>
      )}
      <p className="tenue">
        «Estimado» quiere decir que nadie midió ese precio en ese lugar: sale de la referencia oficial de la ciudad.
        Sirve para comparar lugares entre sí, no es una cuenta exacta.
      </p>
    </div>
  );
}

function Ranking({
  costos,
  nombre,
  etiqueta,
}: {
  costos: readonly CostoCanasta[];
  nombre: (codigo: string) => string;
  etiqueta?: string;
}) {
  return (
    <ol className="ranking" aria-label={etiqueta}>
      {costos.map((c) => (
        <li key={c.codigoMercado} className="ranking__fila">
          <span>
            <strong>{c.nombreMercado}</strong>
            <span className="tenue"> · {c.zona}</span>
            {c.productosEstimados > 0 && (
              <span className="ranking__estimados">
                {" "}
                · {c.productosEstimados === c.productosCubiertos ? "todo estimado" : `${c.productosEstimados} de ${c.productosCubiertos} estimados`}
              </span>
            )}
            {c.faltantes.length > 0 && (
              <span className="ranking__faltan"> · sin precio de {c.faltantes.map(nombre).join(", ")}</span>
            )}
          </span>
          <span className="ranking__total">Bs {c.costoTotal.toFixed(2)}</span>
        </li>
      ))}
    </ol>
  );
}

function FormularioLista({
  contenedor,
  productos,
  lista,
  alTerminar,
}: {
  contenedor: Contenedor;
  productos: Producto[];
  lista: ListaCompras | null;
  alTerminar: (guardada: ListaCompras | null) => void;
}) {
  const [nombre, setNombre] = useState(lista?.nombre ?? "");
  const [items, setItems] = useState<ItemLista[]>(lista ? [...lista.items] : []);
  const [error, setError] = useState<string | null>(null);

  const disponibles = productos.filter((p) => !items.some((i) => i.codigoProducto === p.codigo));

  function agregar(codigo: string) {
    const producto = productos.find((p) => p.codigo === codigo);
    if (!producto) return;
    setItems([...items, { codigoProducto: codigo, cantidad: 1, presentacion: presentacionBase(producto).codigo }]);
  }

  function cambiar(indice: number, parcial: Partial<ItemLista>) {
    setItems(items.map((i, n) => (n === indice ? { ...i, ...parcial } : i)));
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    try {
      alTerminar(await contenedor.listas.guardar(lista?.id ?? null, nombre, items));
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  return (
    <form
      className="formulario formulario--recuadro"
      onSubmit={(e) => void enviar(e)}
      aria-label={lista ? "Editar lista" : "Nueva lista"}
    >
      <label className="campo">
        <span>Nombre de la lista</span>
        <input required value={nombre} placeholder="Compra del mes" onChange={(e) => setNombre(e.target.value)} />
      </label>

      {items.length > 0 && (
        <ul className="renglones renglones--editables">
          {items.map((item, n) => {
            const producto = productos.find((p) => p.codigo === item.codigoProducto);
            return (
              <li key={item.codigoProducto} className="renglon">
                <span className="renglon__producto">{producto?.nombre ?? item.codigoProducto}</span>
                <input
                  type="number"
                  min={0}
                  step="any"
                  aria-label={`Cantidad de ${producto?.nombre ?? item.codigoProducto}`}
                  value={item.cantidad}
                  onChange={(e) => cambiar(n, { cantidad: Number(e.target.value) })}
                />
                <select
                  aria-label={`Presentación de ${producto?.nombre ?? item.codigoProducto}`}
                  value={item.presentacion}
                  onChange={(e) => cambiar(n, { presentacion: e.target.value })}
                >
                  {producto?.presentaciones.map((p) => (
                    <option key={p.codigo} value={p.codigo}>
                      {p.nombre}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="boton boton--suave"
                  aria-label={`Quitar ${producto?.nombre ?? item.codigoProducto}`}
                  onClick={() => setItems(items.filter((_, m) => m !== n))}
                >
                  Quitar
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <SelectorProducto
        productos={disponibles}
        valor={null}
        etiqueta="Agregar un producto"
        ayuda="Busque y elija: se suma a la lista con cantidad 1."
        limpiarAlElegir
        onElegir={agregar}
      />

      <MensajeError texto={error} />
      <div className="formulario__botones">
        <button type="submit" className="boton">
          {lista ? "Guardar cambios" : "Crear lista"}
        </button>
        <button type="button" className="boton boton--suave" onClick={() => alTerminar(null)}>
          Cancelar
        </button>
      </div>
    </form>
  );
}

/**
 * La frase que importa: cuánto se ahorra y dónde (C129). Si el más barato
 * no se distingue de otros con el margen de error, se dice que empatan en
 * vez de inventar un ganador; y se avisa cuántos precios son estimados.
 */
function ResumenAhorro({ resultado }: { resultado: CotizacionLista["minoristas"] }) {
  const { masBarato: mejor, masCaro, ahorro, empatanConElMejor } = resultado;
  if (!mejor || !masCaro || ahorro <= 0) return null;
  const empatados = [mejor, ...empatanConElMejor].map((c) => c.nombreMercado);
  const estimados = mejor.productosEstimados;
  return (
    <div className="ahorro ahorro--resumen">
      {empatanConElMejor.length === 0 ? (
        <p>
          Ahorra <strong>Bs {ahorro.toFixed(2)}</strong> yendo a <strong>{mejor.nombreMercado}</strong> (Bs{" "}
          {mejor.costoTotal.toFixed(2)}) en vez de {masCaro.nombreMercado} (Bs {masCaro.costoTotal.toFixed(2)}).
        </p>
      ) : (
        <p>
          <strong>{empatados.join(", ")}</strong> empatan: la diferencia entre ellos es menor que el margen de error.
          Cualquiera de ellos ahorra hasta <strong>Bs {ahorro.toFixed(2)}</strong> frente a {masCaro.nombreMercado}.
        </p>
      )}
      {estimados > 0 && (
        <p className="tenue">
          {estimados === mejor.productosCubiertos
            ? "Todos los precios de ese lugar son estimados: tómelo como una guía para comparar, no como una cuenta exacta."
            : `${estimados} de ${mejor.productosCubiertos} precios de ese lugar son estimados.`}
        </p>
      )}
    </div>
  );
}

/**
 * Las ofertas de los caseros que tocan esta lista (C133, F4): "su tomate
 * está en oferta en el puesto 14 del Rodríguez". El ahorro es contra el
 * precio del sistema en ese mercado, por la cantidad que pide la lista.
 */
function OfertasDeLaLista({ contenedor, lista, productos }: { contenedor: Contenedor; lista: ListaCompras; productos: Producto[] }) {
  const [ofertas, setOfertas] = useState<Oferta[]>([]);

  useEffect(() => {
    // Si no se pueden traer, la cotización sigue: las ofertas son un extra.
    contenedor.ofertas.vigentes().then(setOfertas, () => setOfertas([]));
  }, [contenedor]);

  const tocan = ofertasParaLista(lista.items, productos, ofertas);
  if (tocan.length === 0) return null;
  return (
    <section className="ofertas-lista" aria-label="Ofertas para esta lista">
      <h4 className="subseccion">Ofertas de caseros para su lista</h4>
      <ul className="ofertas-lista__items">
        {tocan.map(({ oferta, ahorro }) => (
          <li key={oferta.id}>
            <strong>{oferta.nombreProducto}</strong> a Bs {bs(oferta.monto)} por {oferta.presentacion} en{" "}
            <a href={hrefMercado(oferta.codigoMercado)}>{oferta.nombreMercado}</a>
            {oferta.numeroPuesto && <>, {tituloPuesto(oferta.numeroPuesto, oferta.nombrePuesto)}</>}.{" "}
            {ahorro > 0 && (
              <>
                Con lo que pide su lista ahorra unos <strong>Bs {bs(ahorro)}</strong> frente al precio {oferta.procedenciaSistema}{" "}
                de ese mercado.{" "}
              </>
            )}
            <span className="tenue">Declarada por el vendedor · {textoVence(oferta.hasta)}.</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
