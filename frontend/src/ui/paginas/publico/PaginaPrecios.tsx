import { useEffect, useMemo, useState } from "react";

import type { Producto } from "@/dominio/modelo";
import { precioEnPresentacion, presentacionBase, unidadDePresentacion } from "@/dominio/modelo";
import { ahorroPosible } from "@/dominio/servicio/ordenarPorConveniencia";
import type { Contenedor } from "@/infraestructura/contenedor";
import { MapaPuntosVenta } from "@/ui/componentes/MapaPuntosVenta";
import { PanelPunto } from "@/ui/componentes/PanelPunto";
import { SelectorProducto } from "@/ui/componentes/SelectorProducto";
import { TarjetaMercado } from "@/ui/componentes/TarjetaMercado";
import { useComparativa } from "@/ui/hooks/useComparativa";
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
      </div>

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
        <div className="mapa-y-panel">
          <MapaPuntosVenta
            marcadores={marcadores}
            seleccionado={seleccionado}
            onSeleccionar={setSeleccionado}
          />
          <PanelPunto marcador={marcadorSeleccionado} producto={productoActual} />
        </div>
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
            {minoristas.map((item, i) => (
              // "Más conveniente" solo si se midió ahí: entre estimaciones
              // iguales no hay nada que destacar.
              <TarjetaMercado
                key={item.mercado.codigo}
                item={item}
                destacado={i === 0 && item.precio.procedencia === "observado"}
              />
            ))}
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
