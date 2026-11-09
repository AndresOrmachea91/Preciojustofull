import { useEffect, useState } from "react";

import { PASAJE_POR_DEFECTO } from "@/aplicacion/casosUso/usuario/planificarCompra";
import {
  bs,
  nombreDelPuesto,
  NOMBRE_UNIDAD_BASE,
  ZONAS_DE_LA_PAZ,
  type Coordenadas,
  type ListaCompras,
  type Oferta,
  type Producto,
  type PuestoConInventario,
} from "@/dominio/modelo";
import type { Parada, PlanCompra, ResultadoPlan } from "@/dominio/servicio/planificarCompra";
import type { Contenedor } from "@/infraestructura/contenedor";
import { MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { hrefMercado, hrefPuesto } from "@/ui/hooks/useRuta";

const unidad = (codigo: string) => (NOMBRE_UNIDAD_BASE as Record<string, string>)[codigo]?.toLowerCase() ?? codigo;
const cantidad = (x: number) => (Number.isInteger(x) ? String(x) : x.toFixed(2).replace(/0$/, "").replace(".", ","));

/**
 * El plan de compra de una lista (C144): dónde comprar cada cosa contando el
 * pasaje, con lo que se gana y lo que se pierde frente a ir a un solo lugar,
 * y en qué puestos registrados conseguirlo.
 */
export function PlanDeCompra({
  contenedor,
  lista,
  productos,
}: {
  contenedor: Contenedor;
  lista: ListaCompras;
  productos: readonly Producto[];
}) {
  const [pasaje, setPasaje] = useState(PASAJE_POR_DEFECTO);
  const [origen, setOrigen] = useState<{ nombre: string; punto: Coordenadas } | null>(null);
  const [resultado, setResultado] = useState<ResultadoPlan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ubicando, setUbicando] = useState(false);

  useEffect(() => {
    let vigente = true;
    setResultado(null);
    setError(null);
    contenedor.planificarCompra
      .ejecutar(lista.items, productos, { pasaje, origen: origen?.punto ?? null })
      .then(
        (r) => vigente && setResultado(r),
        (e) => vigente && setError(textoDeError(e)),
      );
    return () => {
      vigente = false;
    };
  }, [contenedor, lista, productos, pasaje, origen]);

  async function usarMiUbicacion() {
    setUbicando(true);
    try {
      setOrigen({ nombre: "su ubicación", punto: await contenedor.cercaDeMi.ubicar() });
    } catch (e) {
      setError(textoDeError(e));
    } finally {
      setUbicando(false);
    }
  }

  return (
    <section className="plan" aria-label="Plan de compra con pasajes">
      <h4 className="subseccion">Plan de compra: ahorro contando el pasaje</h4>

      <div className="plan__opciones">
        <label className="campo plan__pasaje">
          <span>Pasaje por tramo (Bs)</span>
          <input
            type="number"
            min={0}
            step={0.5}
            inputMode="decimal"
            value={pasaje}
            onChange={(e) => setPasaje(Math.max(0, Number(e.target.value) || 0))}
          />
        </label>
        <div className="zonas" role="group" aria-label="Desde dónde sale">
          <span className="tenue">Sale desde:</span>
          <button type="button" className="filtro" aria-pressed={origen === null} onClick={() => setOrigen(null)}>
            No sé
          </button>
          {ZONAS_DE_LA_PAZ.map((z) => (
            <button
              key={z.nombre}
              type="button"
              className="filtro"
              aria-pressed={origen?.nombre === z.nombre}
              onClick={() => setOrigen({ nombre: z.nombre, punto: z })}
            >
              {z.nombre}
            </button>
          ))}
          <button type="button" className="filtro" disabled={ubicando} onClick={() => void usarMiUbicacion()}>
            {ubicando ? "Buscando…" : "Mi ubicación"}
          </button>
        </div>
      </div>

      {error && <MensajeError texto={error} />}
      {!resultado && !error && <p className="estado">Armando el plan…</p>}
      {resultado && <ResultadoDelPlan contenedor={contenedor} resultado={resultado} origen={origen?.nombre ?? null} />}
    </section>
  );
}

