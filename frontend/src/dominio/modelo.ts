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
  /** En qué se publica el precio: kg, l, u (unidad) o atado. */
  readonly unidadBase: UnidadBase;
  /** Cómo se vende: kilo, libra, arroba, quintal... Siempre incluye la de factor 1. */
  readonly presentaciones: readonly Presentacion[];
  readonly diasConservacion: number;
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
  /** Cuántos de los productos cubiertos son estimados (nadie los midió en ese lugar). */
  readonly productosEstimados: number;
  /** Un total mayorista no compite con uno de consumidor final. */
  readonly nivelPrecio: NivelPrecio;
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
  /** Quién y cuándo la creó o la cambió. Solo llega en el listado del administrador. */
  readonly auditoria?: Auditoria | null;
}

// --- auditoría y catálogos de referencia -------------------------------------

/** Los 5 campos que tiene cada fila de cada tabla. Los escribe el sistema, nunca una persona. */
export interface Auditoria {
  readonly creadoEn: string;
  readonly creadoPor: string;
  readonly modificadoEn: string | null;
  readonly modificadoPor: string | null;
  readonly eliminado: boolean;
}

export type AccionAuditada = "creado" | "modificado" | "eliminado";

/** Una fila de cualquier tabla vista por su auditoría. */
export interface RegistroAuditado {
  readonly tabla: string;
  readonly clave: string;
  readonly descripcion: string;
  readonly accion: AccionAuditada;
  readonly ultimoCambio: string;
  readonly auditoria: Auditoria;
}

export interface RolDescrito {
  readonly codigo: Rol;
  readonly nombre: string;
  readonly descripcion: string;
  readonly permisos: readonly { readonly codigo: Permiso; readonly descripcion: string }[];
}

export interface FuenteDescrita {
  readonly codigo: string;
  readonly nombre: string;
  readonly descripcion: string;
  readonly confianzaBase: NivelConfianza;
  readonly derivaDe: string | null;
  readonly automatica: boolean;
  readonly url: string | null;
}

export interface Referencias {
  readonly roles: readonly RolDescrito[];
  readonly fuentes: readonly FuenteDescrita[];
}

/** Quién hizo lo último sobre una fila: el que la modificó o, si nadie, el que la creó. */
export function autorDelUltimoCambio(a: Auditoria): string {
  return a.modificadoPor ?? a.creadoPor;
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

// --- presentaciones de venta y catálogo -------------------------------------

export type UnidadBase = "kg" | "l" | "u" | "atado";

/** Una presentación de venta. `factor`: cuántas unidades base trae (un quintal = 46 kg). */
export interface Presentacion {
  readonly codigo: string;
  readonly nombre: string;
  readonly factor: number;
}

/**
 * Las presentaciones que existen, por unidad base. Es la misma tabla que
 * dominio/modelo/presentacion.py del backend: una libra de mercado son
 * 0,46 kg, una arroba 11,5 kg, un quintal 46 kg y un maple 30 huevos.
 */
export const PRESENTACIONES_POR_UNIDAD: Record<UnidadBase, readonly Presentacion[]> = {
  kg: [
    { codigo: "libra", nombre: "Libra", factor: 0.46 },
    { codigo: "kilo", nombre: "Kilo", factor: 1 },
    { codigo: "arroba", nombre: "Arroba", factor: 11.5 },
    { codigo: "quintal", nombre: "Quintal", factor: 46 },
  ],
  l: [{ codigo: "litro", nombre: "Litro", factor: 1 }],
  u: [
    { codigo: "unidad", nombre: "Unidad", factor: 1 },
    { codigo: "docena", nombre: "Docena", factor: 12 },
    { codigo: "maple", nombre: "Maple (30)", factor: 30 },
  ],
  atado: [{ codigo: "atado", nombre: "Atado", factor: 1 }],
};

export const NOMBRE_UNIDAD_BASE: Record<UnidadBase, string> = {
  kg: "Kilo",
  l: "Litro",
  u: "Unidad",
  atado: "Atado",
};

/** La presentación de factor 1: la unidad en la que el sistema guarda y compara. */
export function presentacionBase(producto: Producto): Presentacion {
  return producto.presentaciones.find((p) => p.factor === 1) ?? { codigo: producto.unidadBase, nombre: NOMBRE_UNIDAD_BASE[producto.unidadBase], factor: 1 };
}

/**
 * El mismo precio expresado en otra presentación: el rango se multiplica
 * por el factor y la unidad pasa a ser la presentación. La procedencia, la
 * confianza y las observaciones no cambian: es el mismo dato, otra escala.
 */
/** En qué se mide una presentación: la arroba en kg, la docena en unidades. */
export function unidadDePresentacion(codigo: string): UnidadBase | null {
  for (const [unidad, lista] of Object.entries(PRESENTACIONES_POR_UNIDAD) as [UnidadBase, readonly Presentacion[]][]) {
    if (lista.some((p) => p.codigo === codigo)) return unidad;
  }
  return null;
}

/**
 * El precio llevado a otra presentación. Solo dentro de la misma magnitud:
 * un precio por unidad (un limón) no se pasa a arroba, porque habría que
 * inventar cuánto pesa un limón. En ese caso se devuelve tal cual.
 */
export function precioEnPresentacion(precio: Precio, presentacion: Presentacion): Precio {
  if (presentacion.factor === 1) return precio;
  if (unidadDePresentacion(presentacion.codigo) !== precio.unidad) return precio;
  const f = presentacion.factor;
  return {
    ...precio,
    rango: { minimo: precio.rango.minimo * f, maximo: precio.rango.maximo * f, centro: precio.rango.centro * f },
    unidad: presentacion.nombre.toLowerCase(),
  };
}

export const TIPOS_PUNTO_VENTA: readonly TipoPuntoVenta[] = ["mercado", "supermercado", "minimarket", "tienda", "mayorista"];

export const CATEGORIAS: readonly { codigo: string; nombre: string }[] = [
  { codigo: "hortaliza", nombre: "Hortaliza" },
  { codigo: "tuberculo", nombre: "Tubérculo" },
  { codigo: "fruta", nombre: "Fruta" },
  { codigo: "carne", nombre: "Carne" },
  { codigo: "pescado", nombre: "Pescado" },
  { codigo: "lacteo", nombre: "Lácteo" },
  { codigo: "abarrote", nombre: "Abarrote" },
  { codigo: "otro", nombre: "Otro" },
];

/** Área que cubre el sistema (La Paz y El Alto). La misma regla que el backend. */
export interface Coordenadas {
  readonly latitud: number;
  readonly longitud: number;
}

/** Distancia en línea recta, en km (fórmula del haversine; alcanza para una ciudad). */
export function distanciaKm(a: Coordenadas, b: Coordenadas): number {
  const rad = (g: number) => (g * Math.PI) / 180;
  const dLat = rad(b.latitud - a.latitud);
  const dLon = rad(b.longitud - a.longitud);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.latitud)) * Math.cos(rad(b.latitud)) * Math.sin(dLon / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.sqrt(h));
}

