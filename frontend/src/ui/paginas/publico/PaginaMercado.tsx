import { useEffect, useMemo, useRef, useState } from "react";

import {
  bs,
  esPrecioViejo,
  etiquetaTipo,
  fechaDiaMes,
  nombreCategoria,
  publicaRango,
  sinTildes,
  textoAntiguedad,
  textoDiferenciaCiudad,
  textoDisponibilidad,
  nombreDelPuesto,
  type ArticuloInventario,
  type FichaMercado,
  type PrecioDeProducto,
  type PuestoEnFicha,
  type Usuario,
} from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { Icono } from "@/ui/componentes/Iconos";
import { MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { Pestanas } from "@/ui/componentes/Pestanas";
import { Procedencia } from "@/ui/componentes/Procedencia";
import { TarjetaOferta } from "@/ui/componentes/TarjetaOferta";
import { hrefDe, hrefMercado, useParametroDeRuta } from "@/ui/hooks/useRuta";

type Vista = "precios" | "puestos" | "ofertas";

/**
 * Entrar a un mercado (C134): el precio de cada producto en ese lugar, con
 * su procedencia y cuánto se aparta de la ciudad; sus puestos con lo que
 * cada uno declaró o se le midió; y las ofertas de sus caseros.
 */
export function PaginaMercado({ contenedor, usuario }: { contenedor: Contenedor; usuario: Usuario | null }) {
  const codigo = useParametroDeRuta("codigo");
  // Un enlace compartido por un casero (#/mercado?codigo=x&puesto=14) abre sus puestos con el suyo resaltado.
  const puestoBuscado = useParametroDeRuta("puesto");
  const [ficha, setFicha] = useState<FichaMercado | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [vista, setVista] = useState<Vista>("precios");

  useEffect(() => {
    let vigente = true;
    setError(null);
    contenedor.mercados.ficha(codigo).then(
      (f) => vigente && setFicha(f),
      (e) => vigente && setError(textoDeError(e)),
    );
    return () => {
      vigente = false;
    };
  }, [contenedor, codigo]);

  // Al pasar de un mercado a otro (un sector, por ejemplo) se vuelve a los precios.
  useEffect(() => {
    setFicha(null);
    setVista(puestoBuscado ? "puestos" : "precios");
  }, [codigo, puestoBuscado]);

  return (
    <section aria-labelledby="titulo-mercado" className="ficha">
      <a className="ficha__volver" href={hrefDe("mercados")}>
        ← Todos los mercados
      </a>
      <MensajeError texto={error} />
      {!ficha && !error && <p className="estado">Entrando al mercado…</p>}
      {ficha && (
        <>
          <Cabecera ficha={ficha} />
          <Pestanas<Vista>
            pestanas={[
              { id: "precios", texto: `Precios (${ficha.precios.length})` },
              { id: "puestos", texto: `Puestos (${ficha.puestos.length})` },
              { id: "ofertas", texto: `Ofertas (${ficha.ofertas.length})` },
            ]}
            activa={vista}
            onCambiar={setVista}
          />
          {vista === "precios" && <TablaPrecios ficha={ficha} />}
          {vista === "puestos" && (
            <Puestos ficha={ficha} contenedor={contenedor} usuario={usuario} resaltado={puestoBuscado} />
          )}
          {vista === "ofertas" && (
            <div className="ofertas">
              {ficha.ofertas.length === 0 && (
                <p className="estado">Hoy no hay ofertas vigentes en este lugar.</p>
              )}
              {ficha.ofertas.map((o) => (
                <TarjetaOferta
                  key={o.id}
                  oferta={o}
                  contenedor={contenedor}
                  usuario={usuario}
                  conMercado={false}
                />
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}

function Cabecera({ ficha }: { ficha: FichaMercado }) {
  const { mercado, padre, sectores } = ficha;
  const factor = ficha.factorMercado;
  return (
    <>
      <header className="ficha__cabeza">
        <span className="ficha__sello" aria-hidden="true">
          <Icono nombre={mercado.tipo === "mercado" ? "mercado" : "puesto"} tamano={26} />
        </span>
        <div>
          <h2 id="titulo-mercado" className="ficha__nombre">
            {mercado.nombre}
          </h2>
          <p className="tenue">
            {etiquetaTipo(mercado.tipo)} · {mercado.zona}
            {mercado.macrodistrito && mercado.macrodistrito !== mercado.zona && <> · {mercado.macrodistrito}</>}
            {padre && (
              <>
                {" "}
                · sector de <a href={hrefMercado(padre.codigo)}>{padre.nombre}</a>
              </>
            )}
          </p>
          {sectores.length > 0 && (
            <p className="tenue">
              Sectores:{" "}
              {sectores.map((s, i) => (
                <span key={s.codigo}>
                  {i > 0 && ", "}
                  <a href={hrefMercado(s.codigo)}>{s.nombre}</a>
                </span>
              ))}
            </p>
          )}
        </div>
      </header>

      <div className="cifras">
        <div className="cifra">
          <span className="cifra__valor">{ficha.precios.length}</span>
          <span className="cifra__nombre">
            productos con precio: {ficha.observados} {ficha.observados === 1 ? "medido" : "medidos"} aquí,{" "}
            {ficha.estimados} {ficha.estimados === 1 ? "estimado" : "estimados"}
          </span>
        </div>
        <div className="cifra">
          <span className="cifra__valor">{ficha.puestos.length}</span>
          <span className="cifra__nombre">{ficha.puestos.length === 1 ? "puesto conocido" : "puestos conocidos"}</span>
        </div>
        <div className="cifra">
          <span className="cifra__valor">{ficha.ofertas.length}</span>
          <span className="cifra__nombre">{ficha.ofertas.length === 1 ? "oferta vigente" : "ofertas vigentes"}</span>
        </div>
        <div className="cifra">
          <span className="cifra__valor">
            {Math.abs(factor - 1) < 0.005 ? "—" : `${factor > 1 ? "+" : "−"}${Math.round(Math.abs(factor - 1) * 100)} %`}
          </span>
          <span className="cifra__nombre">
            {Math.abs(factor - 1) < 0.005
              ? "todavía no se midió cuánto se aparta de la ciudad"
              : `suele estar ${factor > 1 ? "más caro" : "más barato"} que el promedio de la ciudad`}
          </span>
        </div>
      </div>

      {ficha.observados === 0 && ficha.precios.length > 0 && (
        <p className="honestidad">
          Nadie midió precios en este lugar todavía: todos son <strong>estimados</strong> desde el boletín oficial de la
          ciudad. Si compra acá, reportar lo que pagó convierte un estimado en un precio observado.
        </p>
      )}
      {ficha.datoMasReciente && (
        <p className="tenue">El precio medido más reciente aquí es del {fechaDiaMes(ficha.datoMasReciente)}.</p>
      )}
    </>
  );
}

function TablaPrecios({ ficha }: { ficha: FichaMercado }) {
  const [texto, setTexto] = useState("");
  const [soloObservados, setSoloObservados] = useState(false);
  const rango = publicaRango(ficha.mercado.tipo);

  const porCategoria = useMemo(() => {
    const buscado = sinTildes(texto.trim());
    const grupos = new Map<string, PrecioDeProducto[]>();
    for (const p of ficha.precios) {
      if (buscado && !sinTildes(p.nombreProducto).includes(buscado)) continue;
      if (soloObservados && p.precio.procedencia !== "observado") continue;
      grupos.set(p.categoria, [...(grupos.get(p.categoria) ?? []), p]);
    }
    return [...grupos.entries()];
  }, [ficha.precios, texto, soloObservados]);

  if (ficha.precios.length === 0) {
    return <p className="estado">No hay precios para este lugar: ni mediciones ni referencia de su nivel.</p>;
  }
  return (
    <>
      <div className="barra">
        <input
          className="barra__buscar"
          type="search"
          placeholder="Buscar un producto"
          aria-label="Buscar un producto en este mercado"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
        />
        <label className="casilla">
          <input type="checkbox" checked={soloObservados} onChange={(e) => setSoloObservados(e.target.checked)} />
          Solo lo medido aquí
        </label>
      </div>
      {porCategoria.length === 0 && <p className="estado">Ningún producto coincide.</p>}
      {porCategoria.map(([categoria, precios]) => (
        <div key={categoria} className="tabla-envoltura">
          <table className="tabla" aria-label={`Precios de ${nombreCategoria(categoria)}`}>
            <caption className="tabla__titulo">{nombreCategoria(categoria)}</caption>
            <thead>
              <tr>
                <th>Producto</th>
                <th>Precio</th>
                <th>De dónde sale</th>
                <th>Frente a la ciudad</th>
              </tr>
            </thead>
            <tbody>
              {precios.map((p) => (
                <tr key={p.codigoProducto} className={esPrecioViejo(p.precio) ? "precio--viejo" : undefined}>
                  <td>{p.nombreProducto}</td>
                  <td className="tabla__numero">
                    {rango ? `Bs ${bs(p.precio.rango.minimo)} a ${bs(p.precio.rango.maximo)}` : `Bs ${bs(p.precio.rango.centro)}`}
                    <span className="tenue"> /{p.precio.unidad}</span>
                  </td>
                  <td>
                    <Procedencia valor={p.precio.procedencia} />
                    {textoAntiguedad(p.precio) && <span className="tenue"> {textoAntiguedad(p.precio)}</span>}
                  </td>
                  <td className={p.diferencia !== null && p.diferencia > 0.005 ? "ficha__caro" : p.diferencia !== null && p.diferencia < -0.005 ? "ficha__barato" : undefined}>
                    {textoDiferenciaCiudad(p.diferencia) ?? (
                      <span className="tenue">{p.precio.procedencia === "estimado" ? "sale de la ciudad" : "—"}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
      {ficha.productosSinPrecio > 0 && (
        <p className="tenue">
          {ficha.productosSinPrecio} {ficha.productosSinPrecio === 1 ? "producto no tiene" : "productos no tienen"} precio
          acá: sin mediciones ni referencia de este nivel. No se inventa.
        </p>
      )}
    </>
  );
}

function Puestos({
  ficha,
  contenedor,
  usuario,
  resaltado = "",
}: {
  ficha: FichaMercado;
  contenedor: Contenedor;
  usuario: Usuario | null;
  resaltado?: string;
}) {
  // El inventario de cada puesto (C137): lo que tiene hoy, con su disponibilidad.
  const [inventarios, setInventarios] = useState<Map<string, readonly ArticuloInventario[]>>(new Map());
  useEffect(() => {
    let vigente = true;
    contenedor.mercados.puestos(ficha.mercado.codigo).then(
      (d) => vigente && setInventarios(new Map(d.puestos.map((x) => [`${x.puesto.codigoMercado}:${x.puesto.numero}`, x.articulos]))),
      () => undefined,
    );
    return () => {
      vigente = false;
    };
  }, [contenedor, ficha.mercado.codigo]);

  if (ficha.puestos.length === 0) {
    return (
      <p className="estado">
        Todavía no hay puestos registrados en este lugar. Si usted vende aquí, cree su cuenta de vendedor y registre su
        puesto desde «Mi puesto»: su foto, sus precios y sus ofertas van a aparecer en el mapa.
      </p>
    );
  }
  return (
    <div className="puestos">
      {ficha.puestos.map((p) => (
        <TarjetaPuesto
          key={p.puesto.numero}
          item={p}
          articulos={inventarios.get(`${p.puesto.codigoMercado}:${p.puesto.numero}`) ?? []}
          contenedor={contenedor}
          usuario={usuario}
          resaltado={resaltado !== "" && resaltado.toUpperCase() === p.puesto.numero}
        />
      ))}
    </div>
  );
}

function TarjetaPuesto({
  item,
  articulos,
  contenedor,
  usuario,
  resaltado = false,
}: {
  item: PuestoEnFicha;
  articulos: readonly ArticuloInventario[];
  contenedor: Contenedor;
  usuario: Usuario | null;
  resaltado?: boolean;
}) {
  const { puesto, precios, ofertas } = item;
  const titulo = nombreDelPuesto(puesto);
  const tarjeta = useRef<HTMLElement>(null);
  useEffect(() => {
    if (resaltado) tarjeta.current?.scrollIntoView?.({ block: "center" });
  }, [resaltado]);
  return (
    <article ref={tarjeta} className={`puesto${resaltado ? " puesto--resaltado" : ""}`} aria-label={titulo}>
      {puesto.foto && <img className="puesto__foto" src={puesto.foto} alt={`Foto de ${titulo}`} loading="lazy" />}
      <header className="puesto__cabeza">
        <span className="puesto__numero" aria-hidden="true">
          {puesto.esLocal ? <Icono nombre="caja" tamano={20} /> : puesto.numero}
        </span>
        <div>
          <h3 className="puesto__nombre">{titulo}</h3>
          {puesto.referencia && <p className="tenue">{puesto.referencia}</p>}
          {!puesto.registrado && <p className="tenue">Visto en el levantamiento de campo; el casero todavía no lo registró.</p>}
        </div>
      </header>
      {puesto.rubros.length > 0 && (
        <p className="puesto__rubros">
          {puesto.rubros.map((r) => (
            <span key={r} className="chip">
              {nombreCategoria(r)}
            </span>
          ))}
        </p>
      )}
      {articulos.length > 0 && (
        <ul className="puesto__precios" aria-label={`Lo que tiene hoy ${titulo}`}>
          {articulos.map((a) => (
            <li key={a.codigoProducto} className={a.disponibilidad === "agotado" ? "puesto__agotado" : undefined}>
              <span>{a.nombreProducto}</span>
              <span className="tabla__numero">
                Bs {bs(a.monto)} <span className="tenue">por {a.presentacion}</span>
              </span>
              <span className="tenue">
                declarado por el casero
                {a.disponibilidad !== "hay" && (
                  <>
                    {" · "}
                    <span className={`disponible disponible--${a.disponibilidad}`}>{textoDisponibilidad(a.disponibilidad)}</span>
                  </>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
      {articulos.length === 0 && precios.length > 0 && (
        <ul className="puesto__precios">
          {precios.map((p) => (
            <li key={p.codigoProducto}>
              <span>{p.nombreProducto}</span>
              <span className="tabla__numero">
                Bs {bs(p.monto)} <span className="tenue">por {p.unidad}</span>
              </span>
              <span className="tenue">
                {p.fuente === "campo" ? "medido en campo" : "declarado por el casero"}
                {p.fecha && ` el ${fechaDiaMes(p.fecha)}`}
              </span>
            </li>
          ))}
        </ul>
      )}
      {articulos.length === 0 && precios.length === 0 && ofertas.length === 0 && (
        <p className="tenue">Sin precios publicados todavía.</p>
      )}
      {ofertas.map((o) => (
        <TarjetaOferta key={o.id} oferta={o} contenedor={contenedor} usuario={usuario} conMercado={false} />
      ))}
    </article>
  );
}