function ResultadoDelPlan({
  contenedor,
  resultado,
  origen,
}: {
  contenedor: Contenedor;
  resultado: ResultadoPlan;
  origen: string | null;
}) {
  const { mejor, unSoloLugar, porParadas, faltantes } = resultado;
  if (!mejor) return <p className="estado">No hay precios al consumidor para estos productos todavía.</p>;

  const reparte = mejor.paradas.length > 1;
  // Si lo mejor es un solo lugar, igual se muestra qué pasaría al repartir: la cuenta que no conviene.
  const repartir = !reparte ? porParadas.find((p) => p.paradas.length === 2) ?? null : null;
  // Lo que repartir dejaría en el bolsillo (negativo: costaría más). Si es poco, no vale otra vuelta.
  const ahorroRepartiendo = repartir ? Math.round((mejor.total - repartir.total) * 100) / 100 : 0;
  const otros = repartir
    ? repartir.paradas.map((p) => p.mercado.nombre).filter((n) => n !== mejor.paradas[0]!.mercado.nombre).join(" y ")
    : "";

  return (
    <>
      <div className={`plan__veredicto${reparte ? " plan__veredicto--reparte" : ""}`}>
        <p className="plan__titulo">
          {reparte
            ? `Conviene repartir la compra en ${mejor.paradas.length} mercados`
            : `Conviene comprar todo en ${mejor.paradas[0]!.mercado.nombre}`}
        </p>
        <div className="plan__balance">
          <Cifra
            etiqueta="Gana en precios"
            monto={reparte ? resultado.ganaEnPrecios : repartir ? Math.max(0, mejor.costoProductos - repartir.costoProductos) : 0}
            tono="gana"
          />
          <Cifra
            etiqueta="Pierde en pasajes"
            monto={reparte ? resultado.pierdeEnPasajes : repartir ? Math.max(0, repartir.costoPasajes - mejor.costoPasajes) : 0}
            tono="pierde"
          />
          {reparte ? (
            <Cifra etiqueta="Le queda en el bolsillo" monto={resultado.neto} tono="neto" />
          ) : (
            <Cifra
              etiqueta="Si reparte, al final"
              monto={ahorroRepartiendo}
              tono={ahorroRepartiendo > 0 ? "gana" : "pierde"}
              signo
            />
          )}
        </div>
        <p className="tenue plan__explica">
          {reparte
            ? `Frente a comprar todo en ${unSoloLugar?.paradas[0]?.mercado.nombre ?? "un solo lugar"}.`
            : !repartir
              ? "Ningún reparto entre mercados baja el total."
              : ahorroRepartiendo > 0
                ? `Ir también a ${otros} ahorraría apenas Bs ${bs(ahorroRepartiendo)} después del pasaje: no vale otra vuelta por tan poco.`
                : `Ir también a ${otros} ahorraría en precios, pero el pasaje se come ese ahorro.`}
        </p>
      </div>

      <ol className="plan__paradas">
        {mejor.paradas.map((parada, i) => (
          <ParadaDelPlan key={parada.mercado.codigo} contenedor={contenedor} parada={parada} numero={i + 1} />
        ))}
      </ol>

      <p className="plan__total">
        <span>
          Productos <strong>Bs {bs(mejor.costoProductos)}</strong>
        </span>
        <span>
          + pasajes <strong>Bs {bs(mejor.costoPasajes)}</strong>
          <span className="tenue">
            {" "}
            ({mejor.tramosPagados} de {mejor.tramos} tramos en minibús
            {mejor.tramos > mejor.tramosPagados ? `, ${mejor.tramos - mejor.tramosPagados} a pie` : ""})
          </span>
        </span>
        <span className="plan__gran-total">
          = <strong>Bs {bs(mejor.total)}</strong>
        </span>
      </p>
      <p className="tenue">
        {origen
          ? `Saliendo de ${origen}${mejor.distanciaKm !== null ? `, unos ${String(mejor.distanciaKm).replace(".", ",")} km de recorrido` : ""}. Menos de 800 m se camina.`
          : "Sin saber de dónde sale, se cuentan pagados la ida y la vuelta. Elija su zona para que la cuenta sea más fina."}
        {mejor.estimados > 0 && ` ${mejor.estimados} precio(s) del plan son estimados: nadie los midió todavía en ese lugar.`}
      </p>

      {faltantes.length > 0 && (
        <p className="aviso">Sin precio en ningún lugar: {faltantes.map((f) => f.nombre).join(", ")}. No entran en la cuenta.</p>
      )}

      {porParadas.length > 1 && <Comparacion planes={porParadas} mejor={mejor} />}
    </>
  );
}

/** Una cifra del balance. Con `signo`, dice + o − (lo que se gana o se pierde). */
function Cifra({ etiqueta, monto, tono, signo = false }: { etiqueta: string; monto: number; tono: string; signo?: boolean }) {
  return (
    <div className={`plan__cifra plan__cifra--${tono}`}>
      <span className="tenue">{etiqueta}</span>
      <strong>
        {signo ? (monto > 0 ? "+" : monto < 0 ? "−" : "") : ""}Bs {bs(Math.abs(monto))}
      </strong>
    </div>
  );
}

