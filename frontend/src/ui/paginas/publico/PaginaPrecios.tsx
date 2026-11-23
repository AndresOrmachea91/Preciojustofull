import { useEffect, useMemo, useState } from "react";

import type { Oferta, PrecioEnMercado, Producto, Usuario } from "@/dominio/modelo";
import { bs,
  agruparPorPrecio,
  empatan,
  esPrecioViejo,
  precioEnPresentacion,
  presentacionBase,
  publicaRango,
  nombreDelPuesto,
  textoDistancia,
  unidadDePresentacion,
  ZONAS_DE_LA_PAZ,
} from "@/dominio/modelo";
import { ahorroPosible } from "@/dominio/servicio/ordenarPorConveniencia";
import type { Contenedor } from "@/infraestructura/contenedor";
import { GraficoHistorial } from "@/ui/componentes/GraficoHistorial";
import { Icono } from "@/ui/componentes/Iconos";
import { MapaPuntosVenta, type RamasDelMercado } from "@/ui/componentes/MapaPuntosVenta";
import { PanelPunto, type ResumenDelMapa } from "@/ui/componentes/PanelPunto";
import { Procedencia } from "@/ui/componentes/Procedencia";
import { SelectorProducto } from "@/ui/componentes/SelectorProducto";
import { TarjetaMercado } from "@/ui/componentes/TarjetaMercado";
import { VentanaMercado } from "@/ui/componentes/VentanaMercado";
import { VentanaPuesto } from "@/ui/componentes/VentanaPuesto";
import { useCercania } from "@/ui/hooks/useCercania";
import { useComparativa } from "@/ui/hooks/useComparativa";
import { useHistorial } from "@/ui/hooks/useHistorial";
import { useMapa } from "@/ui/hooks/useMapa";
import { useRamasDelMercado } from "@/ui/hooks/useRamasDelMercado";
import { hrefMercado } from "@/ui/hooks/useRuta";

// Con qué producto abre la pantalla: uno que tenga precio en los 88 puntos.
// Si el catálogo no lo trae, se usa el primero.
const PRODUCTO_INICIAL = "arroz_primera";

