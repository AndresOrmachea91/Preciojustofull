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
  NuevaCuenta,
  SesionRepositorio,
} from "@/aplicacion/puertos";
import type { EstadoReporte, Permiso, ReporteEnRevision, Rol, Usuario } from "@/dominio/modelo";

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
  };
}

export class CuentasMemoria implements SesionRepositorio, AdministracionRepositorio {
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

  private actual(): Usuario {
    const id = Number(this.almacen.leer()?.replace("memoria:", ""));
    const usuario = this.cuentas.get(id)?.usuario;
    if (!usuario?.activo) throw new Error("Sesión inválida o vencida. Vuelva a ingresar.");
    return usuario;
  }

  private exigir(permiso: Permiso): void {
    if (!this.actual().permisos.includes(permiso)) throw new Error(`No tiene permiso para ${permiso}`);
  }

  async ingresar(correo: string, contrasena: string): Promise<{ token: string; usuario: Usuario }> {
    const cuenta = [...this.cuentas.values()].find(
      (c) => c.usuario.correo === correo.trim().toLowerCase(),
    );
    if (!cuenta || cuenta.contrasena !== contrasena || !cuenta.usuario.activo) {
      throw new Error("Correo o contraseña incorrectos");
    }
    return { token: `memoria:${cuenta.usuario.id}`, usuario: cuenta.usuario };
  }

  async registrarse(cuenta: NuevaCuenta): Promise<Usuario> {
    return this.alta(cuenta, "usuario");
  }

  private alta(cuenta: NuevaCuenta, rol: Rol): Usuario {
    const correo = cuenta.correo.trim().toLowerCase();
    if ([...this.cuentas.values()].some((c) => c.usuario.correo === correo)) {
      throw new Error(`Ya existe una cuenta con el correo ${correo}`);
    }
    if (cuenta.contrasena.length < 8) throw new Error("La contraseña debe tener al menos 8 caracteres");
    return this.agregar(crear(0, correo, cuenta.nombre || correo.split("@")[0], rol), cuenta.contrasena);
  }

  async yo(): Promise<Usuario> {
    return this.actual();
  }

  async usuarios(): Promise<Usuario[]> {
    this.exigir("gestionar_usuarios");
    return [...this.cuentas.values()].map((c) => c.usuario);
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
    const esAdmin = (u: Usuario) => u.activo && u.rol === "administrador";
    const admins = [...this.cuentas.values()].filter((c) => esAdmin(c.usuario)).length;
    if (esAdmin(antes) && !esAdmin(despues) && admins <= 1) {
      throw new Error("Debe quedar al menos un administrador activo");
    }
    cuenta.usuario = despues;
    return despues;
  }

  async restablecerContrasena(id: number, contrasena: string): Promise<Usuario> {
    this.exigir("gestionar_usuarios");
    const cuenta = this.cuentas.get(id);
    if (!cuenta) throw new Error(`No existe el usuario ${id}`);
    cuenta.contrasena = contrasena;
    return cuenta.usuario;
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
