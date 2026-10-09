import type { Usuario } from "@/dominio/modelo";
import type { AlmacenSesion, NuevaCuenta, SesionRepositorio } from "@/aplicacion/puertos";

/**
 * Ingreso, registro y cierre de sesión. El token vive en el almacén; el
 * usuario se vuelve a pedir al backend al recargar, para que un cambio de
 * rol o una desactivación se vean sin tener que salir y volver a entrar.
 */
export class GestionarSesion {
  constructor(
    private readonly repositorio: SesionRepositorio,
    private readonly almacen: AlmacenSesion,
  ) {}

  async ingresar(correo: string, contrasena: string): Promise<Usuario> {
    const { token, usuario } = await this.repositorio.ingresar(correo, contrasena);
    this.almacen.guardar(token);
    return usuario;
  }

  /** Crea la cuenta y deja la sesión iniciada. */
  async registrarse(cuenta: NuevaCuenta): Promise<Usuario> {
    await this.repositorio.registrarse(cuenta);
    return this.ingresar(cuenta.correo, cuenta.contrasena);
  }

  /** La sesión guardada, si sigue valiendo. Un token vencido se descarta. */
  async restaurar(): Promise<Usuario | null> {
    if (!this.almacen.leer()) return null;
    try {
      return await this.repositorio.yo();
    } catch {
      this.almacen.borrar();
      return null;
    }
  }

  salir(): void {
    this.almacen.borrar();
  }
}
