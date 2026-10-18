import { useCallback, useEffect, useState, type FormEvent } from "react";

import {
  CATEGORIAS,
  DURACIONES_OFERTA,
  MAXIMO_OFERTAS_ACTIVAS,
  NOMBRE_UNIDAD_BASE,
  bs,
  presentacionBase,
  textoVence,
  tituloPuesto,
  type EstadoMiOferta,
  type Mercado,
  type MiOferta,
  type PrecioPublicado,
  type Producto,
  type Puesto,
  type Usuario,
} from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { MensajeAviso, MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { Pestanas } from "@/ui/componentes/Pestanas";
import { SelectorProducto } from "@/ui/componentes/SelectorProducto";
import { useCatalogo } from "@/ui/hooks/useCatalogo";
import { hrefMercado } from "@/ui/hooks/useRuta";

type Vista = "precios" | "puesto" | "ofertas";

/**
 * El vendedor publica los precios de su puesto, registra el puesto dentro
 * del mercado y maneja sus ofertas (C133).
 */
export function PaginaVendedor({ contenedor, vendedor }: { contenedor: Contenedor; vendedor: Usuario }) {
  const { productos, mercados } = useCatalogo(contenedor);
  const [vista, setVista] = useState<Vista>("precios");
  const lugar = mercados.find((m) => m.codigo === vendedor.codigoPuntoVenta);

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
        Mi puesto{lugar && <span className="tenue"> · {lugar.nombre}</span>}
      </h2>
      {lugar && (
        <p className="tenue">
          Así lo ven los compradores: <a href={hrefMercado(lugar.codigo)}>ficha de {lugar.nombre}</a>.
        </p>
      )}
      <Pestanas<Vista>
        pestanas={[
          { id: "precios", texto: "Mis precios" },
          { id: "puesto", texto: "Datos del puesto", visible: !lugar || lugar.tipo === "mercado" },
          { id: "ofertas", texto: "Mis ofertas" },
        ]}
        activa={vista}
        onCambiar={setVista}
      />
      {vista === "precios" && <MisPrecios contenedor={contenedor} productos={productos} />}
      {vista === "puesto" && <DatosDelPuesto contenedor={contenedor} lugar={lugar} />}
      {vista === "ofertas" && <MisOfertas contenedor={contenedor} productos={productos} />}
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
      alPublicar(`Publicado: ${producto?.nombre} a Bs ${Number(monto).toFixed(2)} por ${presentacionElegida}.`);
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

// --- datos del puesto ------------------------------------------------------------------

function DatosDelPuesto({ contenedor, lugar }: { contenedor: Contenedor; lugar: Mercado | undefined }) {
  const [puesto, setPuesto] = useState<Puesto | null | undefined>(undefined);
  const [numero, setNumero] = useState("");
  const [nombre, setNombre] = useState("");
  const [referencia, setReferencia] = useState("");
  const [rubros, setRubros] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  useEffect(() => {
    contenedor.miPuesto.puesto().then(
      (p) => {
        setPuesto(p);
        if (p) {
          setNumero(p.numero);
          setNombre(p.nombre);
          setReferencia(p.referencia);
          setRubros([...p.rubros]);
        }
      },
      (e) => setError(textoDeError(e)),
    );
  }, [contenedor]);

  async function guardar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    setAviso(null);
    try {
      const guardado = await contenedor.miPuesto.guardarPuesto({ numero, nombre, rubros, referencia });
      setPuesto(guardado);
      setAviso(`Guardado: ${tituloPuesto(guardado.numero, guardado.nombre)}. Ya aparece en la ficha del mercado.`);
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  if (puesto === undefined && !error) return <p className="estado">Cargando su puesto…</p>;
  return (
    <form className="formulario formulario--recuadro" onSubmit={(e) => void guardar(e)} aria-label="Datos del puesto">
      <p className="tenue">
        {puesto
          ? "Así lo encuentran los compradores en la ficha del mercado."
          : `Registre su número de puesto${lugar ? ` en ${lugar.nombre}` : ""}: sus precios y ofertas van a mostrarse con él.`}
      </p>
      <div className="formulario__fila">
        <label className="campo">
          <span>Número del puesto</span>
          <input required maxLength={16} value={numero} onChange={(e) => setNumero(e.target.value)} placeholder="14, B-3…" />
        </label>
        <label className="campo">
          <span>Nombre (opcional)</span>
          <input maxLength={80} value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Verduras Doña Rosa" />
        </label>
      </div>
      <label className="campo">
        <span>Cómo encontrarlo (opcional)</span>
        <input
          maxLength={160}
          value={referencia}
          onChange={(e) => setReferencia(e.target.value)}
          placeholder="Pasillo de verduras, frente a la puerta 2"
        />
      </label>
      <fieldset className="campo--grupo">
        <legend>Qué vende</legend>
        {CATEGORIAS.map((c) => (
          <label key={c.codigo} className="casilla">
            <input
              type="checkbox"
              checked={rubros.includes(c.codigo)}
              onChange={(e) =>
                setRubros(e.target.checked ? [...rubros, c.codigo] : rubros.filter((r) => r !== c.codigo))
              }
            />
            {c.nombre}
          </label>
        ))}
      </fieldset>
      <MensajeError texto={error} />
      <MensajeAviso texto={aviso} />
      <div className="formulario__botones">
        <button type="submit" className="boton">
          {puesto ? "Guardar cambios" : "Registrar mi puesto"}
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

  const activas = ofertas?.filter((o) => o.estado === "activa").length ?? 0;

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
          mercado (calculado sin sus propios precios), vence sola y puede tener hasta {MAXIMO_OFERTAS_ACTIVAS} activas.
          Se muestra como <strong>declarada por usted</strong>, y si dos compradores dicen que no estaba así, se pausa
          hasta que la revisen.
        </p>
      </div>

      {activas < MAXIMO_OFERTAS_ACTIVAS ? (
        <FormularioOferta
          contenedor={contenedor}
          productos={productos}
          alPublicar={(texto) => {
            setError(null);
            setAviso(texto);
            cargar();
          }}
        />
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
                    {o.nombreProducto} a Bs {bs(o.monto)} <span className="tenue">por {o.presentacion}</span>
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
