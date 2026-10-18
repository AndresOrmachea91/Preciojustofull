import { useEffect, useMemo, useState } from "react";

import type { Producto } from "@/dominio/modelo";
import {
  empatan,
  esPrecioViejo,
  precioEnPresentacion,
  presentacionBase,
  textoDistancia,
  unidadDePresentacion,
} from "@/dominio/modelo";
import { ahorroPosible } from "@/dominio/servicio/ordenarPorConveniencia";
import type { Contenedor } from "@/infraestructura/contenedor";
import { GraficoHistorial } from "@/ui/componentes/GraficoHistorial";
import { Icono } from "@/ui/componentes/Iconos";
import { MapaPuntosVenta } from "@/ui/componentes/MapaPuntosVenta";
import { PanelPunto } from "@/ui/componentes/PanelPunto";
import { SelectorProducto } from "@/ui/componentes/SelectorProducto";
import { TarjetaMercado } from "@/ui/componentes/TarjetaMercado";
import { useCercania } from "@/ui/hooks/useCercania";
import { useComparativa } from "@/ui/hooks/useComparativa";
import { useHistorial } from "@/ui/hooks/useHistorial";
import { useMapa } from "@/ui/hooks/useMapa";

// Con qué producto abre la pantalla: uno que tenga precio en los 88 puntos.
// Si el catálogo no lo trae, se usa el primero.
const PRODUCTO_INICIAL = "arroz_primera";