export function PaginaPrecios({ contenedor, usuario = null }: { contenedor: Contenedor; usuario?: Usuario | null }) {
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

  // Las ofertas de los caseros para este producto (C133): anillo dorado en el mapa.
  const [ofertas, setOfertas] = useState<Oferta[]>([]);
  useEffect(() => {
    if (!codigo) return;
    let vigente = true;
    contenedor.ofertas.vigentes({ producto: codigo }).then(
      (o) => vigente && setOfertas(o),
      () => vigente && setOfertas([]),
    );
    return () => {
      vigente = false;
    };
  }, [contenedor, codigo]);
  const conOferta = useMemo(() => new Set(ofertas.map((o) => o.codigoMercado)), [ofertas]);
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

  // Los puestos del mercado elegido se abren como ramas en el mapa (C143).
  // Un lugar con un solo puesto (una distribuidora) abre su ventana de siempre.
  const delElegido = useRamasDelMercado(contenedor, seleccionado, producto);
  const ramas = useMemo((): RamasDelMercado | null => {
    if (!delElegido || !marcadorSeleccionado || delElegido.codigoMercado !== seleccionado) return null;
    const lista =
      delElegido.puestos.length < 2
        ? []
        : delElegido.puestos.map(({ puesto, articulos }) => {
            const buscado = articulos.find((a) => a.codigoProducto === producto);
            return {
              clave: puesto.numero,
              numero: puesto.esLocal ? "•" : puesto.numero,
              titulo: nombreDelPuesto(puesto),
              foto: puesto.foto,
              precio: buscado ? buscado.monto : null,
              agotado: buscado?.disponibilidad === "agotado",
              oferta: delElegido.ofertas.some((o) => o.numeroPuesto === puesto.numero),
            };
          });
    return {
      codigo: delElegido.codigoMercado,
      nombre: marcadorSeleccionado.mercado.nombre,
      enlace: hrefMercado(delElegido.codigoMercado),
      lista,
    };
  }, [delElegido, marcadorSeleccionado, seleccionado, producto]);
  const preciosPuestos = useMemo(() => {
    if (!delElegido || delElegido.codigoMercado !== seleccionado) return [];
    return delElegido.puestos.flatMap(({ puesto, articulos }) => {
      const a = articulos.find((x) => x.codigoProducto === producto);
      return a
        ? [{ numero: puesto.numero, titulo: nombreDelPuesto(puesto), monto: a.monto, presentacion: a.presentacion, agotado: a.disponibilidad === "agotado" }]
        : [];
    });
  }, [delElegido, seleccionado, producto]);

  // Solo se ofrecen presentaciones de la magnitud en que llegó el precio: si
  // la fuente publica por unidad, no hay "por arroba" que mostrar.
  const unidadDelPrecio = mapa.datos?.marcadores.find((m) => m.precio)?.precio?.unidad;
  const presentacionesUtiles =
    productoActual?.presentaciones.filter((p) => !unidadDelPrecio || unidadDePresentacion(p.codigo) === unidadDelPrecio) ??
    [];

  const resumen: ResumenDelMapa | null = mapa.datos
    ? {
        ...mapa.datos.resumen,
        // La referencia que se muestra antes de elegir un punto: un mercado estimado, que es la ciudad con su ajuste.
        referencia:
          (
            marcadores.find((m) => m.precio?.procedencia === "estimado" && m.mercado.tipo === "mercado") ??
            marcadores.find((m) => m.precio)
          )?.precio ?? null,
        ofertas: ofertas.length,
      }
    : null;

  const opciones = comparativa.datos?.opciones.map(escalar) ?? [];
  const minoristas = opciones.filter((o) => o.mercado.nivelPrecio === "minorista");
  const mayoristas = opciones.filter((o) => o.mercado.nivelPrecio === "mayorista");
  // La respuesta corta, al lado del mapa: los tres lugares más baratos donde alguien midió el precio.
  // Van por precio; si el dato ya tiene más de una semana, la fila lo dice.
  const masBaratos = minoristas
    .filter((o) => o.precio.procedencia === "observado")
    .sort((x, y) => x.precio.rango.centro - y.precio.rango.centro)
    .slice(0, 3);

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

      {/* Si el GPS no responde (o está apagado), la zona sirve igual: "estoy en Sopocachi". */}
      {(cercania.error || cercania.ubicacion) && (
        <div className="zonas" role="group" aria-label="Elegir mi zona">
          <span className="tenue">{cercania.error ? "O elija su zona:" : "¿Está en otra zona?"}</span>
          {ZONAS_DE_LA_PAZ.map((z) => (
            <button
              key={z.nombre}
              type="button"
              className="filtro"
              aria-pressed={cercania.zona === z.nombre}
              onClick={() => cercania.elegirZona(z)}
            >
              {z.nombre}
            </button>
          ))}
        </div>
      )}

      {cercania.error && (
        <p className="estado estado--error" role="alert">
          {cercania.error}
        </p>
      )}
      {cercania.ubicacion && (
        <section className="cercanos" aria-labelledby="titulo-cercanos">
          <div className="cercanos__cabeza">
            <h2 id="titulo-cercanos" className="seccion">
              {cercania.zona ? `Mercados cerca de ${cercania.zona}` : "Mercados cerca de usted"}
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
                      <span className="cercanos__nombre">
                        {marcador.mercado.nombre}
                        {conOferta.has(marcador.mercado.codigo) && (
                          <span className="cercanos__oferta" title="Un casero tiene una oferta">
                            {" "}
                            ★ oferta
                          </span>
                        )}
                      </span>
                      <span className="tenue">{textoDistancia(distanciaKm)}</span>
                      {precio && (
                        <span className="cercanos__precio">
                          Bs {bs(precio.rango.centro)}
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
              conOferta={conOferta}
              onUbicar={() => void cercania.buscar()}
              ramas={seleccionado ? ramas : null}
              onCerrar={() => setSeleccionado(null)}
              ventanaRama={(clave, alCambiarTamano) => {
                const datos = delElegido?.puestos.find((x) => x.puesto.numero === clave);
                return datos && marcadorSeleccionado ? (
                  <VentanaPuesto
                    mercado={marcadorSeleccionado.mercado}
                    datos={datos}
                    ofertas={delElegido!.ofertas.filter((o) => o.numeroPuesto === clave)}
                    codigoProducto={producto}
                    alCambiarTamano={alCambiarTamano}
                  />
                ) : null;
              }}
              ventana={(codigo, alCambiarTamano) => {
                const marcador = marcadores.find((m) => m.mercado.codigo === codigo);
                return marcador ? (
                  <VentanaMercado
                    contenedor={contenedor}
                    marcador={marcador}
                    producto={productoActual}
                    alCambiarTamano={alCambiarTamano}
                  />
                ) : null;
              }}
            />
            <PanelPunto
              marcador={marcadorSeleccionado}
              producto={productoActual}
              presentacion={presentacion}
              resumen={resumen}
              ofertas={ofertas.filter((o) => o.codigoMercado === seleccionado)}
              contenedor={contenedor}
              usuario={usuario}
              masBaratos={masBaratos}
              preciosPuestos={preciosPuestos}
              alElegir={setSeleccionado}
            />
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
              <strong>Bs {bs(ahorroPosible(minoristas))}</strong> de diferencia.
            </p>
          )}
          {minoristas.some((o) => publicaRango(o.mercado.tipo)) && (
            <p className="tenue lista__nota">
              En los mercados el precio cambia de un puesto a otro: por eso se muestra un rango y no un solo número.
            </p>
          )}
          <ListaDePrecios items={minoristas} conDestacado />

          {mayoristas.length > 0 && (
            <>
              <h2 className="seccion">Precio mayorista</h2>
              <p className="tenue">
                Es otro nivel de la cadena: se compra por bulto, para revender. No compite con los de
                arriba.
              </p>
              <ListaDePrecios items={mayoristas} />
            </>
          )}
        </>
      )}
    </>
  );
}

