/**
 * El mapa. Leaflet es una librería de dibujo, no de dominio: este
 * componente recibe los marcadores YA resueltos por el caso de uso VerMapa
 * y solo los pinta. No sabe de HTTP ni de repositorios.
 *
 * C141: cada punto es un "pin" con su precio (de cerca) o un punto de color
 * (de lejos), con filtros por tipo flotando sobre el mapa, un fondo de mapa
 * suave que sigue el tema claro u oscuro, y vuelo suave al punto elegido.
 */
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import type { Coordenadas, MarcadorMapa, TipoPuntoVenta } from "@/dominio/modelo";
import { esPrecioViejo, etiquetaTipo } from "@/dominio/modelo";
import { Icono } from "@/ui/componentes/Iconos";

/** Centro del municipio de La Paz. */
const CENTRO_LA_PAZ: [number, number] = [-16.505, -68.13];
const ZOOM_INICIAL = 13;
/** Desde este zoom los pines muestran su precio; antes, solo el punto de color. */
const ZOOM_ETIQUETAS = 14;

/**
 * El fondo: las teselas de OpenStreetMap, sin clave. El tono (más suave de
 * día, invertido de noche) lo pone tema.css con un filtro sobre las teselas.
 */
const FONDO = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATRIBUCION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

type Filtro = "todos" | TipoPuntoVenta;

interface Props {
  readonly marcadores: readonly MarcadorMapa[];
  readonly seleccionado: string | null;
  readonly onSeleccionar: (codigo: string) => void;
  /** Dónde está la persona, si pidió ver lo cercano. */
  readonly ubicacion?: Coordenadas | null;
  /** Códigos de los lugares con una oferta vigente del casero para este producto. */
  readonly conOferta?: ReadonlySet<string>;
  /**
   * Lo que se muestra en la ventana que se abre sobre el punto elegido (C137):
   * sus puestos y precios. Recibe con qué avisar que cambió de tamaño.
   */
  readonly ventana?: (codigo: string, alCambiarTamano: () => void) => ReactNode;
  /** El botón "mi ubicación" del mapa; sin esto no aparece. */
  readonly onUbicar?: () => void;
}

const NINGUNO: ReadonlySet<string> = new Set();

/** "8,50" o "125": corto, para que entre en el pin. */
function montoCorto(monto: number): string {
  return monto >= 100 ? Math.round(monto).toString() : monto.toFixed(2).replace(".", ",");
}

function htmlDelPin({ mercado, precio }: MarcadorMapa, oferta: boolean): string {
  const clases = [
    "pin",
    `pin--${mercado.tipo}`,
    !precio ? "pin--sin-precio" : precio.procedencia === "estimado" ? "pin--estimado" : "pin--observado",
    precio && esPrecioViejo(precio) ? "pin--viejo" : "",
    oferta ? "pin--oferta" : "",
  ].filter(Boolean);
  const monto = precio ? `<span class="pin__precio">${montoCorto(precio.rango.centro)}</span>` : "";
  const estrella = oferta ? '<span class="pin__oferta" aria-hidden="true">★</span>' : "";
  return `<div class="${clases.join(" ")}"><span class="pin__punto"></span>${monto}${estrella}</div>`;
}

