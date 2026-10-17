/**
 * Cuentas en memoria: el plan B de la demo y el adaptador de las pruebas.
 *
 * Reproduce lo mínimo de las reglas del backend (credenciales, permisos,
 * último administrador) para que la interfaz se comporte igual sin red.
 * No es seguridad: en memoria todo vive en el navegador.
 */
import type {
  AdministracionRepositorio,
  AlmacenSesion,
  AuditoriaRepositorio,
  MisReportesRepositorio,
  NuevaCuenta,
  RecuperacionRepositorio,
  ReporteRepositorio,
  SesionRepositorio,
} from "@/aplicacion/puertos";
import { NOMBRE_ROL } from "@/dominio/modelo";
import type {
  Auditoria,
  EstadoReporte,
  Permiso,
  Referencias,
  RegistroAuditado,
  ReporteEnRevision,
  Rol,
  Usuario,
} from "@/dominio/modelo";

const PERMISOS: Record<Rol, Permiso[]> = {
  usuario: ["gestionar_listas", "reportar_precio"],
  vendedor: ["gestionar_listas", "publicar_precio_propio", "reportar_precio"],
  administrador: [
    "gestionar_catalogo",
    "gestionar_listas",
    "gestionar_usuarios",
    "publicar_precio_propio",
    "reportar_precio",
    "validar_reportes",
    "ver_auditoria",
  ],
};

/** Cuenta de demostración del modo memoria. */
export const ADMIN_DEMO = { correo: "admin@preciojusto.bo", contrasena: "admin1234" };

interface Cuenta {
  usuario: Usuario;
  contrasena: string;
}

function crear(
  id: number,
  correo: string,
  nombre: string,
  rol: Rol,
  activo = true,
  codigoPuntoVenta: string | null = null,
): Usuario {
  return {
    id,
    correo,
    nombre,
    rol,
    activo,
    creadoEn: "2026-10-01T12:00:00Z",
    permisos: activo ? PERMISOS[rol] : [],
    codigoPuntoVenta,
    auditoria: { creadoEn: "2026-10-01T12:00:00Z", creadoPor: "sistema", modificadoEn: null, modificadoPor: null, eliminado: false },
  };
}

/** Las fuentes de precios, tal como las describe el backend. */
const FUENTES: Referencias["fuentes"] = [
  { codigo: "siip_ipc", nombre: "SIIP - precios al consumidor (IPC)", descripcion: "Precio promedio mensual al consumidor final por ciudad.", confianzaBase: "alto", derivaDe: null, automatica: true, url: "https://siip.produccion.gob.bo" },
  { codigo: "siip_diario", nombre: "SIIP - precios diarios mayoristas", descripcion: "Precio mayorista diario por ciudad.", confianzaBase: "alto", derivaDe: null, automatica: true, url: "https://siip.produccion.gob.bo" },
  { codigo: "vendedor", nombre: "Declarado por el vendedor", descripcion: "Precio que el vendedor publica sobre su propio puesto.", confianzaBase: "medio", derivaDe: null, automatica: false, url: null },
  { codigo: "ciudadano", nombre: "Reporte ciudadano", descripcion: "Entra al motor cuando el administrador lo aprueba.", confianzaBase: "bajo", derivaDe: null, automatica: false, url: null },
];

/** El id de la cuenta de la sesión en memoria (el token es "memoria:<id>"), o null. */
export function idDeSesion(almacen: AlmacenSesion): number | null {
  const id = Number(almacen.leer()?.replace("memoria:", ""));
  return Number.isInteger(id) && id > 0 ? id : null;
}

