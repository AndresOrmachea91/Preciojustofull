import { useCallback, useEffect, useState, type FormEvent } from "react";

import {
  NOMBRE_ROL,
  ROLES,
  puede,
  type EstadoReporte,
  type Mercado,
  type ReporteEnRevision,
  type Rol,
  type Usuario,
} from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { MensajeAviso, MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { Pestanas } from "@/ui/componentes/Pestanas";
import { CatalogoProductos } from "@/ui/paginas/administracion/CatalogoProductos";
import { CatalogoPuntosVenta } from "@/ui/paginas/administracion/CatalogoPuntosVenta";

type Pestana = "usuarios" | "reportes" | "puntos" | "productos";

export function PaginaAdmin({ contenedor, usuario }: { contenedor: Contenedor; usuario: Usuario }) {
  const verUsuarios = puede(usuario, "gestionar_usuarios");
  const verReportes = puede(usuario, "validar_reportes");
  const verCatalogo = puede(usuario, "gestionar_catalogo");
  const [pestana, setPestana] = useState<Pestana>(verUsuarios ? "usuarios" : verReportes ? "reportes" : "puntos");

  const pestanas: { id: Pestana; texto: string; visible: boolean }[] = [
    { id: "usuarios", texto: "Usuarios", visible: verUsuarios },
    { id: "puntos", texto: "Mercados y tiendas", visible: verCatalogo },
    { id: "productos", texto: "Productos", visible: verCatalogo },
    { id: "reportes", texto: "Reportes por revisar", visible: verReportes },
  ];

  return (
    <section aria-labelledby="titulo-admin">
      <h2 id="titulo-admin" className="seccion">
        Administración
      </h2>
      <Pestanas pestanas={pestanas} activa={pestana} onCambiar={setPestana} />
      {pestana === "usuarios" && verUsuarios && <Usuarios contenedor={contenedor} yo={usuario} />}
      {pestana === "puntos" && verCatalogo && <CatalogoPuntosVenta contenedor={contenedor} />}
      {pestana === "productos" && verCatalogo && <CatalogoProductos contenedor={contenedor} />}
      {pestana === "reportes" && verReportes && <Reportes contenedor={contenedor} />}
    </section>
  );
}

// --- usuarios ----------------------------------------------------------------

function Usuarios({ contenedor, yo }: { contenedor: Contenedor; yo: Usuario }) {
  const [lista, setLista] = useState<Usuario[] | null>(null);
  const [puntos, setPuntos] = useState<Mercado[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  // Los puestos y tiendas que se le pueden asignar a un vendedor.
  useEffect(() => {
    void contenedor.catalogo.mercados().then(setPuntos, () => setPuntos([]));
  }, [contenedor]);

  const cargar = useCallback(() => {
    contenedor.administrar.usuarios().then(setLista, (e) => setError(textoDeError(e)));
  }, [contenedor]);

  useEffect(cargar, [cargar]);

  async function aplicar(accion: Promise<Usuario>, texto: string) {
    setError(null);
    setAviso(null);
    try {
      const actualizado = await accion;
      setLista((l) => l?.map((u) => (u.id === actualizado.id ? actualizado : u)) ?? null);
      setAviso(texto);
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  function restablecer(u: Usuario) {
    const nueva = globalThis.prompt?.(`Nueva contraseña para ${u.correo} (mínimo 8 caracteres):`);
    if (nueva) void aplicar(contenedor.administrar.restablecerContrasena(u.id, nueva), "Contraseña restablecida.");
  }

  return (
    <>
      <NuevoUsuario
        contenedor={contenedor}
        alCrear={(u) => {
          setLista((l) => [...(l ?? []), u]);
          setAviso(`Cuenta creada: ${u.correo}`);
        }}
      />

      <MensajeError texto={error} />
      {!error && <MensajeAviso texto={aviso} />}

      {!lista && !error && <p className="estado">Cargando cuentas…</p>}
      {lista && (
        <div className="tabla-envoltura">
          <table className="tabla">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Correo</th>
                <th>Rol</th>
                <th>Puesto</th>
                <th>Estado</th>
                <th aria-label="Acciones" />
              </tr>
            </thead>
            <tbody>
              {lista.map((u) => (
                <tr key={u.id} className={u.activo ? undefined : "tabla__fila--inactiva"}>
                  <td>
                    {u.nombre}
                    {u.id === yo.id && <span className="tenue"> (usted)</span>}
                  </td>
                  <td>{u.correo}</td>
                  <td>
                    <select
                      aria-label={`Rol de ${u.correo}`}
                      value={u.rol}
                      onChange={(e) =>
                        void aplicar(
                          contenedor.administrar.cambiarRol(u.id, e.target.value as Rol),
                          `${u.correo} ahora es ${NOMBRE_ROL[e.target.value as Rol].toLowerCase()}.`,
                        )
                      }
                    >
                      {ROLES.map((r) => (
                        <option key={r} value={r}>
                          {NOMBRE_ROL[r]}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    {u.rol === "vendedor" ? (
                      <select
                        aria-label={`Puesto de ${u.correo}`}
                        value={u.codigoPuntoVenta ?? ""}
                        onChange={(e) =>
                          void aplicar(
                            contenedor.administrar.asignarPuntoVenta(u.id, e.target.value || null),
                            e.target.value
                              ? `${u.correo} vende en ${puntos.find((p) => p.codigo === e.target.value)?.nombre ?? e.target.value}.`
                              : `${u.correo} ya no tiene puesto asignado.`,
                          )
                        }
                      >
                        <option value="">Sin asignar</option>
                        {puntos.map((p) => (
                          <option key={p.codigo} value={p.codigo}>
                            {p.nombre}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span className="tenue">—</span>
                    )}
                  </td>
                  <td>{u.activo ? "Activa" : "Desactivada"}</td>
                  <td className="tabla__acciones">
                    <button
                      type="button"
                      className="boton boton--suave"
                      onClick={() =>
                        void aplicar(
                          contenedor.administrar.cambiarActivo(u.id, !u.activo),
                          `${u.correo} ${u.activo ? "desactivada" : "reactivada"}.`,
                        )
                      }
                    >
                      {u.activo ? "Desactivar" : "Activar"}
                    </button>
                    <button type="button" className="boton boton--suave" onClick={() => restablecer(u)}>
                      Contraseña
                    </button>
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

function NuevoUsuario({ contenedor, alCrear }: { contenedor: Contenedor; alCrear: (u: Usuario) => void }) {
  const [abierto, setAbierto] = useState(false);
  const [correo, setCorreo] = useState("");
  const [nombre, setNombre] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [rol, setRol] = useState<Rol>("vendedor");
  const [error, setError] = useState<string | null>(null);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    try {
      alCrear(await contenedor.administrar.crearUsuario({ correo, nombre, contrasena, rol }));
      setCorreo("");
      setNombre("");
      setContrasena("");
      setAbierto(false);
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  if (!abierto) {
    return (
      <button type="button" className="boton" onClick={() => setAbierto(true)}>
        Nueva cuenta
      </button>
    );
  }

  return (
    <form className="formulario formulario--recuadro" onSubmit={(e) => void enviar(e)} aria-label="Nueva cuenta">
      <div className="formulario__fila">
        <label className="campo">
          <span>Nombre</span>
          <input value={nombre} onChange={(e) => setNombre(e.target.value)} />
        </label>
        <label className="campo">
          <span>Correo</span>
          <input type="email" required value={correo} onChange={(e) => setCorreo(e.target.value)} />
        </label>
      </div>
      <div className="formulario__fila">
        <label className="campo">
          <span>Contraseña inicial</span>
          <input
            type="password"
            required
            minLength={8}
            value={contrasena}
            onChange={(e) => setContrasena(e.target.value)}
            autoComplete="new-password"
          />
        </label>
        <label className="campo">
          <span>Rol</span>
          <select value={rol} onChange={(e) => setRol(e.target.value as Rol)}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {NOMBRE_ROL[r]}
              </option>
            ))}
          </select>
        </label>
      </div>
      <MensajeError texto={error} />
      <div className="formulario__botones">
        <button type="submit" className="boton">
          Crear cuenta
        </button>
        <button type="button" className="boton boton--suave" onClick={() => setAbierto(false)}>
          Cancelar
        </button>
      </div>
    </form>
  );
}

// --- reportes ----------------------------------------------------------------

const FILTROS: { valor: EstadoReporte | "todos"; texto: string }[] = [
  { valor: "pendiente", texto: "Pendientes" },
  { valor: "aprobado", texto: "Aprobados" },
  { valor: "rechazado", texto: "Rechazados" },
  { valor: "todos", texto: "Todos" },
];

function Reportes({ contenedor }: { contenedor: Contenedor }) {
  const [filtro, setFiltro] = useState<EstadoReporte | "todos">("pendiente");
  const [lista, setLista] = useState<ReporteEnRevision[] | null>(null);
  const [nombres, setNombres] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Nombres legibles en vez de códigos; si el catálogo falla, quedan los códigos.
    void Promise.all([contenedor.catalogo.productos(), contenedor.catalogo.mercados()])
      .then(([productos, mercados]) =>
        setNombres(Object.fromEntries([...productos, ...mercados].map((x) => [x.codigo, x.nombre]))),
      )
      .catch(() => undefined);
  }, [contenedor]);

  useEffect(() => {
    setLista(null);
    setError(null);
    contenedor.administrar.reportes(filtro).then(setLista, (e) => setError(textoDeError(e)));
  }, [contenedor, filtro]);

  async function revisar(accion: Promise<ReporteEnRevision>) {
    setError(null);
    try {
      const revisado = await accion;
      setLista(
        (l) =>
          l
            ?.map((r) => (r.id === revisado.id ? revisado : r))
            .filter((r) => filtro === "todos" || r.estado === filtro) ?? null,
      );
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  function rechazar(r: ReporteEnRevision) {
    const motivo = globalThis.prompt?.("Motivo del rechazo:");
    if (motivo !== null && motivo !== undefined) void revisar(contenedor.administrar.rechazar(r.id, motivo));
  }

  return (
    <>
      <p className="tenue">
        Un reporte no se publica directo: recién aprobado entra al motor de fusión como una observación más,
        con la reputación del rol de quien lo envió.
      </p>
      <div className="segmentado segmentado--margen" role="group" aria-label="Filtrar reportes">
        {FILTROS.map((f) => (
          <button
            key={f.valor}
            type="button"
            aria-pressed={filtro === f.valor}
            className="segmentado__opcion"
            onClick={() => setFiltro(f.valor)}
          >
            {f.texto}
          </button>
        ))}
      </div>

      <MensajeError texto={error} />
      {!lista && !error && <p className="estado">Cargando reportes…</p>}
      {lista && lista.length === 0 && <p className="estado">No hay reportes en esta lista.</p>}

      <div className="lista">
        {lista?.map((r) => (
          <article key={r.id} className="tarjeta">
            <div className="tarjeta__cabecera">
              <div>
                <h3 className="tarjeta__nombre">{nombres[r.codigoProducto] ?? r.codigoProducto}</h3>
                <p className="tarjeta__zona">
                  {nombres[r.codigoMercado] ?? r.codigoMercado} · {new Date(r.creadoEn).toLocaleString("es-BO")}
                </p>
              </div>
              <span className={`estado-reporte estado-reporte--${r.estado}`}>{r.estado}</span>
            </div>
            <p className="tarjeta__precio">
              Bs {r.monto.toFixed(2)} <span className="tarjeta__unidad">por {r.unidad.toLowerCase()}</span>
            </p>
            {r.motivoRechazo && <p className="tarjeta__nota">Motivo: {r.motivoRechazo}</p>}
            {r.estado === "pendiente" && (
              <div className="formulario__botones">
                <button type="button" className="boton" onClick={() => void revisar(contenedor.administrar.aprobar(r.id))}>
                  Aprobar
                </button>
                <button type="button" className="boton boton--suave" onClick={() => rechazar(r)}>
                  Rechazar
                </button>
              </div>
            )}
          </article>
        ))}
      </div>
    </>
  );
}
