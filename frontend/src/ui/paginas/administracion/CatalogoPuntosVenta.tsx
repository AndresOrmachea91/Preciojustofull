import { useCallback, useEffect, useState, type FormEvent } from "react";

import type { DatosPuntoVenta } from "@/aplicacion/puertos";
import { TIPOS_PUNTO_VENTA, etiquetaTipo, type Mercado, type TipoPuntoVenta } from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { MensajeAviso, MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { MapaSelectorUbicacion } from "@/ui/componentes/MapaSelectorUbicacion";

const VACIO: DatosPuntoVenta = {
  nombre: "",
  tipo: "mercado",
  zona: "",
  macrodistrito: "",
  latitud: null,
  longitud: null,
  codigoPadre: null,
};

/** Mercados, distribuidores y mayoristas: alta, edición (con su lugar en el mapa) y baja lógica. */
export function CatalogoPuntosVenta({ contenedor }: { contenedor: Contenedor }) {
  const [lista, setLista] = useState<Mercado[] | null>(null);
  const [editando, setEditando] = useState<{ codigo: string | null; datos: DatosPuntoVenta } | null>(null);
  const [aEliminar, setAEliminar] = useState<string | null>(null);
  const [filtro, setFiltro] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const cargar = useCallback(() => {
    contenedor.administrarCatalogo.puntosVenta().then(setLista, (e) => setError(textoDeError(e)));
  }, [contenedor]);
  useEffect(cargar, [cargar]);

  async function eliminar(codigo: string) {
    setError(null);
    try {
      await contenedor.administrarCatalogo.eliminarPuntoVenta(codigo);
      setAviso(`${lista?.find((m) => m.codigo === codigo)?.nombre ?? codigo} se eliminó del catálogo.`);
      setAEliminar(null);
      cargar();
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  const mercados = lista?.filter((m) => m.tipo === "mercado" && !m.codigoPadre) ?? [];
  const visibles =
    lista?.filter((m) => `${m.nombre} ${m.zona} ${m.macrodistrito}`.toLowerCase().includes(filtro.toLowerCase())) ?? [];

  return (
    <>
      {editando ? (
        <FormularioPunto
          contenedor={contenedor}
          codigo={editando.codigo}
          inicial={editando.datos}
          mercados={mercados}
          alTerminar={(guardado) => {
            setEditando(null);
            if (guardado) {
              setAviso(`${guardado.nombre} quedó guardado.`);
              cargar();
            }
          }}
        />
      ) : (
        <div className="barra">
          <button type="button" className="boton" onClick={() => setEditando({ codigo: null, datos: VACIO })}>
            Nuevo punto de venta
          </button>
          <input
            className="barra__buscar"
            type="search"
            placeholder="Buscar por nombre o zona"
            aria-label="Buscar punto de venta"
            value={filtro}
            onChange={(e) => setFiltro(e.target.value)}
          />
        </div>
      )}

      <MensajeError texto={error} />
      {!error && <MensajeAviso texto={aviso} />}
      {!lista && !error && <p className="estado">Cargando puntos de venta…</p>}

      {lista && (
        <div className="tabla-envoltura">
          <table className="tabla" aria-label="Puntos de venta">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Tipo</th>
                <th>Zona</th>
                <th>En el mapa</th>
                <th aria-label="Acciones" />
              </tr>
            </thead>
            <tbody>
              {visibles.map((m) => (
                <tr key={m.codigo}>
                  <td>
                    {m.nombre}
                    {m.codigoPadre && <span className="tenue"> · sector de {m.codigoPadre}</span>}
                  </td>
                  <td>{etiquetaTipo(m.tipo)}</td>
                  <td>{m.macrodistrito || m.zona || <span className="tenue">—</span>}</td>
                  <td>{m.latitud !== undefined ? "Sí" : <span className="tenue">Falta</span>}</td>
                  <td className="tabla__acciones">
                    {aEliminar === m.codigo ? (
                      <>
                        <span className="tenue">¿Eliminar?</span>
                        <button type="button" className="boton boton--peligro" onClick={() => void eliminar(m.codigo)}>
                          Sí, eliminar
                        </button>
                        <button type="button" className="boton boton--suave" onClick={() => setAEliminar(null)}>
                          No
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          type="button"
                          className="boton boton--suave"
                          aria-label={`Editar ${m.nombre}`}
                          onClick={() =>
                            setEditando({
                              codigo: m.codigo,
                              datos: {
                                nombre: m.nombre,
                                tipo: m.tipo,
                                zona: m.zona,
                                macrodistrito: m.macrodistrito,
                                latitud: m.latitud ?? null,
                                longitud: m.longitud ?? null,
                                codigoPadre: m.codigoPadre,
                              },
                            })
                          }
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          className="boton boton--suave"
                          aria-label={`Eliminar ${m.nombre}`}
                          onClick={() => setAEliminar(m.codigo)}
                        >
                          Eliminar
                        </button>
                      </>
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

function FormularioPunto({
  contenedor,
  codigo,
  inicial,
  mercados,
  alTerminar,
}: {
  contenedor: Contenedor;
  codigo: string | null;
  inicial: DatosPuntoVenta;
  mercados: Mercado[];
  alTerminar: (guardado: Mercado | null) => void;
}) {
  const [datos, setDatos] = useState<DatosPuntoVenta>(inicial);
  const [error, setError] = useState<string | null>(null);
  const cambiar = (parcial: Partial<DatosPuntoVenta>) => setDatos((d) => ({ ...d, ...parcial }));

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    try {
      alTerminar(await contenedor.administrarCatalogo.guardarPuntoVenta(codigo, datos));
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  return (
    <form
      className="formulario formulario--recuadro"
      onSubmit={(e) => void enviar(e)}
      aria-label={codigo ? "Editar punto de venta" : "Nuevo punto de venta"}
    >
      <div className="formulario__fila">
        <label className="campo">
          <span>Nombre</span>
          <input required value={datos.nombre} onChange={(e) => cambiar({ nombre: e.target.value })} />
        </label>
        <label className="campo">
          <span>Tipo</span>
          <select value={datos.tipo} onChange={(e) => cambiar({ tipo: e.target.value as TipoPuntoVenta })}>
            {TIPOS_PUNTO_VENTA.map((t) => (
              <option key={t} value={t}>
                {etiquetaTipo(t)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="formulario__fila">
        <label className="campo">
          <span>Zona</span>
          <input value={datos.zona} onChange={(e) => cambiar({ zona: e.target.value })} />
        </label>
        <label className="campo">
          <span>Macrodistrito</span>
          <input value={datos.macrodistrito} onChange={(e) => cambiar({ macrodistrito: e.target.value })} />
        </label>
      </div>
      {datos.tipo === "mercado" && (
        <label className="campo">
          <span>Es un sector de (opcional)</span>
          <select
            value={datos.codigoPadre ?? ""}
            onChange={(e) => cambiar({ codigoPadre: e.target.value || null })}
          >
            <option value="">No, es un mercado propio</option>
            {mercados
              .filter((m) => m.codigo !== codigo)
              .map((m) => (
                <option key={m.codigo} value={m.codigo}>
                  {m.nombre}
                </option>
              ))}
          </select>
        </label>
      )}

      <div className="campo">
        <span>Ubicación: haga clic en el mapa</span>
        <MapaSelectorUbicacion
          latitud={datos.latitud}
          longitud={datos.longitud}
          onCambiar={(latitud, longitud) => cambiar({ latitud, longitud })}
        />
        <small className="tenue">
          {datos.latitud !== null && datos.longitud !== null
            ? `Marcado en ${datos.latitud}, ${datos.longitud}`
            : "Sin ubicación todavía: no aparecerá en el mapa de precios."}
        </small>
      </div>
      <div className="formulario__fila">
        <label className="campo">
          <span>Latitud</span>
          <input
            type="number"
            step="any"
            value={datos.latitud ?? ""}
            onChange={(e) => cambiar({ latitud: e.target.value === "" ? null : Number(e.target.value) })}
          />
        </label>
        <label className="campo">
          <span>Longitud</span>
          <input
            type="number"
            step="any"
            value={datos.longitud ?? ""}
            onChange={(e) => cambiar({ longitud: e.target.value === "" ? null : Number(e.target.value) })}
          />
        </label>
      </div>

      <MensajeError texto={error} />
      <div className="formulario__botones">
        <button type="submit" className="boton">
          {codigo ? "Guardar cambios" : "Crear punto de venta"}
        </button>
        <button type="button" className="boton boton--suave" onClick={() => alTerminar(null)}>
          Cancelar
        </button>
      </div>
    </form>
  );
}