export function PaginaPrecios({ contenedor }: { contenedor: Contenedor }) {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [producto, setProducto] = useState<string | null>(null);
  const [seleccionado, setSeleccionado] = useState<string | null>(null);

  // El catálogo sale del caso de uso, no de una lista escrita a mano.
  useEffect(() => {
    void contenedor.catalogo.productos().then((lista) => {
      setProductos(lista);
      setProducto(
        (actual) =>
          actual ?? lista.find((p) => p.codigo === PRODUCTO_INICIAL)?.codigo ?? lista[0]?.codigo ?? null,
      );
    });
  }, [contenedor]);

  const codigo = producto ?? "";
  const mapa = useMapa(contenedor, codigo);
  const comparativa = useComparativa(contenedor, codigo);
  const historial = useHistorial(contenedor, codigo);
  const productoActual = productos.find((p) => p.codigo === producto) ?? null;

  // En qué presentación ver los precios (kilo, libra, arroba, quintal...).
  // Al cambiar de producto vuelve a la unidad base: un quintal de huevos no existe.
  const [codigoPresentacion, setCodigoPresentacion] = useState<string | null>(null);
  useEffect(() => setCodigoPresentacion(null), [producto]);
  const presentacion = productoActual
    ? (productoActual.presentaciones.find((p) => p.codigo === codigoPresentacion) ?? presentacionBase(productoActual))
    : null;
  const escalar = useMemo(
    () => <T extends { precio: Parameters<typeof precioEnPresentacion>[0] }>(x: T): T =>
      presentacion ? { ...x, precio: precioEnPresentacion(x.precio, presentacion) } : x,
    [presentacion],
  );

  const marcadores = useMemo(
    () => mapa.datos?.marcadores.map((m) => (m.precio ? escalar({ ...m, precio: m.precio }) : m)) ?? [],
    [mapa.datos, escalar],
  );
  const marcadorSeleccionado = marcadores.find((m) => m.mercado.codigo === seleccionado) ?? null;
  const cercania = useCercania(contenedor, marcadores);

  // Solo se ofrecen presentaciones de la magnitud en que llegó el precio: si
  // la fuente publica por unidad, no hay "por arroba" que mostrar.
  const unidadDelPrecio = mapa.datos?.marcadores.find((m) => m.precio)?.precio?.unidad;
  const presentacionesUtiles =
    productoActual?.presentaciones.filter((p) => !unidadDelPrecio || unidadDePresentacion(p.codigo) === unidadDelPrecio) ??
    [];

  const opciones = comparativa.datos?.opciones.map(escalar) ?? [];
  const minoristas = opciones.filter((o) => o.mercado.nivelPrecio === "minorista");
  const mayoristas = opciones.filter((o) => o.mercado.nivelPrecio === "mayorista");

  return (
    <>
      <p className="app__lema">¿Dónde conviene comprar hoy en La Paz?</p>

      <div className="consulta">
        <SelectorProducto
          productos={productos}
          valor={producto}
          onElegir={setProducto}
          etiqueta="Producto"
          ayuda={`${productos.length} productos. Escriba para buscar o elija de la lista.`}
        />

        {presentacionesUtiles.length > 1 && (
          <div className="consulta__presentacion">
            <span className="buscador__etiqueta" id="ver-precio-por">
              Ver el precio por
            </span>
            <div className="segmentado" role="group" aria-labelledby="ver-precio-por">
              {presentacionesUtiles.map((p) => (
                <button
                  key={p.codigo}
                  type="button"
                  aria-pressed={presentacion?.codigo === p.codigo}
                  className="segmentado__opcion"
                  onClick={() => setCodigoPresentacion(p.codigo)}
                >
                  {p.nombre}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="consulta__cerca">
          <span className="buscador__etiqueta" aria-hidden="true">
            &nbsp;
          </span>
          <button
            type="button"
            className="boton boton--suave boton--icono"
            disabled={cercania.buscando}
            onClick={() => void cercania.buscar()}
          >
            <Icono nombre="ubicacion" tamano={18} />
            {cercania.buscando ? "Buscando…" : "Cerca de mí"}
          </button>
        </div>
      </div>

      {cercania.error && (
        <p className="estado estado--error" role="alert">
          {cercania.error}
        </p>
      )}
      {cercania.ubicacion && (
        <section className="cercanos" aria-labelledby="titulo-cercanos">
          <div className="cercanos__cabeza">
            <h2 id="titulo-cercanos" className="seccion">
              Más cerca de usted
            </h2>
            <button type="button" className="enlace" onClick={cercania.olvidar}>
              Ocultar
            </button>
          </div>
          {cercania.cercanos.length === 0 ? (
            <p className="estado">Ningún punto cercano tiene precio para este producto.</p>
          ) : (
            <ol className="cercanos__lista">
              {cercania.cercanos.map(({ marcador, distanciaKm }) => {
                const precio = marcador.precio && escalar({ precio: marcador.precio }).precio;
                return (
                  <li key={marcador.mercado.codigo}>
                    <button
                      type="button"
                      className="cercanos__punto"
                      aria-pressed={seleccionado === marcador.mercado.codigo}
                      onClick={() => setSeleccionado(marcador.mercado.codigo)}
                    >
                      <span className="cercanos__nombre">{marcador.mercado.nombre}</span>
                      <span className="tenue">{textoDistancia(distanciaKm)}</span>
                      {precio && (
                        <span className="cercanos__precio">
                          Bs {precio.rango.centro.toFixed(2)}
                          <span className="tenue"> /{precio.unidad}</span>
                        </span>
                      )}
                    </button>
                  </li>
                );
              })}
            </ol>
          )}
        </section>
      )}

      {mapa.datos && (
        <section className="honestidad" aria-label="De dónde salen estos precios">
          <p>
            <strong>{mapa.datos.resumen.estimados}</strong> puntos con precio{" "}
            <span className="procedencia procedencia--estimado">◌ estimado</span> desde el precio de
            referencia de la ciudad, <strong>{mapa.datos.resumen.observados}</strong> con precio{" "}
            <span className="procedencia procedencia--observado">● observado</span> en el lugar
            {mapa.datos.resumen.sinDatos > 0 && (
              <>
                , y <strong>{mapa.datos.resumen.sinDatos}</strong> sin precio para este producto
              </>
            )}
            .
          </p>
          {mapa.datos.resumen.observados === 0 && mapa.datos.resumen.estimados > 0 && (
            <p className="honestidad__aviso">
              Todavía nadie verificó este precio en ningún mercado concreto: todos son estimaciones a
              partir del boletín oficial de la ciudad. Cuando haya mediciones en campo, van a aparecer
              como observadas.
            </p>
          )}
        </section>
      )}

      {(mapa.cargando || comparativa.cargando) && <p className="estado">Consultando precios…</p>}

      {(mapa.error || comparativa.error) && (
        <div className="estado estado--error" role="alert">
          <p>{mapa.error ?? comparativa.error}</p>
          <button type="button" onClick={() => void (mapa.error ? mapa.reintentar() : comparativa.reintentar())}>
            Reintentar
          </button>
        </div>
      )}

      {mapa.datos && (
        <>
          <div className="mapa-y-panel">
            <MapaPuntosVenta
              marcadores={marcadores}
              seleccionado={seleccionado}
              onSeleccionar={setSeleccionado}
              ubicacion={cercania.ubicacion}
            />
            <PanelPunto marcador={marcadorSeleccionado} producto={productoActual} />
          </div>
          <LeyendaMapa />
        </>
      )}

      {historial.datos && historial.datos.puntos.length > 0 && (
        <section aria-labelledby="titulo-historial">
          <h2 id="titulo-historial" className="seccion">
            Cómo cambió el precio en La Paz
          </h2>
          <p className="tenue">
            Precio de referencia de la ciudad (SIIP), mes a mes
            {historial.datos.variacionMinorista !== null && (
              <>
                {" "}
                · al consumidor final{" "}
                <strong>
                  {historial.datos.variacionMinorista > 0 ? "subió" : historial.datos.variacionMinorista < 0 ? "bajó" : "no cambió"}
                  {historial.datos.variacionMinorista !== 0 && ` ${Math.abs(historial.datos.variacionMinorista)} %`}
                </strong>{" "}
                en el periodo
              </>
            )}
            .
          </p>
          <GraficoHistorial
            puntos={historial.datos.puntos}
            {...(presentacion && unidadDePresentacion(presentacion.codigo) === historial.datos.unidad
              ? { factor: presentacion.factor, unidad: presentacion.nombre.toLowerCase() }
              : { factor: 1, unidad: historial.datos.unidad })}
          />
        </section>
      )}

      {comparativa.datos && !comparativa.cargando && (
        <>
          <h2 className="seccion">Precio al consumidor</h2>
          {ahorroPosible(minoristas) > 0 && (
            <p className="ahorro">
              Entre el más barato y el más caro hay{" "}
              <strong>Bs {ahorroPosible(minoristas).toFixed(2)}</strong> de diferencia.
            </p>
          )}
          <div className="lista">
            {minoristas.map((item, i) => {
              // Con quién no se puede distinguir este precio: la diferencia es
              // menor que la incertidumbre. Entre empatados no se destaca a nadie.
              const empataCon = minoristas
                .filter((otro, j) => j !== i && (i === 0 || j === 0) && empatan(item.precio.rango, otro.precio.rango))
                .map((otro) => otro.mercado.nombre);
              return (
                <TarjetaMercado
                  key={item.mercado.codigo}
                  item={item}
                  // "Más conveniente" solo si se midió ahí, es reciente y gana
                  // de verdad: entre estimaciones o empates no hay a quién destacar.
                  destacado={
                    i === 0 && item.precio.procedencia === "observado" && !esPrecioViejo(item.precio) && empataCon.length === 0
                  }
                  empataCon={empataCon}
                />
              );
            })}
          </div>

          {mayoristas.length > 0 && (
            <>
              <h2 className="seccion">Precio mayorista</h2>
              <p className="tenue">
                Es otro nivel de la cadena: se compra por bulto, para revender. No compite con los de
                arriba.
              </p>
              <div className="lista">
                {mayoristas.map((item) => (
                  <TarjetaMercado key={item.mercado.codigo} item={item} />
                ))}
              </div>
            </>
          )}
        </>
      )}
    </>
  );
}

/** Cómo leer el mapa: qué es un punto lleno, uno hueco y uno atenuado. */
function LeyendaMapa() {
  return (
    <ul className="leyenda" aria-label="Cómo leer el mapa">
      <li>
        <span className="leyenda__punto leyenda__punto--observado" aria-hidden="true" /> Observado: alguien lo midió ahí
      </li>
      <li>
        <span className="leyenda__punto leyenda__punto--estimado" aria-hidden="true" /> Estimado desde el precio de la ciudad
      </li>
      <li>
        <span className="leyenda__punto leyenda__punto--viejo" aria-hidden="true" /> Atenuado: el dato tiene más de una semana
      </li>
    </ul>
  );
}