export class CuentasMemoria
  implements
    SesionRepositorio,
    AdministracionRepositorio,
    AuditoriaRepositorio,
    RecuperacionRepositorio,
    ReporteRepositorio,
    MisReportesRepositorio
{
  /** En memoria no hay correo: los enlaces "enviados" quedan acá (las pruebas los leen). */
  readonly enlacesEnviados: { correo: string; token: string }[] = [];

  private readonly cuentas = new Map<number, Cuenta>();
  private readonly listaReportes = new Map<number, ReporteEnRevision>();
  private siguiente = 1;

  constructor(private readonly almacen: AlmacenSesion) {
    this.agregar(crear(0, ADMIN_DEMO.correo, "Administración", "administrador"), ADMIN_DEMO.contrasena);
    this.agregar(crear(0, "vendedora@preciojusto.bo", "Rosa Mamani", "vendedor", true, "rodriguez"), "puesto1234");
    this.agregar(crear(0, "vecino@correo.bo", "Juan Quispe", "usuario"), "vecino1234");
    for (const [i, [producto, mercado, monto]] of (
      [
        ["tomate", "rodriguez", 9.5],
        ["papa", "lanza", 48],
      ] as const
    ).entries()) {
      this.listaReportes.set(i + 1, {
        id: i + 1,
        codigoProducto: producto,
        codigoMercado: mercado,
        monto,
        unidad: i === 0 ? "KILO" : "ARROBA",
        idAutor: 3,
        creadoEn: `2026-10-0${i + 2}T14:30:00Z`,
        estado: "pendiente",
        motivoRechazo: null,
      });
    }
  }

  private agregar(usuario: Usuario, contrasena: string): Usuario {
    const conId = { ...usuario, id: this.siguiente++ };
    this.cuentas.set(conId.id, { usuario: conId, contrasena });
    return conId;
  }

  private vigentes(): Cuenta[] {
    return [...this.cuentas.values()].filter((c) => !c.usuario.auditoria?.eliminado);
  }

  /** La auditoría después de un cambio: quién (la sesión) y cuándo. */
  private cambiada(antes: Usuario, eliminado = false): Auditoria {
    const base = antes.auditoria ?? { creadoEn: antes.creadoEn, creadoPor: "sistema", modificadoEn: null, modificadoPor: null, eliminado: false };
    return { ...base, modificadoEn: new Date().toISOString(), modificadoPor: this.actual().correo, eliminado };
  }

  private actual(): Usuario {
    const usuario = this.cuentas.get(idDeSesion(this.almacen) ?? 0)?.usuario;
    if (!usuario?.activo || usuario.auditoria?.eliminado) throw new Error("Sesión inválida o vencida. Vuelva a ingresar.");
    return usuario;
  }

  private exigir(permiso: Permiso): void {
    if (!this.actual().permisos.includes(permiso)) throw new Error(`No tiene permiso para ${permiso}`);
  }

  async ingresar(correo: string, contrasena: string): Promise<{ token: string; usuario: Usuario }> {
    const cuenta = this.vigentes().find((c) => c.usuario.correo === correo.trim().toLowerCase());
    if (!cuenta || cuenta.contrasena !== contrasena || !cuenta.usuario.activo) {
      throw new Error("Correo o contraseña incorrectos");
    }
    return { token: `memoria:${cuenta.usuario.id}`, usuario: cuenta.usuario };
  }

  async pedirEnlace(correo: string): Promise<void> {
    const cuenta = this.vigentes().find((c) => c.usuario.correo === correo.trim().toLowerCase());
    if (cuenta?.usuario.activo) {
      this.enlacesEnviados.push({ correo: cuenta.usuario.correo, token: `enlace:${cuenta.usuario.id}:${cuenta.contrasena}` });
    }
  }

  async restablecerConEnlace(token: string, contrasena: string): Promise<void> {
    // Como en el backend: el enlace lleva la contraseña vieja y deja de servir al cambiarla.
    const [, id, vieja] = token.split(":");
    const cuenta = this.cuentas.get(Number(id));
    if (!cuenta || cuenta.contrasena !== vieja || cuenta.usuario.auditoria?.eliminado) {
      throw new Error("El enlace no es válido o ya venció. Pida uno nuevo.");
    }
    cuenta.contrasena = contrasena;
  }

  async registrarse(cuenta: NuevaCuenta): Promise<Usuario> {
    return this.alta(cuenta, "usuario");
  }

  private alta(cuenta: NuevaCuenta, rol: Rol): Usuario {
    const correo = cuenta.correo.trim().toLowerCase();
    if (this.vigentes().some((c) => c.usuario.correo === correo)) {
      throw new Error(`Ya existe una cuenta con el correo ${correo}`);
    }
    if (cuenta.contrasena.length < 8) throw new Error("La contraseña debe tener al menos 8 caracteres");
    return this.agregar(crear(0, correo, cuenta.nombre || correo.split("@")[0], rol), cuenta.contrasena);
  }

  async yo(): Promise<Usuario> {
    return this.actual();
  }

  async usuarios(incluirEliminados = false): Promise<Usuario[]> {
    this.exigir("gestionar_usuarios");
    return (incluirEliminados ? [...this.cuentas.values()] : this.vigentes()).map((c) => c.usuario);
  }

  async eliminarUsuario(id: number): Promise<void> {
    this.exigir("gestionar_usuarios");
    const cuenta = this.vigentes().find((c) => c.usuario.id === id);
    if (!cuenta) throw new Error(`No existe el usuario ${id}`);
    if (id === this.actual().id) throw new Error("No puede eliminar su propia cuenta");
    const u = cuenta.usuario;
    const admins = this.vigentes().filter((c) => c.usuario.activo && c.usuario.rol === "administrador").length;
    if (u.activo && u.rol === "administrador" && admins <= 1) throw new Error("Debe quedar al menos un administrador activo");
    cuenta.usuario = { ...u, auditoria: this.cambiada(u, true) };
  }

  async tablasAuditadas(): Promise<string[]> {
    this.exigir("ver_auditoria");
    return ["usuario"];
  }

  async auditoria(tabla?: string, limite = 50): Promise<RegistroAuditado[]> {
    this.exigir("ver_auditoria");
    if (tabla && tabla !== "usuario") return [];
    return [...this.cuentas.values()]
      .map(({ usuario: u }): RegistroAuditado => {
        const a = u.auditoria!;
        return {
          tabla: "usuario",
          clave: u.correo,
          descripcion: `${u.nombre} (${u.rol})`,
          accion: a.eliminado ? "eliminado" : a.modificadoEn ? "modificado" : "creado",
          ultimoCambio: a.modificadoEn ?? a.creadoEn,
          auditoria: a,
        };
      })
      .sort((x, y) => y.ultimoCambio.localeCompare(x.ultimoCambio))
      .slice(0, limite);
  }

  async referencias(): Promise<Referencias> {
    this.exigir("ver_auditoria");
    return {
      roles: (Object.keys(PERMISOS) as Rol[]).map((rol) => ({
        codigo: rol,
        nombre: NOMBRE_ROL[rol],
        descripcion: "",
        permisos: PERMISOS[rol].map((codigo) => ({ codigo, descripcion: codigo.replaceAll("_", " ") })),
      })),
      fuentes: FUENTES,
    };
  }

  async crearUsuario(cuenta: NuevaCuenta & { rol: Rol }): Promise<Usuario> {
    this.exigir("gestionar_usuarios");
    return this.alta(cuenta, cuenta.rol);
  }

  async actualizarUsuario(
    id: number,
    cambios: { rol?: Rol; activo?: boolean; codigoPuntoVenta?: string | null },
  ): Promise<Usuario> {
    this.exigir("gestionar_usuarios");
    const cuenta = this.cuentas.get(id);
    if (!cuenta) throw new Error(`No existe el usuario ${id}`);
    const antes = cuenta.usuario;
    const despues = crear(
      id,
      antes.correo,
      antes.nombre,
      cambios.rol ?? antes.rol,
      cambios.activo ?? antes.activo,
      cambios.codigoPuntoVenta === undefined ? antes.codigoPuntoVenta : cambios.codigoPuntoVenta,
    );
    const conAuditoria = { ...despues, auditoria: this.cambiada(antes) };
    const esAdmin = (u: Usuario) => u.activo && u.rol === "administrador";
    const admins = [...this.cuentas.values()].filter((c) => esAdmin(c.usuario)).length;
    if (esAdmin(antes) && !esAdmin(despues) && admins <= 1) {
      throw new Error("Debe quedar al menos un administrador activo");
    }
    cuenta.usuario = conAuditoria;
    return conAuditoria;
  }

  async restablecerContrasena(id: number, contrasena: string): Promise<Usuario> {
    this.exigir("gestionar_usuarios");
    const cuenta = this.cuentas.get(id);
    if (!cuenta) throw new Error(`No existe el usuario ${id}`);
    cuenta.contrasena = contrasena;
    return cuenta.usuario;
  }

  async reportar(entrada: { codigoProducto: string; codigoMercado: string; monto: number; unidad: string }): Promise<void> {
    this.exigir("reportar_precio");
    const id = Math.max(0, ...this.listaReportes.keys()) + 1;
    this.listaReportes.set(id, {
      id,
      codigoProducto: entrada.codigoProducto,
      codigoMercado: entrada.codigoMercado,
      monto: entrada.monto,
      unidad: entrada.unidad,
      idAutor: this.actual().id,
      creadoEn: new Date().toISOString(),
      estado: "pendiente",
      motivoRechazo: null,
    });
  }

  async misReportes(): Promise<ReporteEnRevision[]> {
    const yo = this.actual().id;
    return [...this.listaReportes.values()].filter((r) => r.idAutor === yo).sort((a, b) => b.id - a.id);
  }

  async reportes(estado: EstadoReporte | "todos"): Promise<ReporteEnRevision[]> {
    this.exigir("validar_reportes");
    return [...this.listaReportes.values()].filter((r) => estado === "todos" || r.estado === estado);
  }

  async aprobarReporte(id: number): Promise<ReporteEnRevision> {
    return this.revisar(id, "aprobado", null);
  }

  async rechazarReporte(id: number, motivo: string): Promise<ReporteEnRevision> {
    return this.revisar(id, "rechazado", motivo);
  }

  private revisar(id: number, estado: EstadoReporte, motivo: string | null): ReporteEnRevision {
    this.exigir("validar_reportes");
    const reporte = this.listaReportes.get(id);
    if (!reporte) throw new Error(`No existe el reporte ${id}`);
    if (reporte.estado !== "pendiente") throw new Error(`El reporte ${id} ya fue revisado (${reporte.estado})`);
    const revisado = { ...reporte, estado, motivoRechazo: motivo };
    this.listaReportes.set(id, revisado);
    return revisado;
  }
}