export interface PuntoCercano {
  readonly marcador: MarcadorMapa;
  readonly distanciaKm: number;
}

/**
 * Los puntos con precio más cercanos a una ubicación. Solo los que tienen
 * precio: un lugar cercano sin dato no ayuda a decidir dónde comprar.
 */
export function masCercanos(marcadores: readonly MarcadorMapa[], aqui: Coordenadas, cuantos = 5): PuntoCercano[] {
  return marcadores
    .filter((m) => m.precio && m.mercado.latitud !== undefined && m.mercado.longitud !== undefined)
    .map((m) => ({ marcador: m, distanciaKm: distanciaKm(aqui, { latitud: m.mercado.latitud!, longitud: m.mercado.longitud! }) }))
    .sort((a, b) => a.distanciaKm - b.distanciaKm)
    .slice(0, cuantos);
}

/** "350 m" o "1,4 km". */
export function textoDistancia(km: number): string {
  return km < 1 ? `${Math.round((km * 1000) / 10) * 10} m` : `${km.toFixed(1).replace(".", ",")} km`;
}

export function ubicacionValida(latitud: number | null, longitud: number | null): boolean {
  if (latitud === null && longitud === null) return true;
  if (latitud === null || longitud === null) return false;
  return latitud >= -16.7 && latitud <= -16.3 && longitud >= -68.35 && longitud <= -67.95;
}

// --- usuario: listas de compras ---------------------------------------------

/** Un renglón: "2 arrobas de papa". La cantidad va en la presentación que piensa la persona. */
export interface ItemLista {
  readonly codigoProducto: string;
  readonly cantidad: number;
  /** Código de presentación: kilo, arroba, quintal, maple... */
  readonly presentacion: string;
}

export interface ListaCompras {
  readonly id: number;
  readonly nombre: string;
  readonly items: readonly ItemLista[];
}

/** Cuánto suma un renglón en la unidad base del producto (2 arrobas = 23 kg). */
export function enUnidadBase(item: ItemLista, producto: Producto): number {
  const presentacion = producto.presentaciones.find((p) => p.codigo === item.presentacion);
  return item.cantidad * (presentacion?.factor ?? 1);
}

/** Plural de una presentación: arroba → arrobas, quintal → quintales, maple (30) → maples (30). */
export function enPlural(nombre: string): string {
  const [palabra, ...resto] = nombre.split(" ");
  const plural = /[aeiou]$/i.test(palabra) ? `${palabra}s` : `${palabra}es`;
  return [plural, ...resto].join(" ");
}

/** Texto legible de un renglón: "2 arrobas de Papa holandesa". */
export function describirItem(item: ItemLista, producto: Producto | undefined): string {
  const presentacion = producto?.presentaciones.find((p) => p.codigo === item.presentacion);
  const nombre = (presentacion?.nombre ?? item.presentacion).toLowerCase();
  return `${item.cantidad} ${item.cantidad === 1 ? nombre : enPlural(nombre)} de ${producto?.nombre ?? item.codigoProducto}`;
}

// --- vendedor ----------------------------------------------------------------

/** Lo último que el vendedor publicó de un producto en su puesto. */
export interface PrecioPublicado {
  readonly codigoProducto: string;
  readonly nombreProducto: string;
  readonly monto: number;
  readonly presentacion: string;
  /** El mismo precio por kilo (o litro, o unidad): con eso se compara. */
  readonly precioPorUnidadBase: number;
  readonly unidadBase: UnidadBase;
  readonly publicadoEn: string;
}

// --- historial de precios ----------------------------------------------------

/** El precio de referencia de la ciudad en un mes, en la unidad base del producto. */
export interface PuntoHistorial {
  /** "2026-09" */
  readonly periodo: string;
  readonly nivel: NivelPrecio;
  readonly precio: number;
  readonly observaciones: number;
}

export interface HistorialPrecio {
  readonly unidad: UnidadBase;
  readonly puntos: readonly PuntoHistorial[];
}

/** Cuánto cambió una serie entre su primer y su último mes, en porcentaje. Null si no hay dos meses. */
export function variacionPorcentual(puntos: readonly PuntoHistorial[], nivel: NivelPrecio): number | null {
  const serie = puntos.filter((p) => p.nivel === nivel);
  if (serie.length < 2 || serie[0].precio === 0) return null;
  return Math.round(((serie[serie.length - 1].precio - serie[0].precio) / serie[0].precio) * 1000) / 10;
}
