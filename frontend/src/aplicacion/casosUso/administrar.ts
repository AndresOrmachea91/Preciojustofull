import type { EstadoReporte, ReporteEnRevision, Rol, Usuario } from "@/dominio/modelo";
import type { AdministracionRepositorio, NuevaCuenta } from "@/aplicacion/puertos";

/**
 * Lo que hace el administrador: cuentas y revisión de reportes. Las
 * validaciones de verdad (permisos, último administrador) están en el
 * backend; acá se valida solo lo que conviene avisar antes de enviar.
 */
export class Administrar {
  constructor(private readonly repositorio: AdministracionRepositorio) {}

  usuarios(): Promise<Usuario[]> {
    return this.repositorio.usuarios();
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