function Comparacion({ planes, mejor }: { planes: readonly PlanCompra[]; mejor: PlanCompra }) {
  return (
    <div className="tabla-envoltura">
      <table className="tabla plan__tabla">
        <caption className="tenue">Las otras formas de hacer la compra</caption>
        <thead>
          <tr>
            <th scope="col">Lugares</th>
            <th scope="col">Productos</th>
            <th scope="col">Pasajes</th>
            <th scope="col">Total</th>
          </tr>
        </thead>
        <tbody>
          {planes.map((p) => (
            <tr key={p.paradas.map((x) => x.mercado.codigo).join("+")} className={p === mejor ? "plan__fila-mejor" : undefined}>
              <th scope="row">{p.paradas.map((x) => x.mercado.nombre).join(" + ")}</th>
              <td>Bs {bs(p.costoProductos)}</td>
              <td>Bs {bs(p.costoPasajes)}</td>
              <td>
                <strong>Bs {bs(p.total)}</strong>
                {p === mejor && <span className="insignia"> el mejor</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Una parada: qué comprar ahí y en qué puestos registrados lo tienen. */
function ParadaDelPlan({ contenedor, parada, numero }: { contenedor: Contenedor; parada: Parada; numero: number }) {
  const [puestos, setPuestos] = useState<readonly PuestoConInventario[]>([]);
  const [ofertas, setOfertas] = useState<readonly Oferta[]>([]);
  const codigo = parada.mercado.codigo;

  useEffect(() => {
    let vigente = true;
    contenedor.mercados.puestos(codigo, { articulos: 50 }).then(
      (d) => vigente && setPuestos(d.puestos),
      () => vigente && setPuestos([]),
    );
    contenedor.ofertas.vigentes({ mercado: codigo }).then(
      (o) => vigente && setOfertas(o),
      () => vigente && setOfertas([]),
    );
    return () => {
      vigente = false;
    };
  }, [contenedor, codigo]);

  const buscados = new Set(parada.compras.map((c) => c.necesidad.codigoProducto));
  // Los puestos registrados que tienen algo de lo que se compra aquí: primero los que tienen más.
  const recomendados = puestos
    .map((p) => ({ ...p, tiene: p.articulos.filter((a) => buscados.has(a.codigoProducto) && a.disponibilidad !== "agotado") }))
    .filter((p) => p.tiene.length > 0)
    .sort((a, b) => b.tiene.length - a.tiene.length)
    .slice(0, 3);

  return (
    <li className="plan__parada">
      <div className="plan__parada-cabeza">
        <span className="plan__numero" aria-hidden="true">
          {numero}
        </span>
        <a href={hrefMercado(codigo)}>
          <strong>{parada.mercado.nombre}</strong>
        </a>
        <span className="tenue">{parada.mercado.zona}</span>
        <strong className="plan__subtotal">Bs {bs(parada.subtotal)}</strong>
      </div>
      <ul className="plan__compras">
        {parada.compras.map((c) => (
          <li key={c.necesidad.codigoProducto}>
            <span>
              {c.necesidad.nombre}{" "}
              <span className="tenue">
                · {cantidad(c.necesidad.cantidadBase)} {unidad(c.necesidad.unidad)} a Bs {bs(c.precioUnidad)}
                {c.procedencia === "estimado" ? " (estimado)" : ""}
              </span>
            </span>
            <span className="ventana__monto">Bs {bs(c.costo)}</span>
          </li>
        ))}
      </ul>
      {recomendados.length > 0 && (
        <div className="plan__puestos">
          <span className="tenue">Caseras registradas que lo tienen:</span>
          <ul>
            {recomendados.map(({ puesto, tiene }) => (
              <li key={puesto.numero}>
                <a href={hrefPuesto(codigo, puesto.numero)}>{nombreDelPuesto(puesto)}</a>
                <span className="tenue">
                  {" "}
                  ·{" "}
                  {tiene
                    .map((a) => {
                      const oferta = ofertas.find((o) => o.numeroPuesto === puesto.numero && o.codigoProducto === a.codigoProducto);
                      return oferta
                        ? `★ ${a.nombreProducto} Bs ${bs(oferta.monto)}/${oferta.presentacion} (oferta)`
                        : `${a.nombreProducto} Bs ${bs(a.monto)}/${a.presentacion}`;
                    })
                    .join(" · ")}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </li>
  );
}