export function MapaPuntosVenta({
  marcadores,
  seleccionado,
  onSeleccionar,
  ubicacion = null,
  conOferta = NINGUNO,
  ventana,
  onUbicar,
}: Props) {
  const contenedor = useRef<HTMLDivElement>(null);
  const mapa = useRef<L.Map | null>(null);
  const capa = useRef<L.LayerGroup | null>(null);
  const [cerca, setCerca] = useState(false);
  const [filtro, setFiltro] = useState<Filtro>("todos");
  const [soloOfertas, setSoloOfertas] = useState(false);

  // El mapa se crea una vez; los marcadores se redibujan cuando cambian.
  useEffect(() => {
    if (!contenedor.current || mapa.current) return;
    const m = L.map(contenedor.current, { zoomControl: false }).setView(CENTRO_LA_PAZ, ZOOM_INICIAL);
    L.control.zoom({ position: "bottomright", zoomInTitle: "Acercar", zoomOutTitle: "Alejar" }).addTo(m);
    L.tileLayer(FONDO, { maxZoom: 19, attribution: ATRIBUCION }).addTo(m);
    m.on("zoomend", () => setCerca(m.getZoom() >= ZOOM_ETIQUETAS));
    capa.current = L.layerGroup().addTo(m);
    mapa.current = m;
    return () => {
      m.remove();
      mapa.current = null;
      capa.current = null;
    };
  }, []);

  const visibles = useMemo(
    () =>
      marcadores.filter(
        ({ mercado }) =>
          (filtro === "todos" || mercado.tipo === filtro) && (!soloOfertas || conOferta.has(mercado.codigo)),
      ),
    [marcadores, filtro, soloOfertas, conOferta],
  );

  // Los puntos se crean cuando cambian los datos o el filtro; elegir uno solo
  // cambia la clase del anterior y del nuevo, no redibuja todos.
  const puntos = useRef(new Map<string, L.Marker>());
  const elegido = useRef<string | null>(null);

  const marcar = useCallback((codigo: string | null, activo: boolean) => {
    const punto = codigo ? puntos.current.get(codigo) : undefined;
    if (!punto) return;
    punto.getElement()?.querySelector(".pin")?.classList.toggle("pin--activo", activo);
    punto.setZIndexOffset(activo ? 1000 : 0);
  }, []);

  useEffect(() => {
    const grupo = capa.current;
    if (!grupo) return;
    grupo.clearLayers();
    puntos.current.clear();
    for (const marcador of visibles) {
      const { mercado } = marcador;
      if (mercado.latitud === undefined || mercado.longitud === undefined) continue;
      const oferta = conOferta.has(mercado.codigo);
      const punto = L.marker([mercado.latitud, mercado.longitud], {
        icon: L.divIcon({ html: htmlDelPin(marcador, oferta), className: "pin-icono", iconSize: [0, 0] }),
        keyboard: true,
        riseOnHover: true,
      });
      punto.bindTooltip(oferta ? `${mercado.nombre} · con oferta` : mercado.nombre, {
        direction: "top",
        offset: [0, -16],
        className: "tooltip-vidrio",
      });
      punto.on("click", () => onSeleccionar(mercado.codigo));
      punto.on("keypress", (e: L.LeafletKeyboardEvent) => {
        if (e.originalEvent.key === "Enter") onSeleccionar(mercado.codigo);
      });
      punto.addTo(grupo);
      punto.getElement()?.setAttribute("aria-label", mercado.nombre);
      puntos.current.set(mercado.codigo, punto);
    }
    elegido.current = null;
  }, [visibles, onSeleccionar, conOferta]);

  // Vuela al elegido: lo acerca y deja lugar arriba para la ventana.
  const volando = useRef(false);
  useEffect(() => {
    if (elegido.current === seleccionado) return;
    marcar(elegido.current, false);
    marcar(seleccionado, true);
    elegido.current = seleccionado;
    const m = mapa.current;
    const punto = seleccionado ? puntos.current.get(seleccionado) : undefined;
    if (!m || !punto) return;
    const zoom = Math.max(m.getZoom(), 15);
    const destino = m.unproject(m.project(punto.getLatLng(), zoom).subtract([0, 180]), zoom);
    volando.current = true;
    m.flyTo(destino, zoom, { duration: 0.6 });
    m.once("moveend", () => {
      volando.current = false;
    });
  }, [seleccionado, visibles, marcar]);

  // La persona: un punto azul que late, distinto de cualquier mercado.
  const aqui = useRef<L.Marker | null>(null);
  useEffect(() => {
    aqui.current?.remove();
    aqui.current = null;
    if (!mapa.current || !ubicacion) return;
    aqui.current = L.marker([ubicacion.latitud, ubicacion.longitud], {
      icon: L.divIcon({ html: '<span class="yo"></span>', className: "pin-icono", iconSize: [0, 0] }),
      interactive: false,
      keyboard: false,
      zIndexOffset: 2000,
    })
      .bindTooltip("Usted está aquí", { direction: "top", offset: [0, -10], className: "tooltip-vidrio" })
      .addTo(mapa.current);
    mapa.current.flyTo([ubicacion.latitud, ubicacion.longitud], 15, { duration: 0.8 });
  }, [ubicacion]);

  // La ventana del punto elegido: un popup de Leaflet cuyo contenido dibuja
  // React (createPortal), así puede cargar datos y usar los componentes de siempre.
  const [nodoVentana, setNodoVentana] = useState<HTMLDivElement | null>(null);
  const popup = useRef<L.Popup | null>(null);
  const conVentana = ventana !== undefined;
  useEffect(() => {
    popup.current?.remove();
    popup.current = null;
    setNodoVentana(null);
    const m = mapa.current;
    const punto = seleccionado ? puntos.current.get(seleccionado) : undefined;
    if (!conVentana || !m || !punto) return;
    const nodo = document.createElement("div");
    const ventanaNueva = L.popup({
      maxWidth: 320,
      minWidth: 260,
      maxHeight: 360,
      className: "ventana-mapa",
      offset: [0, -14],
      // Arriba deja libres los filtros; a la derecha, los botones.
      autoPanPaddingTopLeft: [16, 64],
      autoPanPaddingBottomRight: [64, 16],
    })
      .setLatLng(punto.getLatLng())
      .setContent(nodo);
    ventanaNueva.on("remove", () => {
      if (elegido.current === seleccionado) marcar(seleccionado, false);
    });
    popup.current = ventanaNueva;
    setNodoVentana(nodo);
    // Si el mapa está volando al punto, la ventana se abre al llegar: abrirla
    // antes cortaría el vuelo para acomodarse.
    const abrir = () => {
      if (popup.current === ventanaNueva) ventanaNueva.openOn(m);
    };
    if (volando.current) m.once("moveend", abrir);
    else abrir();
    return () => {
      m.off("moveend", abrir);
      ventanaNueva.remove();
      if (popup.current === ventanaNueva) popup.current = null;
    };
  }, [seleccionado, visibles, conVentana, marcar]);
  const acomodar = useCallback(() => popup.current?.update(), []);

  const verTodo = () => {
    const m = mapa.current;
    const conLugar = visibles.filter((v) => v.mercado.latitud !== undefined && v.mercado.longitud !== undefined);
    if (!m) return;
    if (conLugar.length === 0) {
      m.flyTo(CENTRO_LA_PAZ, ZOOM_INICIAL, { duration: 0.6 });
      return;
    }
    m.flyToBounds(L.latLngBounds(conLugar.map((v) => [v.mercado.latitud!, v.mercado.longitud!])), {
      padding: [40, 40],
      duration: 0.6,
    });
  };

  // Los filtros: solo los tipos que hay, con cuántos puntos tiene cada uno.
  const tipos = useMemo(() => {
    const cuenta = new Map<TipoPuntoVenta, number>();
    for (const { mercado } of marcadores) cuenta.set(mercado.tipo, (cuenta.get(mercado.tipo) ?? 0) + 1);
    return [...cuenta.entries()];
  }, [marcadores]);
  const ofertasEnMapa = marcadores.filter((m) => conOferta.has(m.mercado.codigo)).length;

  return (
    <div className={`mapa-marco${cerca ? " mapa-marco--cerca" : ""}`}>
      <div
        ref={contenedor}
        className="mapa"
        role="region"
        aria-label="Mapa de puntos de venta de La Paz"
        data-marcadores={marcadores.length}
      />

      {tipos.length > 1 || ofertasEnMapa > 0 ? (
        <div className="mapa__filtros" role="group" aria-label="Qué mostrar en el mapa">
          <button type="button" className="filtro" aria-pressed={filtro === "todos"} onClick={() => setFiltro("todos")}>
            Todos <span className="filtro__cuenta">{marcadores.length}</span>
          </button>
          {tipos.map(([tipo, n]) => (
            <button
              key={tipo}
              type="button"
              className={`filtro filtro--${tipo}`}
              aria-pressed={filtro === tipo}
              onClick={() => setFiltro(filtro === tipo ? "todos" : tipo)}
            >
              <span className="filtro__punto" aria-hidden="true" />
              {etiquetaTipo(tipo)} <span className="filtro__cuenta">{n}</span>
            </button>
          ))}
          {ofertasEnMapa > 0 && (
            <button
              type="button"
              className="filtro filtro--oferta"
              aria-pressed={soloOfertas}
              onClick={() => setSoloOfertas(!soloOfertas)}
            >
              ★ Con oferta <span className="filtro__cuenta">{ofertasEnMapa}</span>
            </button>
          )}
        </div>
      ) : null}

      <div className="mapa__acciones">
        <button type="button" className="mapa__boton" onClick={verTodo} aria-label="Ver todos los puntos">
          <Icono nombre="mercado" tamano={18} />
        </button>
        {onUbicar && (
          <button type="button" className="mapa__boton" onClick={onUbicar} aria-label="Ir a mi ubicación">
            <Icono nombre="ubicacion" tamano={18} />
          </button>
        )}
      </div>

      {!cerca && visibles.some((v) => v.precio) && (
        <p className="mapa__pista" aria-hidden="true">
          Acérquese para ver los precios en el mapa
        </p>
      )}

      {nodoVentana && seleccionado && ventana && createPortal(ventana(seleccionado, acomodar), nodoVentana)}
    </div>
  );
}
