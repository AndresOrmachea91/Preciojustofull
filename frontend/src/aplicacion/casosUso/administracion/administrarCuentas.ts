import { celularBoliviano, type CaseraRegistrada, type EstadoReporte, type NuevaCasera, type ReporteEnRevision, type Rol, type Usuario } from "@/dominio/modelo";
import type { AdministracionRepositorio, NuevaCuenta } from "@/aplicacion/puertos";

/**
 * Lo que hace el administrador: cuentas y revisión de reportes. Las
 * validaciones de verdad (permisos, último administrador) están en el
 * backend; acá se valida solo lo que conviene avisar antes de enviar.
 */
export class Administrar {
  constructor(private readonly repositorio: AdministracionRepositorio) {}

  usuarios(incluirEliminados = false): Promise<Usuario[]> {
    return this.repositorio.usuarios(incluirEliminados);
  }

  /** El backend impide eliminarse a sí mismo y al último administrador; acá se avisa antes. */
  eliminarUsuario(id: number, yo: Usuario): Promise<void> {
    if (id === yo.id) return Promise.reject(new Error("No puede eliminar su propia cuenta"));
    return this.repositorio.eliminarUsuario(id);
  }

  /** C144: registrar a una casera en su puesto. Se avisa antes lo que el backend igual rechazaría. */
  registrarCasera(casera: NuevaCasera): Promise<CaseraRegistrada> {
    if (!casera.nombre.trim()) return Promise.reject(new Error("Escriba el nombre de la casera"));
    if (!celularBoliviano(casera.celular)) {
      return Promise.reject(new Error("El celular debe tener 8 dígitos y empezar en 6 o 7"));
    }
    if (!casera.codigoMercado) return Promise.reject(new Error("Elija el mercado"));
    if (!casera.numero.trim()) return Promise.reject(new Error("Escriba el número del puesto"));
    return this.repositorio.registrarCasera(casera);
  }

  crearUsuario(cuenta: NuevaCuenta & { rol: Rol }): Promise<Usuario> {
    return this.repositorio.crearUsuario({ ...cuenta, correo: cuenta.correo.trim() });
  }

  cambiarRol(id: number, rol: Rol): Promise<Usuario> {
    return this.repositorio.actualizarUsuario(id, { rol });
  }

  cambiarActivo(id: number, activo: boolean): Promise<Usuario> {
    return this.repositorio.actualizarUsuario(id, { activo });
  }

  /** Asigna (o quita, con null) el puesto o tienda de un vendedor. */
  asignarPuntoVenta(id: number, codigo: string | null): Promise<Usuario> {
    return this.repositorio.actualizarUsuario(id, { codigoPuntoVenta: codigo });
  }

  restablecerContrasena(id: number, contrasena: string): Promise<Usuario> {
    return this.repositorio.restablecerContrasena(id, contrasena);
  }

  reportes(estado: EstadoReporte | "todos" = "pendiente"): Promise<ReporteEnRevision[]> {
    return this.repositorio.reportes(estado);
  }

  aprobar(id: number): Promise<ReporteEnRevision> {
    return this.repositorio.aprobarReporte(id);
  }

  rechazar(id: number, motivo: string): Promise<ReporteEnRevision> {
    if (motivo.trim().length < 3) {
      return Promise.reject(new Error("Escriba el motivo del rechazo (al menos 3 caracteres)"));
    }
    return this.repositorio.rechazarReporte(id, motivo.trim());
  }
}
