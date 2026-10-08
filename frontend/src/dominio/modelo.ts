/**
 * Modelo del dominio.
 *
 * Tipos y reglas puras. No importa React, ni fetch, ni Leaflet, ni nada del
 * navegador. Si mañana la aplicación se reescribe en otro framework, este
 * archivo no cambia una línea.
 */

export type NivelConfianza = "verificado" | "alto" | "medio" | "bajo";

export type TipoPuntoVenta = "mercado" | "minimarket" | "tienda" | "supermercado" | "mayorista";

/** A qué altura de la cadena está el precio. Dos números de niveles distintos no compiten. */
export type NivelPrecio = "mayorista" | "minorista";

/**
 * De dónde sale un precio. OBSERVADO: alguien lo midió en ese lugar.
 * ESTIMADO: se calculó desde la referencia de la ciudad y un factor. Un
 * precio sin procedencia no existe en este modelo.
 */
export type Procedencia = "observado" | "estimado";

export interface RangoPrecio {
  readonly minimo: number;
  readonly maximo: number;
  readonly centro: number;
}

export interface Precio {
  readonly codigoProducto: string;
  readonly codigoMercado: string;
  readonly periodo: string;
  readonly rango: RangoPrecio;
  readonly unidad: string;
  readonly confianza: NivelConfianza;
  readonly procedencia: Procedencia;
  readonly observacionesUsadas: number;
  /** Fecha de la observación más reciente que lo respalda; null si ninguna la trae. */
  readonly fechaObservacionMasReciente: string | null;
  readonly conflictos: readonly string[];
}

export interface Mercado {
  readonly codigo: string;
  readonly nombre: string;
  readonly tipo: TipoPuntoVenta;
  readonly zona: string;
  readonly macrodistrito: string;
  /** Código del mercado que lo contiene, si es un sector de otro. */
  readonly codigoPadre: string | null;
  readonly nivelPrecio: NivelPrecio;
  readonly latitud?: number;
  readonly longitud?: number;
}

export interface Producto {
  readonly codigo: string;
  readonly nombre: string;
  readonly categoria: string;
  readonly esPerecedero: boolean;
}

export interface PrecioEnMercado {
  readonly mercado: Mercado;
  readonly precio: Precio;
}

/** Un punto en el mapa: el lugar, y su precio si el sistema tiene uno. */
export interface MarcadorMapa {
  readonly mercado: Mercado;
  readonly precio: Precio | null;
}

export interface ItemCanasta {
  readonly codigoProducto: string;
  readonly cantidad: number;
}

export interface CostoCanasta {
  readonly codigoMercado: string;
  readonly nombreMercado: string;
  readonly zona: string;
  readonly costoTotal: number;
  readonly productosCubiertos: number;
  readonly productosPedidos: number;
  readonly cobertura: number;
  readonly faltantes: readonly string[];
}

/**
 * En un mercado grande hay decenas de puestos y se regatea, así que se
 * publica un rango. En una tienda o minimarket hay un dueño y el precio
 * está puesto, así que se puede mostrar el precio de ese local.
 */
export function publicaRango(tipo: TipoPuntoVenta): boolean {
  return tipo === "mercado";
}

export function etiquetaConfianza(nivel: NivelConfianza): string {
  const etiquetas: Record<NivelConfianza, string> = {
    verificado: "Verificado en campo",
    alto: "Fuente oficial",
    medio: "Estimado",
    bajo: "Dato único sin contraste",
  };
  return etiquetas[nivel];
}

export function etiquetaTipo(tipo: TipoPuntoVenta): string {
  const etiquetas: Record<TipoPuntoVenta, string> = {
    mercado: "Mercado",
    minimarket: "Minimarket",
    tienda: "Tienda",
    supermercado: "Supermercado",
    mayorista: "Mayorista",
  };
  return etiquetas[tipo];
}

export function etiquetaNivel(nivel: NivelPrecio): string {
  return nivel === "mayorista" ? "Precio mayorista" : "Precio al consumidor";
}

export function etiquetaProcedencia(procedencia: Procedencia): string {
  return procedencia === "observado" ? "Observado en este lugar" : "Estimado";
}

/**
 * La explicación que acompaña a todo precio. No es letra chica: es lo que
 * el usuario tiene que saber para decidir cuánto creerle.
 */
export function explicacionProcedencia(precio: Precio, mercado?: Mercado): string {
  const n = precio.observacionesUsadas;
  const respaldo = `${n} ${n === 1 ? "observación" : "observaciones"} de la fuente oficial`;
  if (precio.procedencia === "estimado") {
    const lugar = mercado ? `en ${mercado.nombre}` : "en este lugar";
    return (
      `Estimado a partir del precio de referencia de la ciudad (${respaldo}). ` +
      `Todavía nadie verificó este precio ${lugar}.`
    );
  }
  return `Medido en este lugar: ${n} ${n === 1 ? "observación" : "observaciones"}.`;
}

// --- cuentas y sesiones --------------------------------------------------

export type Rol = "usuario" | "vendedor" | "administrador";

export type Permiso =
  | "reportar_precio"
  | "gestionar_listas"
  | "publicar_precio_propio"
  | "gestionar_usuarios"
  | "gestionar_catalogo"
  | "validar_reportes"
  | "ver_auditoria";

export const ROLES: readonly Rol[] = ["usuario", "vendedor", "administrador"];

export const NOMBRE_ROL: Record<Rol, string> = {
  usuario: "Usuario",
  vendedor: "Vendedor",
  administrador: "Administrador",
};

/**
 * Los permisos los decide el backend y llegan con el usuario: la interfaz
 * solo muestra u oculta acciones según esa lista, nunca repite la matriz.
 * Ocultar un botón es comodidad; quien protege de verdad es la API.
 */
export interface Usuario {
  readonly id: number;
  readonly correo: string;
  readonly nombre: string;
  readonly rol: Rol;
  readonly activo: boolean;
  readonly creadoEn: string;
  readonly permisos: readonly Permiso[];
  /** Solo vendedores: el código del puesto o tienda que le asignó el administrador. */
  readonly codigoPuntoVenta: string | null;
}

export function puede(usuario: Usuario | null, permiso: Permiso): boolean {
  return usuario !== null && usuario.activo && usuario.permisos.includes(permiso);
}

export type EstadoReporte = "pendiente" | "aprobado" | "rechazado";

export interface ReporteEnRevision {
  readonly id: number;
  readonly codigoProducto: string;
  readonly codigoMercado: string;
  readonly monto: number;
  readonly unidad: string;
  readonly idAutor: number;
  readonly creadoEn: string;
  readonly estado: EstadoReporte;
  readonly motivoRechazo: string | null;
}
