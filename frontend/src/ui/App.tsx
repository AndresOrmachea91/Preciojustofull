import { useEffect, useMemo, useState } from "react";

import type { Producto } from "@/dominio/modelo";
import { ahorroPosible } from "@/dominio/servicio/ordenarPorConveniencia";
import { crearContenedor } from "@/infraestructura/contenedor";
import { MapaPuntosVenta } from "@/ui/componentes/MapaPuntosVenta";
import { PanelPunto } from "@/ui/componentes/PanelPunto";
import { TarjetaMercado } from "@/ui/componentes/TarjetaMercado";
import { useComparativa } from "@/ui/hooks/useComparativa";
import { useMapa } from "@/ui/hooks/useMapa";

export default function App() {
  const contenedor = useMemo(() => crearContenedor(), []);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [producto, setProducto] = useState<string | null>(null);
  const [seleccionado, setSeleccionado] = useState<string | null>(null);

  // El catálogo sale del caso de uso, no de una lista escrita a mano.
  useEffect(() => {
    void contenedor.catalogo.productos().then((lista) => {
      setProductos(lista);
      setProducto((actual) => actual ?? lista[0]?.codigo ?? null);
    });
  }, [contenedor]);

  const codigo = producto ?? "";
  const mapa = useMapa(contenedor, codigo);
  const comparativa = useComparativa(contenedor, codigo);
  const productoActual = productos.find((p) => p.codigo === producto) ?? null;
  const marcadorSeleccionado =
    mapa.datos?.marcadores.find((m) => m.mercado.codigo === seleccionado) ?? null;

  const minoristas = comparativa.datos?.opciones.filter((o) => o.mercado.nivelPrecio === "minorista") ?? [];
  const mayoristas = comparativa.datos?.opciones.filter((o) => o.mercado.nivelPrecio === "mayorista") ?? [];

  return (
    <div className="app">
      <header className="app__cabecera">
        <h1>PrecioJusto</h1>
        <p>¿Dónde conviene comprar hoy en La Paz?</p>
      </header>

      <nav className="selector" aria-label="Elegir producto">
        {productos.map((p) => (
          <button
            key={p.codigo}
            type="button"
            className={`selector__opcion${producto === p.codigo ? " selector__opcion--activa" : ""}`}
            aria-pressed={producto === p.codigo}
            onClick={() => setProducto(p.codigo)}
          >
            {p.nombre}
          </button>
        ))}
      </nav>

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
            marcadores={mapa.datos.marcadores}
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
    </div>
  );
}
