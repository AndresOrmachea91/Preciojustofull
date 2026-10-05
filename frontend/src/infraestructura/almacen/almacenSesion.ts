/**
 * Dónde vive el token entre recargas. Es el único archivo que sabe que
 * existe localStorage.
 */
import type { AlmacenSesion } from "@/aplicacion/puertos";

const CLAVE = "preciojusto.sesion";

export class AlmacenSesionLocal implements AlmacenSesion {
  leer(): string | null {
    // Navegación privada o almacenamiento bloqueado: se sigue sin recordar
    // la sesión, en vez de romper la página.
    try {
      return globalThis.localStorage?.getItem(CLAVE) ?? null;
    } catch {
      return null;
    }
  }

  guardar(token: string): void {
    try {
      globalThis.localStorage?.setItem(CLAVE, token);
    } catch {
      // Sin almacenamiento la sesión dura lo que dura la pestaña.
    }
  }

  borrar(): void {
    try {
      globalThis.localStorage?.removeItem(CLAVE);
    } catch {
      // Nada que borrar.
    }
  }
}

export class AlmacenSesionMemoria implements AlmacenSesion {
  private token: string | null = null;

  leer(): string | null {
    return this.token;
  }

  guardar(token: string): void {
    this.token = token;
  }

  borrar(): void {
    this.token = null;
  }
}
