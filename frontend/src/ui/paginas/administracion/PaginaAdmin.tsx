import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { bs,
  NOMBRE_ROL,
  ROLES,
  puede,
  sinTildes,
  type Auditoria,
  type EstadoReporte,
  type Mercado,
  type ReporteEnRevision,
  type Rol,
  type Usuario,
} from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { MensajeAviso, MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { Pestanas } from "@/ui/componentes/Pestanas";
import { fechaCorta } from "@/ui/formato";
import { Auditoria as VistaAuditoria } from "@/ui/paginas/administracion/Auditoria";
import { CatalogoProductos } from "@/ui/paginas/administracion/CatalogoProductos";
import { CatalogoPuntosVenta } from "@/ui/paginas/administracion/CatalogoPuntosVenta";
import { OfertasEnRevision } from "@/ui/paginas/administracion/OfertasEnRevision";
import { PlanillaCampo } from "@/ui/paginas/administracion/PlanillaCampo";
import { RegistrarCasera } from "@/ui/paginas/administracion/RegistrarCasera";
import { Referencias } from "@/ui/paginas/administracion/Referencias";
import { SaludSistema } from "@/ui/paginas/administracion/SaludSistema";

type Pestana =
  | "usuarios" | "caseras" | "reportes" | "ofertas" | "puntos" | "productos" | "campo" | "salud" | "auditoria"
  | "referencias";

export function PaginaAdmin({ contenedor, usuario }: { contenedor: Contenedor; usuario: Usuario }) {
  const verUsuarios = puede(usuario, "gestionar_usuarios");
  const verReportes = puede(usuario, "validar_reportes");
  const verCatalogo = puede(usuario, "gestionar_catalogo");
  const verAuditoria = puede(usuario, "ver_auditoria");
  const verCampo = puede(usuario, "importar_campo");
  const verSalud = puede(usuario, "ver_salud");
  const [pestana, setPestana] = useState<Pestana>(verUsuarios ? "usuarios" : verReportes ? "reportes" : "puntos");

  // Lo que espera una decisión del administrador: se ve en la pestaña sin tener que entrar a buscarlo.
  const [porRevisar, setPorRevisar] = useState({ reportes: 0, ofertas: 0 });
  useEffect(() => {
    if (!verReportes) return;
    let vigente = true;
    void Promise.all([
      contenedor.administrar.reportes("pendiente").then((l) => l.length, () => 0),
      contenedor.revisarOfertas.pendientes().then((l) => l.length, () => 0),
    ]).then(([reportes, ofertas]) => vigente && setPorRevisar({ reportes, ofertas }));
    return () => {
      vigente = false;
    };
    // Se vuelve a contar al cambiar de pestaña: ahí es donde se aprueba o se retira.
  }, [contenedor, verReportes, pestana]);

  const pestanas: { id: Pestana; texto: string; visible: boolean; pendientes?: number }[] = [
    { id: "usuarios", texto: "Usuarios", visible: verUsuarios },
    { id: "caseras", texto: "Registrar casera", visible: verUsuarios },
    { id: "puntos", texto: "Mercados y distribuidores", visible: verCatalogo },
    { id: "productos", texto: "Productos", visible: verCatalogo },
    { id: "reportes", texto: "Reportes por revisar", visible: verReportes, pendientes: porRevisar.reportes },
    { id: "ofertas", texto: "Ofertas", visible: verReportes, pendientes: porRevisar.ofertas },
    { id: "campo", texto: "Planilla de campo", visible: verCampo },
    { id: "salud", texto: "Salud del sistema", visible: verSalud },
    { id: "auditoria", texto: "Auditoría", visible: verAuditoria },
    { id: "referencias", texto: "Roles y fuentes", visible: verAuditoria },
  ];

  return (
    <section aria-labelledby="titulo-admin">
      <h2 id="titulo-admin" className="seccion">
        Administración
      </h2>
      <Pestanas pestanas={pestanas} activa={pestana} onCambiar={setPestana} />
      {pestana === "usuarios" && verUsuarios && <Usuarios contenedor={contenedor} yo={usuario} />}
      {pestana === "caseras" && verUsuarios && <RegistrarCasera contenedor={contenedor} />}
      {pestana === "puntos" && verCatalogo && <CatalogoPuntosVenta contenedor={contenedor} />}
      {pestana === "productos" && verCatalogo && <CatalogoProductos contenedor={contenedor} />}
      {pestana === "reportes" && verReportes && <Reportes contenedor={contenedor} />}
      {pestana === "ofertas" && verReportes && <OfertasEnRevision contenedor={contenedor} />}
      {pestana === "campo" && verCampo && <PlanillaCampo contenedor={contenedor} />}
      {pestana === "salud" && verSalud && <SaludSistema contenedor={contenedor} />}
      {pestana === "auditoria" && verAuditoria && <VistaAuditoria contenedor={contenedor} />}
      {pestana === "referencias" && verAuditoria && <Referencias contenedor={contenedor} />}
    </section>
  );
}

// --- usuarios ----------------------------------------------------------------

function Usuarios({ contenedor, yo }: { contenedor: Contenedor; yo: Usuario }) {
  const [lista, setLista] = useState<Usuario[] | null>(null);
  const [conEliminadas, setConEliminadas] = useState(false);
  const [aEliminar, setAEliminar] = useState<number | null>(null);
  const [puntos, setPuntos] = useState<Mercado[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [texto, setTexto] = useState("");
  const [rol, setRol] = useState<Rol | "todos">("todos");

  // Los puestos y tiendas que se le pueden asignar a un vendedor.
  useEffect(() => {
    void contenedor.catalogo.mercados().then(setPuntos, () => setPuntos([]));
  }, [contenedor]);

  const cargar = useCallback(() => {
    contenedor.administrar.usuarios(conEliminadas).then(setLista, (e) => setError(textoDeError(e)));
  }, [contenedor, conEliminadas]);

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

  async function eliminar(u: Usuario) {
    setError(null);
    setAviso(null);
    setAEliminar(null);
    try {
      await contenedor.administrar.eliminarUsuario(u.id, yo);
      setAviso(`${u.correo} eliminada. Su fila y su auditoría quedan guardadas.`);
      cargar();
    } catch (e) {
      setError(textoDeError(e));
    }
  }

  function restablecer(u: Usuario) {
    const nueva = globalThis.prompt?.(`Nueva contraseña para ${u.correo} (mínimo 8 caracteres):`);
    if (nueva) void aplicar(contenedor.administrar.restablecerContrasena(u.id, nueva), "Contraseña restablecida.");
  }

  const visibles = useMemo(() => {
    const buscado = sinTildes(texto.trim());
    return (lista ?? []).filter(
      (u) => (rol === "todos" || u.rol === rol) && (!buscado || sinTildes(`${u.nombre} ${u.correo}`).includes(buscado)),
    );
  }, [lista, texto, rol]);

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

      <label className="casilla casilla--barra">
        <input type="checkbox" checked={conEliminadas} onChange={(e) => setConEliminadas(e.target.checked)} />
        Mostrar también las cuentas eliminadas
      </label>

      <div className="barra-filtros">
        <input
          className="barra__buscar"
          type="search"
          placeholder="Buscar por nombre o correo"
          aria-label="Buscar cuentas"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
        />
        <div className="segmentado" role="group" aria-label="Filtrar por rol">
          {(["todos", ...ROLES] as const).map((r) => (
            <button key={r} type="button" className="segmentado__opcion" aria-pressed={rol === r} onClick={() => setRol(r)}>
              {r === "todos" ? "Todos" : NOMBRE_ROL[r]}
            </button>
          ))}
        </div>
        {lista && (
          <span className="tenue">
            {visibles.length} de {lista.length} cuentas
          </span>
        )}
      </div>

      {!lista && !error && <p className="estado">Cargando cuentas…</p>}
      {lista && visibles.length === 0 && <p className="estado">Ninguna cuenta coincide con la búsqueda.</p>}
      {lista && visibles.length > 0 && (
        <div className="tabla-envoltura">
          <table className="tabla">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Correo</th>
                <th>Rol</th>
                <th>Puesto</th>
                <th>Estado</th>
                <th>Auditoría</th>
                <th aria-label="Acciones" />
              </tr>
            </thead>
            <tbody>
              {visibles.map((u) =>
                u.auditoria?.eliminado ? (
                  <FilaEliminada key={u.id} usuario={u} />
                ) : (
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
                    <td>{u.auditoria && <CeldaAuditoria auditoria={u.auditoria} />}</td>
                    <td className="tabla__acciones">
                      {aEliminar === u.id ? (
                        <>
                          <span className="tenue">¿Eliminar la cuenta?</span>
                          <button type="button" className="boton boton--peligro" onClick={() => void eliminar(u)}>
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
                          {u.id !== yo.id && (
                            <button type="button" className="boton boton--suave" onClick={() => setAEliminar(u.id)}>
                              Eliminar
                            </button>
                          )}
                        </>
                      )}
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

/** Quién creó la fila y quién la cambió por última vez, con su fecha. */
function CeldaAuditoria({ auditoria: a }: { auditoria: Auditoria }) {
  // En la tabla va solo la fecha; quién lo hizo y la hora salen al pasar el cursor
  // (y completos en la pestaña Auditoría). Así cada cuenta ocupa un solo renglón.
  const dia = (iso: string) => new Date(iso).toLocaleDateString("es-BO", { day: "2-digit", month: "2-digit", year: "2-digit" });
  const detalle =
    `Creada por ${a.creadoPor} · ${fechaCorta(a.creadoEn)}` +
    (a.modificadoEn ? `
${a.eliminado ? "Eliminada" : "Modificada"} por ${a.modificadoPor} · ${fechaCorta(a.modificadoEn)}` : "");
  return (
    <span className="auditoria-celda" title={detalle}>
      <span>Creada {dia(a.creadoEn)}</span>
      {a.modificadoEn && (
        <span className="tenue">
          {/* Quién eliminó una cuenta se ve siempre: es lo que se busca en esa fila. */}
          {a.eliminado ? `Eliminada por ${a.modificadoPor} · ${dia(a.modificadoEn)}` : `Cambió ${dia(a.modificadoEn)}`}
        </span>
      )}
    </span>
  );
}

/** Una cuenta eliminada se muestra, sin acciones: el eliminado es lógico. */
function FilaEliminada({ usuario: u }: { usuario: Usuario }) {
  return (
    <tr className="tabla__fila--inactiva tabla__fila--eliminada">
      <td>{u.nombre}</td>
      <td>{u.correo}</td>
      <td>{NOMBRE_ROL[u.rol]}</td>
      <td>
        <span className="tenue">—</span>
      </td>
      <td>
        <span className="accion accion--eliminado">Eliminada</span>
      </td>
      <td>{u.auditoria && <CeldaAuditoria auditoria={u.auditoria} />}</td>
      <td />
    </tr>
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
              Bs {bs(r.monto)} <span className="tarjeta__unidad">por {r.unidad.toLowerCase()}</span>
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
