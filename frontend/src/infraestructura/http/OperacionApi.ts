/**
 * Adaptador HTTP de la confiabilidad del estimado (/api/v1/precios/confiabilidad)
 * y de la operación del administrador (/api/v1/admin/campo/importar y /admin/salud).
 */
import type { ConfiabilidadRepositorio, OperacionRepositorio } from "@/aplicacion/puertos";
import type { EvaluacionEstimador, ResultadoImportacion, SaludSistema } from "@/dominio/modelo";
import type { ClienteHttp } from "@/infraestructura/http/clienteHttp";

interface EvaluacionDto {
  casos: number;
  error_medio: number | null;
  sesgo: number | null;
  cobertura: number | null;
  error_medio_sin_factor: number | null;
  el_factor_ayuda: boolean | null;
  mercados: number;
  productos: number;
  por_producto: { codigo_producto: string; nombre_producto: string; casos: number; error_medio: number; cobertura: number }[];
  detalle: {
    nombre_producto: string;
    nombre_mercado: string;
    periodo: string;
    observado: number;
    estimado: number;
    estimado_minimo: number;
    estimado_maximo: number;
    sin_factor: number;
    error: number;
    dentro_del_rango: boolean;
  }[];
  calculado_en: string;
}

interface SaludDto {
  estado_general: SaludSistema["estadoGeneral"];
  puntos: SaludSistema["puntos"][number][];
  fuentes: { fuente: string; observaciones: number; ultima_captura: string | null }[];
  recolecciones: { fuente: string; ocurrido_en: string; exito: boolean; detalle: string | null; hechos_nuevos_24h: number }[];
  respaldo: {
    fecha: string | null;
    archivo: string | null;
    tamano_bytes: number | null;
    verificado: boolean;
    filas_observaciones: number | null;
    detalle: string | null;
  } | null;
  cobertura_observada: number | null;
  ventana_dias: number;
}

export class OperacionApi implements ConfiabilidadRepositorio, OperacionRepositorio {
  constructor(private readonly http: ClienteHttp) {}

  async evaluacion(): Promise<EvaluacionEstimador> {
    const d = await this.http.get<EvaluacionDto>("/precios/confiabilidad");
    return {
      casos: d.casos,
      errorMedio: d.error_medio,
      sesgo: d.sesgo,
      cobertura: d.cobertura,
      errorMedioSinFactor: d.error_medio_sin_factor,
      elFactorAyuda: d.el_factor_ayuda,
      mercados: d.mercados,
      productos: d.productos,
      porProducto: d.por_producto.map((p) => ({
        codigoProducto: p.codigo_producto,
        nombreProducto: p.nombre_producto,
        casos: p.casos,
        errorMedio: p.error_medio,
        cobertura: p.cobertura,
      })),
      detalle: d.detalle.map((c) => ({
        nombreProducto: c.nombre_producto,
        nombreMercado: c.nombre_mercado,
        periodo: c.periodo,
        observado: c.observado,
        estimado: c.estimado,
        estimadoMinimo: c.estimado_minimo,
        estimadoMaximo: c.estimado_maximo,
        sinFactor: c.sin_factor,
        error: c.error,
        dentroDelRango: c.dentro_del_rango,
      })),
      calculadoEn: d.calculado_en,
    };
  }

  async importarCampo(csv: string, archivo: string, soloRevisar: boolean): Promise<ResultadoImportacion> {
    const d = await this.http.post<{
      leidas: number;
      validas: number;
      guardadas: number;
      solo_revisar: boolean;
      rechazadas: { fila: number; motivo: string }[];
    }>("/admin/campo/importar", { csv, archivo, solo_revisar: soloRevisar });
    return { leidas: d.leidas, validas: d.validas, guardadas: d.guardadas, soloRevisar: d.solo_revisar, rechazadas: d.rechazadas };
  }

  async salud(): Promise<SaludSistema> {
    const d = await this.http.get<SaludDto>("/admin/salud");
    return {
      estadoGeneral: d.estado_general,
      puntos: d.puntos,
      fuentes: d.fuentes.map((f) => ({ fuente: f.fuente, observaciones: f.observaciones, ultimaCaptura: f.ultima_captura })),
      recolecciones: d.recolecciones.map((r) => ({
        fuente: r.fuente,
        ocurridoEn: r.ocurrido_en,
        exito: r.exito,
        detalle: r.detalle,
        hechosNuevos24h: r.hechos_nuevos_24h,
      })),
      respaldo: d.respaldo && {
        fecha: d.respaldo.fecha,
        archivo: d.respaldo.archivo,
        tamanoBytes: d.respaldo.tamano_bytes,
        verificado: d.respaldo.verificado,
        filasObservaciones: d.respaldo.filas_observaciones,
        detalle: d.respaldo.detalle,
      },
      coberturaObservada: d.cobertura_observada,
      ventanaDias: d.ventana_dias,
    };
  }
}
