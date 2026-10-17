import { problemaConContrasena } from "@/dominio/modelo";
import type { RecuperacionRepositorio } from "@/aplicacion/puertos";

/**
 * Olvidé mi contraseña: pedir el enlace al correo y, con él, elegir una
 * nueva. Las reglas de verdad están en el backend; acá se avisa antes.
 */
export class RecuperarContrasena {
  constructor(private readonly repositorio: RecuperacionRepositorio) {}

  pedirEnlace(correo: string): Promise<void> {
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(correo.trim())) {
      return Promise.reject(new Error("Escriba el correo con el que creó su cuenta"));
    }
    return this.repositorio.pedirEnlace(correo.trim());
  }

  restablecer(token: string, contrasena: string, repetida: string): Promise<void> {
    if (!token) return Promise.reject(new Error("El enlace está incompleto. Ábralo de nuevo desde el correo."));
    if (contrasena !== repetida) return Promise.reject(new Error("Las dos contraseñas no coinciden"));
    const problema = problemaConContrasena(contrasena);
    if (problema) return Promise.reject(new Error(problema));
    return this.repositorio.restablecerConEnlace(token, contrasena);
  }
}
