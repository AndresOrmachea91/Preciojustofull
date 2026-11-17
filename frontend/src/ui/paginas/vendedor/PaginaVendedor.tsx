import { useCallback, useEffect, useState, type FormEvent } from "react";

import {
  DURACIONES_OFERTA,
  MAXIMO_OFERTAS_ACTIVAS,
  NOMBRE_UNIDAD_BASE,
  PRODUCTOS_POR_COMBO,
  ofertasQueCuentan,
  bs,
  presentacionBase,
  textoVence,
  type EstadoMiOferta,
  type MiOferta,
  type PrecioPublicado,
  type Producto,
  type Usuario,
} from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { MensajeAviso, MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { Pestanas } from "@/ui/componentes/Pestanas";
import { SelectorProducto } from "@/ui/componentes/SelectorProducto";
import { useCatalogo } from "@/ui/hooks/useCatalogo";
import { InventarioPuesto } from "@/ui/paginas/vendedor/InventarioPuesto";
import { MiNegocio } from "@/ui/paginas/vendedor/MiNegocio";
import { RendimientoPuesto } from "@/ui/paginas/vendedor/RendimientoPuesto";
import { hrefMercado } from "@/ui/hooks/useRuta";

type Vista = "inventario" | "negocio" | "ofertas" | "precios";

/**
 * El casero desde el celular (C137): su inventario a un toque, su negocio
 * (puesto en un mercado o distribuidora, con foto), sus ofertas y lo que
 * publicó. Si todavía no registró dónde vende, empieza por ahí: ya no
 * depende de que un administrador se lo asigne (decisión 26).
 */
export function PaginaVendedor({ contenedor, vendedor }: { contenedor: Contenedor; vendedor: Usuario }) {
  const { productos, mercados } = useCatalogo(contenedor);
  const [punto, setPunto] = useState<string | null>(vendedor.codigoPuntoVenta ?? null);
  const [vista, setVista] = useState<Vista>("inventario");
  const lugar = mercados.find((m) => m.codigo === punto);

  if (!punto) {
    return (
      <section aria-labelledby="titulo-puesto">
        <h2 id="titulo-puesto" className="seccion">
          Mi puesto
        </h2>
        <p className="app__lema">
          Diga dónde vende y aparezca en el mapa: los compradores ven su puesto, su foto y sus precios.
        </p>
        <MiNegocio contenedor={contenedor} mercados={mercados} alGuardar={(p) => setPunto(p.codigoMercado)} />
      </section>
    );
  }

  return (
    <section aria-labelledby="titulo-puesto">
      <h2 id="titulo-puesto" className="seccion">
        Mi puesto{lugar && <span className="tenue"> · {lugar.nombre}</span>}
      </h2>
      {lugar && (
        <p className="tenue">
          Así lo ven los compradores: <a href={hrefMercado(lugar.codigo)}>ficha de {lugar.nombre}</a>.
        </p>
      )}
      <Pestanas<Vista>
        pestanas={[
          { id: "inventario", texto: "Inventario" },
          { id: "negocio", texto: "Mi negocio" },
          { id: "ofertas", texto: "Mis ofertas" },
          { id: "precios", texto: "Precios publicados" },
        ]}
        activa={vista}
        onCambiar={setVista}
      />
      {vista === "inventario" && <InventarioPuesto contenedor={contenedor} productos={productos} />}
      {vista === "negocio" && (
        <>
          <RendimientoPuesto contenedor={contenedor} />
          <MiNegocio contenedor={contenedor} mercados={mercados} alGuardar={(p) => setPunto(p.codigoMercado)} />
        </>
      )}
      {vista === "ofertas" && <MisOfertas contenedor={contenedor} productos={productos} />}
      {vista === "precios" && <MisPrecios contenedor={contenedor} productos={productos} />}
    </section>
  );
}

// --- precios -----------------------------------------------------------------------

function MisPrecios({ contenedor, productos }: { contenedor: Contenedor; productos: readonly Producto[] }) {
  const [precios, setPrecios] = useState<PrecioPublicado[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const cargar = useCallback(() => {
    contenedor.miPuesto.misPrecios().then(setPrecios, (e) => setError(textoDeError(e)));
  }, [contenedor]);
  useEffect(cargar, [cargar]);

  return (
    <>
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
                    Bs {bs(p.monto)} <span className="tenue">por {p.presentacion}</span>
                  </td>
                  <td className="tenue">
                    Bs {bs(p.precioPorUnidadBase)} por {NOMBRE_UNIDAD_BASE[p.unidadBase].toLowerCase()}
                  </td>
                  <td className="tenue">{new Date(p.publicadoEn).toLocaleDateString("es-BO")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
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
    if (!codigoProducto) {
      setError("Elija un producto de la lista");
      return;
    }
    try {
      await contenedor.miPuesto.publicar({ codigoProducto, monto: Number(monto), presentacion: presentacionElegida });
      alPublicar(`Publicado: ${producto?.nombre} a Bs ${bs(Number(monto))} por ${presentacionElegida}.`);
      setMonto("");
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  return (
    <form className="formulario formulario--recuadro" onSubmit={(e) => void enviar(e)} aria-label="Publicar un precio">
      <div className="formulario__fila formulario__fila--tres">
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

// --- ofertas ---------------------------------------------------------------------------

const ESTADO: Record<EstadoMiOferta, string> = {
  activa: "Activa",
  vencida: "Vencida",
  en_revision: "En revisión",
  retirada: "Retirada",
};

function MisOfertas({ contenedor, productos }: { contenedor: Contenedor; productos: readonly Producto[] }) {
  const [ofertas, setOfertas] = useState<MiOferta[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const cargar = useCallback(() => {
    contenedor.miPuesto.misOfertas().then(setOfertas, (e) => setError(textoDeError(e)));
  }, [contenedor]);
  useEffect(cargar, [cargar]);

  // Un combo entero cuenta como una sola oferta activa (C145).
  const activas = ofertasQueCuentan(ofertas?.filter((o) => o.estado === "activa") ?? []);
  const [tipo, setTipo] = useState<"suelta" | "combo">("suelta");
  const publicado = (texto: string) => {
    setError(null);
    setAviso(texto);
    cargar();
  };

  async function retirar(o: MiOferta) {
    setError(null);
    try {
      await contenedor.miPuesto.retirarOferta(o.id);
      setAviso(`Retirada la oferta de ${o.nombreProducto}.`);
      cargar();
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  return (
    <>
      <div className="candado">
        <p>
          <strong>Las reglas de una oferta:</strong> tiene que ser más barata que el precio que el sistema tiene para su
          mercado (calculado sin sus propios precios), vence sola y puede tener hasta {MAXIMO_OFERTAS_ACTIVAS} activas
          (un combo cuenta como una).
          Se muestra como <strong>declarada por usted</strong>, y si dos compradores dicen que no estaba así, se pausa
          hasta que la revisen.
        </p>
      </div>

      <RendimientoPuesto contenedor={contenedor} ofertas={ofertas} />

      {activas < MAXIMO_OFERTAS_ACTIVAS ? (
        <>
          <div className="segmentado" role="group" aria-label="Qué publicar">
            <button type="button" className="segmentado__opcion" aria-pressed={tipo === "suelta"} onClick={() => setTipo("suelta")}>
              Oferta de un producto
            </button>
            <button type="button" className="segmentado__opcion" aria-pressed={tipo === "combo"} onClick={() => setTipo("combo")}>
              Combo de {PRODUCTOS_POR_COMBO.minimo} o {PRODUCTOS_POR_COMBO.maximo} productos
            </button>
          </div>
          {tipo === "suelta" ? (
            <FormularioOferta contenedor={contenedor} productos={productos} alPublicar={publicado} />
          ) : (
            <FormularioCombo contenedor={contenedor} productos={productos} alPublicar={publicado} />
          )}
        </>
      ) : (
        <p className="estado">Ya tiene {MAXIMO_OFERTAS_ACTIVAS} ofertas activas: retire una o espere a que venza.</p>
      )}

      <MensajeError texto={error} />
      <MensajeAviso texto={aviso} />

      <h3 className="subseccion">Mis ofertas</h3>
      {!ofertas && !error && <p className="estado">Cargando sus ofertas…</p>}
      {ofertas && ofertas.length === 0 && <p className="estado">Todavía no publicó ofertas.</p>}
      {ofertas && ofertas.length > 0 && (
        <div className="tabla-envoltura">
          <table className="tabla" aria-label="Mis ofertas">
            <thead>
              <tr>
                <th>Oferta</th>
                <th>Estado</th>
                <th>Compradores</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {ofertas.map((o) => (
                <tr key={o.id} className={o.estado === "activa" ? undefined : "tabla__fila--inactiva"}>
                  <td>
                    {o.combo && <span className="chip chip--combo">{o.combo}</span>} {o.nombreProducto} a Bs {bs(o.monto)}{" "}
                    <span className="tenue">por {o.presentacion}</span>
                    {o.nota && <div className="tenue">«{o.nota}»</div>}
                  </td>
                  <td>
                    <span className={`estado-oferta estado-oferta--${o.estado}`}>{ESTADO[o.estado]}</span>
                    {o.estado === "activa" && <div className="tenue">{textoVence(o.hasta)}</div>}
                  </td>
                  <td className="tenue">
                    {o.confirmaron} la vieron así · {o.desmintieron} dijeron que no
                  </td>
                  <td>
                    {(o.estado === "activa" || o.estado === "en_revision") && (
                      <button type="button" className="boton boton--suave" onClick={() => void retirar(o)}>
                        Retirar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function FormularioOferta({
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
  const [horas, setHoras] = useState<number>(48);
  const [nota, setNota] = useState("");
  const [error, setError] = useState<string | null>(null);
  const producto = productos.find((p) => p.codigo === codigoProducto);
  const presentacionElegida = presentacion || (producto ? presentacionBase(producto).codigo : "");

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    try {
      await contenedor.miPuesto.publicarOferta({
        codigoProducto,
        monto: Number(monto),
        presentacion: presentacionElegida,
        horas,
        nota,
      });
      alPublicar(`Oferta publicada: ${producto?.nombre} a Bs ${bs(Number(monto))} por ${presentacionElegida}, por ${horas} horas.`);
      setMonto("");
      setNota("");
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  return (
    <form className="formulario formulario--recuadro" onSubmit={(e) => void enviar(e)} aria-label="Publicar una oferta">
      <div className="formulario__fila formulario__fila--tres">
        <SelectorProducto
          productos={productos}
          valor={codigoProducto}
          etiqueta="Producto en oferta"
          onElegir={(codigo) => {
            setCodigoProducto(codigo);
            setPresentacion("");
          }}
        />
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
          <span>Precio de oferta (Bs)</span>
          <input required type="number" min={0} step="0.01" value={monto} onChange={(e) => setMonto(e.target.value)} />
        </label>
      </div>
      <div className="formulario__fila">
        <div className="campo">
          <span id="duracion-oferta">Dura</span>
          <div className="segmentado" role="group" aria-labelledby="duracion-oferta">
            {DURACIONES_OFERTA.map((h) => (
              <button
                key={h}
                type="button"
                className="segmentado__opcion"
                aria-pressed={horas === h}
                onClick={() => setHoras(h)}
              >
                {h} horas
              </button>
            ))}
          </div>
        </div>
        <label className="campo">
          <span>Nota (opcional)</span>
          <input maxLength={80} value={nota} onChange={(e) => setNota(e.target.value)} placeholder="Hasta agotar" />
        </label>
      </div>
      <MensajeError texto={error} />
      <div className="formulario__botones">
        <button type="submit" className="boton">
          Publicar oferta
        </button>
      </div>
    </form>
  );
}

/**
 * Un combo (C145): 2 o 3 productos en oferta bajo un nombre. Cada precio
 * tiene que ser más barato que el sistema, igual que una oferta suelta; el
 * combo entero cuenta como UNA oferta activa y vence junto.
 */
function FormularioCombo({
  contenedor,
  productos,
  alPublicar,
}: {
  contenedor: Contenedor;
  productos: readonly Producto[];
  alPublicar: (texto: string) => void;
}) {
  const vacio = { codigoProducto: "", presentacion: "", monto: "" };
  const [nombre, setNombre] = useState("");
  const [renglones, setRenglones] = useState([vacio, vacio]);
  const [horas, setHoras] = useState<number>(48);
  const [nota, setNota] = useState("");
  const [error, setError] = useState<string | null>(null);

  const cambiar = (i: number, cambios: Partial<typeof vacio>) =>
    setRenglones(renglones.map((r, j) => (j === i ? { ...r, ...cambios } : r)));

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    try {
      await contenedor.miPuesto.publicarCombo({
        nombre,
        horas,
        nota,
        renglones: renglones.map((r) => {
          const producto = productos.find((p) => p.codigo === r.codigoProducto);
          return {
            codigoProducto: r.codigoProducto,
            monto: Number(r.monto),
            presentacion: r.presentacion || (producto ? presentacionBase(producto).codigo : ""),
          };
        }),
      });
      alPublicar(`Combo «${nombre.trim()}» publicado por ${horas} horas: cuenta como una sola oferta.`);
      setNombre("");
      setRenglones([vacio, vacio]);
      setNota("");
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  return (
    <form className="formulario formulario--recuadro" onSubmit={(e) => void enviar(e)} aria-label="Publicar un combo">
      <label className="campo">
        <span>Nombre del combo</span>
        <input
          required
          maxLength={40}
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder="Combo sopa, Para el almuerzo…"
        />
      </label>
      {renglones.map((r, i) => {
        const producto = productos.find((p) => p.codigo === r.codigoProducto);
        return (
          <div key={i} className="formulario__fila formulario__fila--tres combo__renglon">
            <label className="campo">
              <span>Producto {i + 1}</span>
              <select
                value={r.codigoProducto}
                onChange={(e) => cambiar(i, { codigoProducto: e.target.value, presentacion: "" })}
              >
                <option value="">Elija…</option>
                {productos.map((p) => (
                  <option key={p.codigo} value={p.codigo}>
                    {p.nombre}
                  </option>
                ))}
              </select>
            </label>
            <label className="campo">
              <span>Por</span>
              <select
                value={r.presentacion || (producto ? presentacionBase(producto).codigo : "")}
                disabled={!producto}
                onChange={(e) => cambiar(i, { presentacion: e.target.value })}
              >
                {producto?.presentaciones.map((p) => (
                  <option key={p.codigo} value={p.codigo}>
                    {p.nombre}
                  </option>
                ))}
              </select>
            </label>
            <label className="campo">
              <span>Precio de oferta (Bs)</span>
              <input type="number" min={0} step="0.01" value={r.monto} onChange={(e) => cambiar(i, { monto: e.target.value })} />
            </label>
          </div>
        );
      })}
      <div className="formulario__botones">
        {renglones.length < PRODUCTOS_POR_COMBO.maximo && (
          <button type="button" className="boton boton--suave" onClick={() => setRenglones([...renglones, vacio])}>
            + Agregar un tercer producto
          </button>
        )}
        {renglones.length > PRODUCTOS_POR_COMBO.minimo && (
          <button type="button" className="boton boton--suave" onClick={() => setRenglones(renglones.slice(0, -1))}>
            Quitar el último
          </button>
        )}
      </div>
      <div className="formulario__fila">
        <div className="campo">
          <span id="duracion-combo">Dura</span>
          <div className="segmentado" role="group" aria-labelledby="duracion-combo">
            {DURACIONES_OFERTA.map((h) => (
              <button key={h} type="button" className="segmentado__opcion" aria-pressed={horas === h} onClick={() => setHoras(h)}>
                {h} horas
              </button>
            ))}
          </div>
        </div>
        <label className="campo">
          <span>Nota (opcional)</span>
          <input maxLength={80} value={nota} onChange={(e) => setNota(e.target.value)} placeholder="Para la sopa del domingo" />
        </label>
      </div>
      <MensajeError texto={error} />
      <div className="formulario__botones">
        <button type="submit" className="boton">
          Publicar combo
        </button>
      </div>
    </form>
  );
}
