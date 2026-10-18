/**
 * Confiabilidad y operación sin backend (modo demo). No hay mediciones de
 * campo contra las que medir ni recolector ni respaldos: se dice eso, no se
 * inventan números.
 */
import type { ConfiabilidadRepositorio, OperacionRepositorio } from "@/aplicacion/puertos";
import type { EvaluacionEstimador, ResultadoImportacion, SaludSistema } from "@/dominio/modelo";

export class OperacionMemoria implements ConfiabilidadRepositorio, OperacionRepositorio {
  async evaluacion(): Promise<EvaluacionEstimador> {
    return {
      casos: 0,
      errorMedio: null,
      sesgo: null,
      cobertura: null,
      errorMedioSinFactor: null,
      elFactorAyuda: null,
      mercados: 0,
      productos: 0,
      porProducto: [],
      detalle: [],
      calculadoEn: new Date().toISOString(),
    };
  }

  async importarCampo(csv: string, _archivo: string, soloRevisar: boolean): Promise<ResultadoImportacion> {
    const filas = csv.trim().split(/\r?\n/).length - 1;
    return {
      leidas: filas,
      validas: 0,
      guardadas: 0,
      soloRevisar,
      rechazadas: [{ fila: 0, motivo: "El modo demo no guarda planillas: conecte la API para importar." }],
    };
  }

  async salud(): Promise<SaludSistema> {
    return {
      estadoGeneral: "sin_datos",
      puntos: [
        { nombre: "Recolección del SIIP", estado: "sin_datos", detalle: "El modo demo no recolecta." },
        { nombre: "Respaldo de la base", estado: "sin_datos", detalle: "El modo demo no tiene base de datos." },
        { nombre: "Precios observados", estado: "sin_datos", detalle: "Datos de ejemplo fijos." },
      ],
      fuentes: [],
      recolecciones: [],
      respaldo: null,
      coberturaObservada: null,
      ventanaDias: 30,
    };
  }
}
