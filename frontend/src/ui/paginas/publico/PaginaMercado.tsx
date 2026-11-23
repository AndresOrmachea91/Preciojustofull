import { useEffect, useMemo, useState } from "react";

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
  type FichaMercado,
  type PrecioDeProducto,
  type PuestoConInventario,
  type Usuario,
} from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { DetallePuesto, PlanoMercado, type PuestoDelPlano } from "@/ui/componentes/PlanoMercado";
import { Icono } from "@/ui/componentes/Iconos";
import { MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { Pestanas } from "@/ui/componentes/Pestanas";
import { Procedencia } from "@/ui/componentes/Procedencia";
import { TarjetaOferta } from "@/ui/componentes/TarjetaOferta";
import { hrefDe, hrefMercado, useParametroDeRuta } from "@/ui/hooks/useRuta";

type Vista = "puestos" | "precios" | "ofertas";

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
  const [vista, setVista] = useState<Vista>("puestos");

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

  // Al pasar de un mercado a otro (un sector, por ejemplo) se vuelve al mercado con sus puestos.
  useEffect(() => {
    setFicha(null);
    setVista("puestos");
  }, [codigo, puestoBuscado]);
  // Un lugar sin puestos registrados abre directo en sus precios.
  useEffect(() => {
    if (ficha && ficha.puestos.length === 0 && !puestoBuscado) setVista("precios");
  }, [ficha, puestoBuscado]);

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
              { id: "puestos", texto: `El mercado · ${ficha.puestos.length} ${ficha.puestos.length === 1 ? "puesto" : "puestos"}` },
              { id: "precios", texto: `Precios (${ficha.precios.length})` },
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
  // El inventario de cada puesto (C137, C148): lo que tiene hoy y cuánto le queda.
  const [inventarios, setInventarios] = useState<Map<string, PuestoConInventario>>(new Map());
  const [elegido, setElegido] = useState<string | null>(resaltado ? resaltado.toUpperCase() : null);
  useEffect(() => {
    let vigente = true;
    contenedor.mercados.puestos(ficha.mercado.codigo).then(
      (d) => vigente && setInventarios(new Map(d.puestos.map((x) => [x.puesto.numero, x]))),
      () => undefined,
    );
    return () => {
      vigente = false;
    };
  }, [contenedor, ficha.mercado.codigo]);
  useEffect(() => setElegido(resaltado ? resaltado.toUpperCase() : null), [resaltado]);

  const puestos: PuestoDelPlano[] = useMemo(
    () =>
      ficha.puestos.map((p) => {
        const inv = inventarios.get(p.puesto.numero);
        return { puesto: p.puesto, articulos: inv?.articulos ?? [], total: inv?.total ?? 0, ofertas: p.ofertas, precios: p.precios };
      }),
    [ficha.puestos, inventarios],
  );

  if (ficha.puestos.length === 0) {
    return (
      <div className="estado estado--vacio">
        <p>
          Todavía no hay puestos registrados en este lugar. Si usted vende aquí, cree su cuenta y registre su puesto desde
          «Mi puesto»: su foto, sus precios y sus ofertas van a aparecer aquí y en el mapa.
        </p>
        <div className="estado__acciones">
          <a className="boton" href="#/registrarse">
            Registrar mi puesto gratis
          </a>
        </div>
      </div>
    );
  }
  const actual = puestos.find((p) => p.puesto.numero === elegido) ?? null;
  return (
    <div className="mercado-vivo">
      <p className="tenue mercado-vivo__ayuda">
        Toque un puesto para ver qué tiene, a cuánto y cuánto le queda. El color del toldo dice qué vende.
      </p>
      <PlanoMercado puestos={puestos} seleccionado={elegido} alElegir={(n) => setElegido(n === elegido ? null : n)} />
      {actual && <DetallePuesto item={actual} contenedor={contenedor} usuario={usuario} alCerrar={() => setElegido(null)} />}
    </div>
  );
}
