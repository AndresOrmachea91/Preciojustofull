import { useCallback, useEffect, useState, type FormEvent } from "react";

import type { DatosProducto } from "@/aplicacion/puertos";
import {
  CATEGORIAS,
  NOMBRE_UNIDAD_BASE,
  PRESENTACIONES_POR_UNIDAD,
  type Producto,
  type UnidadBase,
} from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";

const VACIO: DatosProducto = {
  nombre: "",
  categoria: "abarrote",
  unidadBase: "kg",
  presentaciones: PRESENTACIONES_POR_UNIDAD.kg.map((p) => p.codigo),
  diasConservacion: 30,
};

function mensaje(e: unknown): string {
  return e instanceof Error ? e.message : "No se pudo completar la operación";
}

function nombreCategoria(codigo: string): string {
  return CATEGORIAS.find((c) => c.codigo === codigo)?.nombre ?? codigo;
}

/** Productos de la canasta: alta, edición (con sus presentaciones de venta) y baja lógica. */
export function CatalogoProductos({ contenedor }: { contenedor: Contenedor }) {
  const [lista, setLista] = useState<Producto[] | null>(null);
  const [editando, setEditando] = useState<{ codigo: string | null; datos: DatosProducto } | null>(null);
  const [aEliminar, setAEliminar] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const cargar = useCallback(() => {
    contenedor.administrarCatalogo.productos().then(setLista, (e) => setError(mensaje(e)));
  }, [contenedor]);
  useEffect(cargar, [cargar]);

  async function eliminar(codigo: string) {
    setError(null);
    try {
      await contenedor.administrarCatalogo.eliminarProducto(codigo);
      setAviso(`${lista?.find((p) => p.codigo === codigo)?.nombre ?? codigo} se eliminó del catálogo.`);
      setAEliminar(null);
      cargar();
    } catch (e) {
      setError(mensaje(e));
    }
  }

  return (
    <>
      {editando ? (
        <FormularioProducto
          contenedor={contenedor}
          codigo={editando.codigo}
          inicial={editando.datos}
          alTerminar={(guardado) => {
            setEditando(null);
            if (guardado) {
              setAviso(`${guardado.nombre} quedó guardado.`);
              cargar();
            }
          }}
        />
      ) : (
        <button type="button" className="boton" onClick={() => setEditando({ codigo: null, datos: VACIO })}>
          Nuevo producto
        </button>
      )}

      {error && (
        <p className="estado estado--error" role="alert">
          {error}
        </p>
      )}
      {aviso && !error && (
        <p className="aviso" role="status">
          {aviso}
        </p>
      )}
      {!lista && !error && <p className="estado">Cargando productos…</p>}

      {lista && (
        <div className="tabla-envoltura">
          <table className="tabla" aria-label="Productos">
            <thead>
              <tr>
                <th>Producto</th>
                <th>Categoría</th>
                <th>Se vende por</th>
                <th aria-label="Acciones" />
              </tr>
            </thead>
            <tbody>
              {lista.map((p) => (
                <tr key={p.codigo}>
                  <td>{p.nombre}</td>
                  <td>{nombreCategoria(p.categoria)}</td>
                  <td>{p.presentaciones.map((x) => x.nombre).join(", ")}</td>
                  <td className="tabla__acciones">
                    {aEliminar === p.codigo ? (
                      <>
                        <span className="tenue">¿Eliminar?</span>
                        <button type="button" className="boton boton--peligro" onClick={() => void eliminar(p.codigo)}>
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
                          aria-label={`Editar ${p.nombre}`}
                          onClick={() =>
                            setEditando({
                              codigo: p.codigo,
                              datos: {
                                nombre: p.nombre,
                                categoria: p.categoria,
                                unidadBase: p.unidadBase,
                                presentaciones: p.presentaciones.map((x) => x.codigo),
                                diasConservacion: p.diasConservacion,
                              },
                            })
                          }
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          className="boton boton--suave"
                          aria-label={`Eliminar ${p.nombre}`}
                          onClick={() => setAEliminar(p.codigo)}
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

function FormularioProducto({
  contenedor,
  codigo,
  inicial,
  alTerminar,
}: {
  contenedor: Contenedor;
  codigo: string | null;
  inicial: DatosProducto;
  alTerminar: (guardado: Producto | null) => void;
}) {
  const [datos, setDatos] = useState<DatosProducto>(inicial);
  const [error, setError] = useState<string | null>(null);
  const cambiar = (parcial: Partial<DatosProducto>) => setDatos((d) => ({ ...d, ...parcial }));
  const posibles = PRESENTACIONES_POR_UNIDAD[datos.unidadBase];

  function alternar(codigoPresentacion: string) {
    cambiar({
      presentaciones: datos.presentaciones.includes(codigoPresentacion)
        ? datos.presentaciones.filter((c) => c !== codigoPresentacion)
        : [...datos.presentaciones, codigoPresentacion],
    });
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    try {
      alTerminar(await contenedor.administrarCatalogo.guardarProducto(codigo, datos));
    } catch (e) {
      setError(mensaje(e));
    }
  }

  return (
    <form
      className="formulario formulario--recuadro"
      onSubmit={(e) => void enviar(e)}
      aria-label={codigo ? "Editar producto" : "Nuevo producto"}
    >
      <div className="formulario__fila">
        <label className="campo">
          <span>Nombre</span>
          <input required value={datos.nombre} onChange={(e) => cambiar({ nombre: e.target.value })} />
        </label>
        <label className="campo">
          <span>Categoría</span>
          <select value={datos.categoria} onChange={(e) => cambiar({ categoria: e.target.value })}>
            {CATEGORIAS.map((c) => (
              <option key={c.codigo} value={c.codigo}>
                {c.nombre}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="formulario__fila">
        <label className="campo">
          <span>Se mide en</span>
          <select
            value={datos.unidadBase}
            onChange={(e) => {
              const unidad = e.target.value as UnidadBase;
              // Al cambiar la unidad, las presentaciones viejas ya no aplican.
              cambiar({ unidadBase: unidad, presentaciones: PRESENTACIONES_POR_UNIDAD[unidad].map((p) => p.codigo) });
            }}
          >
            {(Object.keys(NOMBRE_UNIDAD_BASE) as UnidadBase[]).map((u) => (
              <option key={u} value={u}>
                {NOMBRE_UNIDAD_BASE[u]}
              </option>
            ))}
          </select>
        </label>
        <label className="campo">
          <span>Días que se conserva</span>
          <input
            type="number"
            min={1}
            max={3650}
            value={datos.diasConservacion}
            onChange={(e) => cambiar({ diasConservacion: Number(e.target.value) })}
          />
        </label>
      </div>
      <fieldset className="campo campo--grupo">
        <legend>Se vende por</legend>
        {posibles.map((p) => (
          <label key={p.codigo} className="casilla">
            <input
              type="checkbox"
              checked={datos.presentaciones.includes(p.codigo)}
              onChange={() => alternar(p.codigo)}
            />
            {p.nombre}
            {p.factor !== 1 && (
              <span className="tenue">
                {" "}
                ({p.factor} {NOMBRE_UNIDAD_BASE[datos.unidadBase].toLowerCase()})
              </span>
            )}
          </label>
        ))}
      </fieldset>

      {error && (
        <p className="estado estado--error" role="alert">
          {error}
        </p>
      )}
      <div className="formulario__botones">
        <button type="submit" className="boton">
          {codigo ? "Guardar cambios" : "Crear producto"}
        </button>
        <button type="button" className="boton boton--suave" onClick={() => alTerminar(null)}>
          Cancelar
        </button>
      </div>
    </form>
  );
}
