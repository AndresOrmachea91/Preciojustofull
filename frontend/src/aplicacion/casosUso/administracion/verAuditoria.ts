import type { Referencias, RegistroAuditado } from "@/dominio/modelo";
import type { AuditoriaRepositorio } from "@/aplicacion/puertos";

/**
 * La auditoría del sistema, para el administrador: quién creó, modificó o
 * eliminó cada registro, y qué roles y fuentes existen. Solo lectura.
 */
export class VerAuditoria {
  constructor(private readonly repositorio: AuditoriaRepositorio) {}

  tablas(): Promise<string[]> {
    return this.repositorio.tablasAuditadas();
  }

  /** Lo más reciente primero. Sin tabla, de todas. */
  recientes(tabla?: string, limite = 50): Promise<RegistroAuditado[]> {
    return this.repositorio.auditoria(tabla || undefined, limite);
  }

  referencias(): Promise<Referencias> {
    return this.repositorio.referencias();
  }
}