/**
 * Los lugares de una lista de precios. Los que tienen exactamente el mismo
 * precio estimado van juntos en una sola tarjeta: 88 tarjetas idénticas no
 * dicen más que una. Lo medido en un lugar siempre va aparte.
 */
function ListaDePrecios({ items, conDestacado = false }: { items: readonly PrecioEnMercado[]; conDestacado?: boolean }) {
  // Con quién no se puede distinguir cada precio: la diferencia es menor que
  // la incertidumbre. Entre empatados no se destaca a nadie.
  const empates = new Map<string, string[]>();
  items.forEach((item, i) => {
    empates.set(
      item.mercado.codigo,
      items
        .filter((otro, j) => j !== i && (i === 0 || j === 0) && empatan(item.precio.rango, otro.precio.rango))
        .map((otro) => otro.mercado.nombre),
    );
  });
  return (
    <div className="lista">
      {agruparPorPrecio(items).map((grupo) => {
        const [primero] = grupo.items;
        if (grupo.items.length > 1) return <TarjetaGrupo key={grupo.clave} items={grupo.items} />;
        const empataCon = empates.get(primero.mercado.codigo) ?? [];
        return (
          <TarjetaMercado
            key={grupo.clave}
            item={primero}
            // "Más conveniente" solo si se midió ahí, es reciente y gana de
            // verdad: entre estimaciones o empates no hay a quién destacar.
            destacado={
              conDestacado &&
              primero === items[0] &&
              primero.precio.procedencia === "observado" &&
              !esPrecioViejo(primero.precio) &&
              empataCon.length === 0
            }
            empataCon={grupo.items.length === 1 && primero.precio.procedencia === "observado" ? empataCon : []}
          />
        );
      })}
    </div>
  );
}

/** Varios lugares con el mismo precio estimado, en una sola tarjeta con sus nombres. */
function TarjetaGrupo({ items }: { items: readonly PrecioEnMercado[] }) {
  const { precio, mercado } = items[0];
  const rango = publicaRango(mercado.tipo);
  return (
    <article className={`tarjeta tarjeta--estimado tarjeta--grupo${esPrecioViejo(precio) ? " precio--viejo" : ""}`}>
      <header className="tarjeta__cabecera">
        <div>
          <h3 className="tarjeta__nombre">{items.length} lugares con el mismo precio</h3>
          <p className="tarjeta__zona">
            Nadie lo midió en ninguno de ellos: todos salen del precio de la ciudad.
          </p>
        </div>
        <Procedencia valor="estimado" />
      </header>
      <p className="tarjeta__precio">
        {rango ? (
          <>
            Bs {bs(precio.rango.minimo)} <span className="tenue">a</span> {bs(precio.rango.maximo)}
          </>
        ) : (
          <>Bs {bs(precio.rango.centro)}</>
        )}
        <span className="tarjeta__unidad"> por {precio.unidad}</span>
      </p>
      <details className="tarjeta__lugares">
        <summary>Ver los {items.length} lugares</summary>
        <ul className="lugares">
          {items.map((x) => (
            <li key={x.mercado.codigo}>
              <a href={hrefMercado(x.mercado.codigo)}>{x.mercado.nombre}</a>
            </li>
          ))}
        </ul>
      </details>
    </article>
  );
}

/** Cómo leer el mapa: el color dice qué es; el borde, de dónde sale el precio. */
function LeyendaMapa() {
  return (
    <ul className="leyenda" aria-label="Cómo leer el mapa">
      <li>
        <span className="leyenda__pin leyenda__pin--observado" aria-hidden="true">8,50</span> Observado: alguien lo midió ahí
      </li>
      <li>
        <span className="leyenda__pin leyenda__pin--estimado" aria-hidden="true">8,50</span> Estimado desde el precio de la ciudad
      </li>
      <li>
        <span className="leyenda__pin leyenda__pin--viejo" aria-hidden="true">8,50</span> Atenuado: el dato tiene más de una semana
      </li>
      <li>
        <span className="leyenda__pin leyenda__pin--oferta" aria-hidden="true">★</span> Estrella dorada: un casero tiene una oferta
      </li>
    </ul>
  );
}
