import type { ReporteEnRevision } from "@/dominio/modelo";
import type { MisReportesRepositorio, ReporteRepositorio } from "@/aplicacion/puertos";

/** El usuario reporta un precio que vio y sigue en qué quedó cada reporte. */
export class ReportarPrecio {
  constructor(
    private readonly reportes: ReporteRepositorio,
    private readonly mios: MisReportesRepositorio,
  ) {}

  reportar(entrada: {
    codigoProducto: string;
    codigoMercado: string;
    monto: number;
    /** Código de presentación (kilo, arroba...). */
    presentacion: string;
  }): Promise<void> {
    if (!entrada.codigoProducto || !entrada.codigoMercado) {
      return Promise.reject(new Error("Elija el producto y el lugar donde lo vio"));
    }
    if (!(entrada.monto > 0)) return Promise.reject(new Error("Escriba el precio que vio"));
    return this.reportes.reportar({
      codigoProducto: entrada.codigoProducto,
      codigoMercado: entrada.codigoMercado,
      monto: entrada.monto,
      // "ARROBA", "QUINTAL": el texto de unidad que entiende el backend.
      unidad: entrada.presentacion.toUpperCase(),
    });
  }

  misReportes(): Promise<ReporteEnRevision[]> {
    return this.mios.misReportes();
  }
}
