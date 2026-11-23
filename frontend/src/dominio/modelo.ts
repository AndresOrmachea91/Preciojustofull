/**
 * Modelo del dominio.
 *
 * Tipos y reglas puras. No importa React, ni fetch, ni Leaflet, ni nada del
 * navegador. Si mañana la aplicación se reescribe en otro framework, este
 * archivo no cambia una línea.
 */

export type NivelConfianza = "verificado" | "alto" | "medio" | "bajo";

/** Mercados, distribuidores y mayoristas. Las cadenas (supermercado, minimarket, tienda) salieron del sistema: decisión 26. */
export type TipoPuntoVenta = "mercado" | "distribuidor" | "mayorista" | "minimarket" | "tienda" | "supermercado";

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
  /** Voces INDEPENDIENTES por fuente: { vendedor: 1, ciudadano: 2 }. Una persona cuenta una vez. */
  readonly voces: Readonly<Record<string, number>>;
  /** Solo si es estimado: el factor del lugar que multiplicó el precio de la ciudad. */
  readonly factorMercado: number | null;
  /** Días desde el dato más reciente (null si el backend no lo calculó). */
  readonly antiguedadDias: number | null;
  /** Por qué el rango es más ancho de lo que da el desacuerdo entre fuentes. */
  readonly motivosRango: readonly string[];
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
  /** El rango del total: suma de los mínimos y de los máximos. 0 si no se conoce. */
  readonly costoMinimo: number;
  readonly costoMaximo: number;
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
    medio: "Confianza media",
    bajo: "Dato único sin contraste",
  };
  return etiquetas[nivel];
}

export function etiquetaTipo(tipo: TipoPuntoVenta): string {
  const etiquetas: Record<TipoPuntoVenta, string> = {
    mercado: "Mercado",
    distribuidor: "Distribuidor",
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
  const lugar = mercado ? `en ${mercado.nombre}` : "en este lugar";
  if (precio.procedencia === "estimado") {
    const factor = precio.factorMercado;
    const nombre = mercado?.nombre ?? "este lugar";
    const ajuste =
      factor === null || Math.abs(factor - 1) < 0.005
        ? ""
        : `, con un ajuste de ${factor > 1 ? "+" : "−"}${Math.round(Math.abs(factor - 1) * 100)} % porque ${nombre} ` +
          `suele estar ${factor > 1 ? "más caro" : "más barato"} que el promedio de la ciudad`;
    const n = precio.observacionesUsadas;
    return (
      `Calculado desde ${referenciaDeCiudad(precio.voces)} (${mesLegible(precio.periodo)}; ` +
      `${n} ${n === 1 ? "observación" : "observaciones"} de la fuente oficial)${ajuste}. ` +
      `Todavía nadie verificó este precio ${lugar}.`
    );
  }
  const cuando = precio.fechaObservacionMasReciente ? `Visto el ${fechaDiaMes(precio.fechaObservacionMasReciente)}` : "Visto";
  return `${cuando} por ${quienesHablan(precio.voces) || textoObservaciones(precio.observacionesUsadas)}.`;
}

/** Cada fuente dicha como la diría una persona, en singular y plural. */
const NOMBRE_DE_FUENTE: Record<string, readonly [string, string]> = {
  vendedor: ["un vendedor del puesto", "vendedores"],
  ciudadano: ["un comprador", "compradores"],
  campo: ["una medición de campo", "mediciones de campo"],
  medios: ["un medio de prensa", "medios de prensa"],
  prensa: ["la prensa (copia del SIIP)", "la prensa (copia del SIIP)"],
  siip_ipc: ["el SIIP (precio al consumidor de la ciudad)", "el SIIP (precio al consumidor de la ciudad)"],
  siip_diario: ["el SIIP (precio mayorista de la ciudad)", "el SIIP (precio mayorista de la ciudad)"],
};

/** De qué referencia de ciudad sale un estimado. */
function referenciaDeCiudad(voces: Readonly<Record<string, number>>): string {
  if (voces.siip_diario) return "el precio mayorista de la ciudad (SIIP)";
  if (voces.siip_ipc) return "el precio al consumidor de la ciudad (SIIP)";
  return "la referencia oficial de la ciudad";
}

/** "un vendedor del puesto y 2 compradores". Vacío si no hay voces. */
export function quienesHablan(voces: Readonly<Record<string, number>>): string {
  const partes = Object.entries(voces)
    .filter(([, n]) => n > 0)
    .sort(([, a], [, b]) => b - a)
    .map(([fuente, n]) => {
      const [uno, varios] = NOMBRE_DE_FUENTE[fuente] ?? [fuente, fuente];
      return n === 1 || uno === varios ? uno : `${n} ${varios}`;
    });
  if (partes.length <= 1) return partes[0] ?? "";
  return `${partes.slice(0, -1).join(", ")} y ${partes[partes.length - 1]}`;
}

function textoObservaciones(n: number): string {
  return `${n} ${n === 1 ? "observación" : "observaciones"}`;
}

const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];

/** "2026-09" o "2026-09-15" → "septiembre de 2026". */
export function mesLegible(periodo: string): string {
  const [anio, mes] = periodo.split("-").map(Number);
  return mes ? `${MESES[mes - 1]} de ${anio}` : String(anio);
}

/** "2026-10-12" → "12/10". */
export function fechaDiaMes(fecha: string): string {
  const [, mes, dia] = fecha.split("-");
  return `${dia}/${mes}`;
}

/** Días después de los cuales un precio se muestra atenuado: puede haber cambiado. */
export const DIAS_PRECIO_RECIENTE = 7;

/** Un precio observado de más de una semana: se muestra, pero avisando. */
export function esPrecioViejo(precio: Precio): boolean {
  return precio.antiguedadDias !== null && precio.antiguedadDias > DIAS_PRECIO_RECIENTE;
}

/** "hoy", "ayer", "hace 9 días". Null si no se sabe. */
export function textoAntiguedad(precio: Precio): string | null {
  const d = precio.antiguedadDias;
  if (d === null) return null;
  if (d === 0) return "hoy";
  if (d === 1) return "ayer";
  if (d >= 730) return `hace más de ${Math.floor(d / 365)} años`;
  if (d >= 365) return "hace más de un año";
  if (d >= 60) return `hace unos ${Math.round(d / 30)} meses`;
  return `hace ${d} días`;
}

/**
 * Dos precios EMPATAN cuando la diferencia es menor que la incertidumbre:
 * el centro de uno cae dentro del rango del otro. Es la misma regla que
 * el backend (dominio/servicio/rango_honesto.py). Decir que uno "gana"
 * por 20 centavos con un margen de 1 Bs sería inventar un ganador.
 */
export function empatan(a: RangoPrecio, b: RangoPrecio): boolean {
  const conRango = (r: RangoPrecio) => r.maximo > r.minimo;
  if (!conRango(a) && !conRango(b)) return false;
  return (a.minimo <= b.centro && b.centro <= a.maximo) || (b.minimo <= a.centro && a.centro <= b.maximo);
}

/** El rango de una lista cotizada en un lugar. */
export function rangoDeCosto(c: CostoCanasta): RangoPrecio {
  return { minimo: c.costoMinimo, maximo: c.costoMaximo, centro: c.costoTotal };
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
  | "ver_auditoria"
  | "importar_campo"
  | "ver_salud";

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

/** Qué le falta a una contraseña, o null si cumple. Es la regla del backend: se avisa antes de enviar. */
export function problemaConContrasena(contrasena: string): string | null {
  if (contrasena.length < 8) return "La contraseña debe tener al menos 8 caracteres";
  if (/^\d+$/.test(contrasena) || /^\p{L}+$/u.test(contrasena)) return "La contraseña debe combinar letras y números";
  return null;
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

/** Los que se pueden dar de alta: el sistema es de mercados y caseros, no de cadenas. */
export const TIPOS_PUNTO_VENTA: readonly TipoPuntoVenta[] = ["mercado", "distribuidor", "mayorista"];

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

/**
 * Zonas conocidas de La Paz y El Alto, por si el GPS no responde o está
 * apagado: "estoy en Sopocachi" alcanza para ordenar los mercados por cercanía.
 */
export interface Zona extends Coordenadas {
  readonly nombre: string;
}

export const ZONAS_DE_LA_PAZ: readonly Zona[] = [
  { nombre: "Centro", latitud: -16.4958, longitud: -68.1336 },
  { nombre: "Max Paredes", latitud: -16.4935, longitud: -68.1455 },
  { nombre: "Sopocachi", latitud: -16.5106, longitud: -68.1263 },
  { nombre: "Miraflores", latitud: -16.5013, longitud: -68.1174 },
  { nombre: "Villa Fátima", latitud: -16.4835, longitud: -68.1219 },
  { nombre: "Zona Sur", latitud: -16.5393, longitud: -68.0858 },
  { nombre: "El Alto (Ceja)", latitud: -16.5055, longitud: -68.163 },
];

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


// --- confiabilidad del estimado (backtest) ------------------------------------

export interface CasoEvaluado {
  readonly nombreProducto: string;
  readonly nombreMercado: string;
  readonly periodo: string;
  readonly observado: number;
  readonly estimado: number;
  readonly estimadoMinimo: number;
  readonly estimadoMaximo: number;
  readonly sinFactor: number;
  /** Error relativo con signo: positivo si el estimado se pasó. */
  readonly error: number;
  readonly dentroDelRango: boolean;
}

export interface ResumenEvaluacionProducto {
  readonly codigoProducto: string;
  readonly nombreProducto: string;
  readonly casos: number;
  readonly errorMedio: number;
  readonly cobertura: number;
}

/** Cuánto se equivoca el estimado frente a los precios que sí se midieron. */
export interface EvaluacionEstimador {
  readonly casos: number;
  readonly errorMedio: number | null;
  readonly sesgo: number | null;
  readonly cobertura: number | null;
  readonly errorMedioSinFactor: number | null;
  readonly elFactorAyuda: boolean | null;
  readonly mercados: number;
  readonly productos: number;
  readonly porProducto: readonly ResumenEvaluacionProducto[];
  readonly detalle: readonly CasoEvaluado[];
  readonly calculadoEn: string;
}

/** 0.084 → "8,4 %". */
export function porcentaje(valor: number, decimales = 1): string {
  return `${(valor * 100).toFixed(decimales).replace(".", ",")} %`;
}

/** Cómo leer el sesgo en una frase: si el estimado tiende a quedarse corto o a pasarse. */
export function lecturaDelSesgo(sesgo: number): string {
  if (Math.abs(sesgo) < 0.01) return "no tiende ni a quedarse corto ni a pasarse";
  return sesgo < 0 ? `tiende a quedarse corto (${porcentaje(Math.abs(sesgo))} por debajo)` : `tiende a pasarse (${porcentaje(sesgo)} por encima)`;
}

// --- administración: campo y salud ---------------------------------------------

export interface ResultadoImportacion {
  readonly leidas: number;
  readonly validas: number;
  readonly guardadas: number;
  readonly soloRevisar: boolean;
  readonly rechazadas: readonly { readonly fila: number; readonly motivo: string }[];
}

export type EstadoSalud = "bien" | "revisar" | "sin_datos";

export interface SaludSistema {
  readonly estadoGeneral: EstadoSalud;
  readonly puntos: readonly { readonly nombre: string; readonly estado: EstadoSalud; readonly detalle: string }[];
  readonly fuentes: readonly { readonly fuente: string; readonly observaciones: number; readonly ultimaCaptura: string | null }[];
  readonly recolecciones: readonly {
    readonly fuente: string;
    readonly ocurridoEn: string;
    readonly exito: boolean;
    readonly detalle: string | null;
    readonly hechosNuevos24h: number;
  }[];
  readonly respaldo: {
    readonly fecha: string | null;
    readonly archivo: string | null;
    readonly tamanoBytes: number | null;
    readonly verificado: boolean;
    readonly filasObservaciones: number | null;
    readonly detalle: string | null;
  } | null;
  readonly coberturaObservada: number | null;
  readonly ventanaDias: number;
}

// --- puestos, ofertas del casero (C133) y ficha del mercado (C134) ----------------

/** Un puesto dentro de un mercado: "el 14 del Rodríguez". */
export interface Puesto {
  readonly id: number | null;
  readonly codigoMercado: string;
  readonly numero: string;
  readonly nombre: string;
  /** Categorías del catálogo: hortaliza, carne... */
  readonly rubros: readonly string[];
  /** Cómo encontrarlo adentro: "pasillo de verduras, frente a la puerta 2". */
  readonly referencia: string;
  /** False si el número solo aparece en mediciones de campo: nadie lo registró todavía. */
  readonly registrado: boolean;
  /** Dirección de la foto del puesto, o null si todavía no tiene. */
  readonly foto: string | null;
  /** El local entero de una distribuidora: no tiene número de puesto. */
  readonly esLocal: boolean;
  /** C146: teléfono de contacto (celular de 8 dígitos o fijo de 7), si lo puso. */
  readonly celular: string | null;
}

/** Enlace para llamar: tel:+591… */
export function enlaceLlamar(telefono: string): string {
  return `tel:+591${telefono}`;
}

/** Enlace de WhatsApp, solo para celulares (8 dígitos que empiezan en 6 o 7). */
export function enlaceWhatsapp(telefono: string, texto = ""): string | null {
  if (!/^[67]\d{7}$/.test(telefono)) return null;
  return `https://wa.me/591${telefono}${texto ? `?text=${encodeURIComponent(texto)}` : ""}`;
}

/**
 * Una oferta vigente del casero, con su candado: el ahorro se mide contra
 * el precio del SISTEMA en ese mercado (sin la voz del casero), nunca
 * contra un "antes" que escribe él.
 */
export interface Oferta {
  readonly id: number;
  readonly codigoProducto: string;
  readonly nombreProducto: string;
  readonly unidadBase: UnidadBase;
  readonly codigoMercado: string;
  readonly nombreMercado: string;
  readonly numeroPuesto: string | null;
  readonly nombrePuesto: string | null;
  readonly monto: number;
  readonly presentacion: string;
  readonly precioPorUnidadBase: number;
  readonly desde: string;
  readonly hasta: string;
  readonly nota: string;
  /** C145: el combo al que pertenece ("Combo sopa"); null si es suelta. */
  readonly combo: string | null;
  /** El precio del sistema en ese mercado, por unidad base, y si es observado o estimado. */
  readonly precioSistema: number;
  readonly procedenciaSistema: Procedencia;
  readonly ahorroPorUnidad: number;
  /** 0.12 = 12 % más barata que el sistema. */
  readonly ahorroRelativo: number;
  readonly confirmaron: number;
  readonly desmintieron: number;
}

export type EstadoMiOferta = "activa" | "vencida" | "en_revision" | "retirada";

/** Una oferta tal como la ve el casero que la publicó. */
export interface MiOferta {
  readonly id: number;
  readonly codigoProducto: string;
  readonly nombreProducto: string;
  readonly monto: number;
  readonly presentacion: string;
  readonly precioPorUnidadBase: number;
  readonly desde: string;
  readonly hasta: string;
  readonly nota: string;
  /** C145: el combo al que pertenece; null si es suelta. */
  readonly combo: string | null;
  readonly estado: EstadoMiOferta;
  readonly confirmaron: number;
  readonly desmintieron: number;
}

/** Una oferta que dos compradores desmintieron: espera que el administrador la mire. */
export interface OfertaEnRevision {
  readonly id: number;
  readonly nombreProducto: string;
  readonly nombreMercado: string;
  readonly numeroPuesto: string | null;
  readonly monto: number;
  readonly presentacion: string;
  readonly hasta: string;
  readonly nota: string;
  readonly confirmaron: number;
  readonly desmintieron: number;
}

export interface ResultadoConfirmacion {
  readonly confirmaron: number;
  readonly desmintieron: number;
  /** Con este desmentido ya son dos personas: la oferta se pausó. */
  readonly pausada: boolean;
}

/** Cuánto dura una oferta: vence sola. */
export const DURACIONES_OFERTA = [24, 48, 72] as const;
export const MAXIMO_OFERTAS_ACTIVAS = 3;
/** C145: un combo junta de 2 a 3 productos y cuenta como UNA oferta activa. */
export const PRODUCTOS_POR_COMBO = { minimo: 2, maximo: 3 } as const;

/** Cuántas ofertas activas cuentan para el máximo: un combo entero cuenta como una. */
export function ofertasQueCuentan(ofertas: readonly { id: number; combo: string | null }[]): number {
  return new Set(ofertas.map((o) => o.combo ?? `#${o.id}`)).size;
}

/** El precio de un producto en un lugar, y cuánto se aparta de la ciudad. */
export interface PrecioDeProducto {
  readonly codigoProducto: string;
  readonly nombreProducto: string;
  readonly categoria: string;
  readonly precio: Precio;
  readonly ciudad: number | null;
  /** +0.06 = 6 % más caro que la referencia de la ciudad. */
  readonly diferencia: number | null;
}

/** Lo último que se supo de un producto en un puesto: lo que declaró el casero o midió el campo. */
export interface PrecioDelPuesto {
  readonly codigoProducto: string;
  readonly nombreProducto: string;
  readonly monto: number;
  readonly unidad: string;
  readonly precioPorUnidadBase: number;
  readonly unidadBase: UnidadBase;
  readonly fecha: string | null;
  readonly fuente: "vendedor" | "campo";
}

export interface PuestoEnFicha {
  readonly puesto: Puesto;
  readonly precios: readonly PrecioDelPuesto[];
  readonly ofertas: readonly Oferta[];
}

/** Todo lo que el sistema sabe de un lugar (C134). */
export interface FichaMercado {
  readonly mercado: Mercado;
  readonly padre: Mercado | null;
  readonly sectores: readonly Mercado[];
  readonly factorMercado: number;
  readonly precios: readonly PrecioDeProducto[];
  readonly puestos: readonly PuestoEnFicha[];
  readonly ofertas: readonly Oferta[];
  readonly observados: number;
  readonly estimados: number;
  readonly productosSinPrecio: number;
  readonly datoMasReciente: string | null;
}

export interface EntradaDirectorio {
  readonly mercado: Mercado;
  readonly puestos: number;
  readonly ofertas: number;
  readonly sectores: number;
}

/** "Puesto 14 · Verduras Doña Rosa", o solo "Puesto 14". */
export function tituloPuesto(numero: string, nombre?: string | null): string {
  return `Puesto ${numero}${nombre ? ` · ${nombre}` : ""}`;
}

/** Cuánto le queda a una oferta: "vence en 5 h", "vence mañana", "venció". */
export function textoVence(hasta: string, ahora: Date = new Date()): string {
  const horas = (Date.parse(hasta) - ahora.getTime()) / 3_600_000;
  if (horas <= 0) return "venció";
  if (horas < 1) return "vence en menos de una hora";
  if (horas < 20) return `vence en ${Math.round(horas)} h`;
  if (horas < 36) return "vence mañana";
  return `vence en ${Math.round(horas / 24)} días`;
}

/** Bs con coma decimal, como se escribe en Bolivia: 1.2 → "1,20". */
export function bs(monto: number): string {
  return monto.toFixed(2).replace(".", ",");
}

/**
 * La frase del candado: cuánto menos que el precio del sistema y qué precio
 * es ése. "Bs 2,35 menos por kilo que el precio estimado de Mercado Lanza (−16 %)".
 */
export function textoAhorroOferta(o: Oferta): string {
  const unidad = NOMBRE_UNIDAD_BASE[o.unidadBase].toLowerCase();
  return (
    `Bs ${bs(o.ahorroPorUnidad)} menos por ${unidad} que el precio ${o.procedenciaSistema} de ${o.nombreMercado} ` +
    `(−${Math.round(o.ahorroRelativo * 100)} %)`
  );
}

/** "6 % más caro que la ciudad", "3 % más barato", "igual que la ciudad". Null si no se puede comparar. */
export function textoDiferenciaCiudad(diferencia: number | null): string | null {
  if (diferencia === null) return null;
  const pct = Math.round(Math.abs(diferencia) * 100);
  if (pct === 0) return "igual que la ciudad";
  return `${pct} % más ${diferencia > 0 ? "caro" : "barato"} que la ciudad`;
}

/** Lo que se ahorra en un renglón de la lista si se compra en oferta. */
export interface OfertaParaLista {
  readonly oferta: Oferta;
  /** Cuánto del producto pide la lista, en unidad base (2 arrobas = 23 kg). */
  readonly cantidadBase: number;
  readonly ahorro: number;
}

/**
 * Las ofertas que tocan una lista (F4): por cada producto de la lista, la
 * oferta vigente que más ahorra frente al sistema. Ordenadas por cuánto se
 * ahorra en la cantidad que la persona pidió.
 */
export function ofertasParaLista(
  items: readonly ItemLista[],
  productos: readonly Producto[],
  ofertas: readonly Oferta[],
): OfertaParaLista[] {
  const salida: OfertaParaLista[] = [];
  for (const item of items) {
    const producto = productos.find((p) => p.codigo === item.codigoProducto);
    const candidatas = ofertas.filter((o) => o.codigoProducto === item.codigoProducto);
    if (!producto || candidatas.length === 0) continue;
    const mejor = candidatas.reduce((a, b) => (b.ahorroPorUnidad > a.ahorroPorUnidad ? b : a));
    const cantidadBase = enUnidadBase(item, producto);
    salida.push({ oferta: mejor, cantidadBase, ahorro: Math.round(mejor.ahorroPorUnidad * cantidadBase * 100) / 100 });
  }
  return salida.sort((a, b) => b.ahorro - a.ahorro);
}

/** Sin tildes ni mayúsculas, para buscar como escribe la gente. */
export function sinTildes(texto: string): string {
  return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

/**
 * El directorio filtrado: por texto (nombre, zona o macrodistrito) y por
 * tipo. Primero los que tienen ofertas, después por nombre. Los sectores
 * no se listan sueltos: se entra por su mercado.
 */
// --- caseras con puesto fijo, registradas en el mercado (C144) ---------------

/** Las caseras registradas en su puesto entran con su celular: por dentro, <celular>@caseras.preciojusto.bo. */
export const DOMINIO_CASERAS = "caseras.preciojusto.bo";

/** "+591 712-34567" → "71234567". Null si no es un celular de Bolivia (8 dígitos, empieza en 6 o 7). */
export function celularBoliviano(texto: string): string | null {
  let digitos = (texto ?? "").replace(/[\s\-().]/g, "");
  if (digitos.startsWith("+591")) digitos = digitos.slice(4);
  else if (digitos.startsWith("591") && digitos.length === 11) digitos = digitos.slice(3);
  return /^[67]\d{7}$/.test(digitos) ? digitos : null;
}

/** Se entra con el correo o, si es una casera, con su celular. */
export function identificadorDeIngreso(texto: string): string {
  const celular = celularBoliviano(texto);
  return celular ? `${celular}@${DOMINIO_CASERAS}` : texto.trim();
}

export interface NuevaCasera {
  readonly nombre: string;
  readonly celular: string;
  readonly codigoMercado: string;
  readonly numero: string;
  readonly nombrePuesto: string;
  readonly rubros: readonly string[];
  readonly referencia: string;
}

export interface CaseraRegistrada {
  readonly idUsuario: number;
  readonly nombre: string;
  readonly celular: string;
  readonly codigoMercado: string;
  readonly numero: string;
  /** Se muestra una sola vez, para anotársela a la casera. */
  readonly claveTemporal: string;
}

/** El precio de la ciudad de un producto, al consumidor y por mayor (C144). */
export interface PrecioReferencial {
  readonly producto: Producto;
  readonly consumidor: Precio | null;
  readonly mayorista: Precio | null;
}

/** Cuántos lugares hay y en cuántos ya hay caseras registradas (C144). */
export interface PanoramaMercados {
  /** Mercados de consumidor final, sin contar sus sectores. */
  readonly mercados: number;
  readonly distribuidores: number;
  readonly mayoristas: number;
  /** Lugares con al menos un puesto registrado: los que entran al piloto. */
  readonly conCaseras: number;
  readonly puestos: number;
  readonly ofertas: number;
  /** Por macrodistrito: cuántos mercados hay y en cuántos ya hay caseras. */
  readonly porMacrodistrito: readonly { nombre: string; mercados: number; conCaseras: number }[];
}

export function panoramaDeMercados(entradas: readonly EntradaDirectorio[]): PanoramaMercados {
  const lugares = entradas.filter((e) => !e.mercado.codigoPadre);
  const porMacro = new Map<string, { nombre: string; mercados: number; conCaseras: number }>();
  for (const e of lugares.filter((x) => x.mercado.tipo === "mercado")) {
    const nombre = e.mercado.macrodistrito || e.mercado.zona || "Sin macrodistrito";
    const fila = porMacro.get(nombre) ?? { nombre, mercados: 0, conCaseras: 0 };
    fila.mercados++;
    if (e.puestos > 0) fila.conCaseras++;
    porMacro.set(nombre, fila);
  }
  return {
    mercados: lugares.filter((e) => e.mercado.tipo === "mercado").length,
    distribuidores: lugares.filter((e) => e.mercado.tipo === "distribuidor").length,
    mayoristas: lugares.filter((e) => e.mercado.tipo === "mayorista").length,
    conCaseras: lugares.filter((e) => e.puestos > 0).length,
    // Los puestos y ofertas de los sectores cuentan para su mercado.
    puestos: entradas.reduce((s, e) => s + e.puestos, 0),
    ofertas: entradas.reduce((s, e) => s + e.ofertas, 0),
    porMacrodistrito: [...porMacro.values()].sort((a, b) => b.mercados - a.mercados || a.nombre.localeCompare(b.nombre)),
  };
}

export function filtrarDirectorio(
  entradas: readonly EntradaDirectorio[],
  texto: string,
  tipo: TipoPuntoVenta | "todos" = "todos",
): EntradaDirectorio[] {
  const buscado = sinTildes(texto.trim());
  return entradas
    .filter((e) => !e.mercado.codigoPadre)
    .filter((e) => tipo === "todos" || e.mercado.tipo === tipo)
    .filter(
      (e) =>
        !buscado ||
        [e.mercado.nombre, e.mercado.zona, e.mercado.macrodistrito].some((t) => sinTildes(t).includes(buscado)),
    )
    .sort((a, b) => Number(b.ofertas > 0) - Number(a.ofertas > 0) || a.mercado.nombre.localeCompare(b.mercado.nombre));
}

export function nombreCategoria(codigo: string): string {
  return CATEGORIAS.find((c) => c.codigo === codigo)?.nombre ?? codigo;
}

// --- qué medir primero y cuánto se mueve cada precio (A4230, A5020) -------------

/** Cuánto se movió el precio de la ciudad de un mes a otro. */
export interface VariacionDeProducto {
  readonly producto: Producto;
  /** Cambio mensual típico: 0.04 = suele moverse 4 % de un mes al siguiente. */
  readonly cambioMensual: number;
  readonly mayorSubida: number;
  readonly mayorBajada: number;
  readonly meses: number;
  readonly nivel: NivelPrecio;
}

export interface PrioridadDeProducto {
  readonly producto: Producto;
  readonly puntaje: number;
  readonly lugaresSinDato: number;
  readonly lugaresConDatoViejo: number;
  readonly lugaresAlDia: number;
  readonly cambioMensual: number | null;
  readonly anchoRelativo: number | null;
  readonly motivos: readonly string[];
}

export interface LugarPorVisitar {
  readonly mercado: Mercado;
  readonly productosAlDia: number;
  readonly productosTotal: number;
}

/** Recolección adaptativa: qué medir primero y dónde, en vez de medir todo por igual. */
export interface PlanDeVerificacion {
  readonly fecha: string;
  readonly productos: readonly PrioridadDeProducto[];
  readonly lugares: readonly LugarPorVisitar[];
  readonly variaciones: readonly VariacionDeProducto[];
}

/**
 * Lugares con exactamente el mismo precio, juntos. Cuando todo sale del
 * mismo boletín de la ciudad, 88 tarjetas iguales no dicen nada que una
 * sola no diga: se muestra una vez, con los nombres. Lo observado no se
 * junta nunca: cada medición en un lugar merece su propia tarjeta.
 */
export interface GrupoDePrecio {
  readonly clave: string;
  readonly items: readonly PrecioEnMercado[];
}

export function agruparPorPrecio(items: readonly PrecioEnMercado[]): GrupoDePrecio[] {
  const grupos: GrupoDePrecio[] = [];
  const porClave = new Map<string, PrecioEnMercado[]>();
  for (const item of items) {
    const { precio, mercado } = item;
    if (precio.procedencia === "observado") {
      grupos.push({ clave: mercado.codigo, items: [item] });
      continue;
    }
    const clave = [
      publicaRango(mercado.tipo) ? "rango" : "unico",
      precio.unidad,
      precio.rango.minimo.toFixed(2),
      precio.rango.maximo.toFixed(2),
      precio.confianza,
      esPrecioViejo(precio),
    ].join("|");
    const existente = porClave.get(clave);
    if (existente) {
      existente.push(item);
    } else {
      const nuevo = [item];
      porClave.set(clave, nuevo);
      grupos.push({ clave, items: nuevo });
    }
  }
  return grupos;
}

// --- inventario del puesto y la ventana del mapa (C137) -------------------------

/** Si al casero le queda: "hay", "poco" o "se acabó". Se cambia en un toque desde el celular. */
export type Disponibilidad = "hay" | "poco" | "agotado";

export const DISPONIBILIDADES: readonly { valor: Disponibilidad; texto: string }[] = [
  { valor: "hay", texto: "Hay" },
  { valor: "poco", texto: "Queda poco" },
  { valor: "agotado", texto: "Se acabó" },
];

export function textoDisponibilidad(d: Disponibilidad): string {
  return DISPONIBILIDADES.find((x) => x.valor === d)?.texto ?? d;
}

export interface ArticuloInventario {
  readonly codigoProducto: string;
  readonly nombreProducto: string;
  readonly categoria: string;
  readonly monto: number;
  readonly presentacion: string;
  readonly precioPorUnidadBase: number;
  readonly unidadBase: UnidadBase;
  readonly disponibilidad: Disponibilidad;
  readonly actualizadoEn: string | null;
  /** C148: cuánto le queda, en la misma presentación del precio (12 arrobas). null: no lo lleva. */
  readonly cantidad: number | null;
  /** Desde cuánto avisar que queda poco. */
  readonly minimo: number | null;
}

/** Con la cantidad a la vista el estado sale solo: 0 se acabó, hasta el mínimo queda poco. */
export function disponibilidadPara(cantidad: number, minimo: number | null): Disponibilidad {
  if (cantidad <= 0) return "agotado";
  if (minimo !== null && cantidad <= minimo) return "poco";
  return "hay";
}

/** "12 arrobas", "1 kilo", "2,5 kilos". */
export function textoCantidad(cantidad: number, presentacion: string): string {
  const n = Number.isInteger(cantidad) ? String(cantidad) : cantidad.toFixed(1).replace(".", ",");
  const p = presentacion.toLowerCase();
  const plural = cantidad === 1 || p.endsWith("s") ? p : p + (/[aeiou]$/.test(p) ? "s" : "es");
  return n + " " + plural;
}

/** Qué tan lleno está, de 0 a 1, para la barrita: seis veces el aviso se toma como "lleno". */
export function nivelExistencia(a: Pick<ArticuloInventario, "cantidad" | "minimo">): number | null {
  if (a.cantidad === null) return null;
  const lleno = Math.max((a.minimo ?? 5) * 6, 1);
  return Math.max(0, Math.min(1, a.cantidad / lleno));
}

export interface SugerenciaPrecio {
  readonly tipo: "bajar" | "subir" | "en_linea" | "sin_referencia";
  readonly texto: string;
  readonly precioSugerido: number | null;
  readonly precioMercado: number | null;
  readonly diferencia: number | null;
}

export interface RenglonReporte {
  readonly articulo: ArticuloInventario;
  readonly sugerencia: SugerenciaPrecio;
  readonly alertas: readonly string[];
}

/** C148: lo que la casera tiene que revisar hoy y una sugerencia de precio por producto. */
export interface ReporteInventario {
  readonly renglones: readonly RenglonReporte[];
  readonly productos: number;
  readonly conCantidad: number;
  readonly valorTotal: number;
  readonly agotados: number;
  readonly quedaPoco: number;
  readonly paraRevisarPrecio: number;
  readonly sinActualizar: number;
  readonly consejos: readonly string[];
}

// Un dibujito por producto: se reconoce de un vistazo, sin leer.
const ICONO_PRODUCTO: readonly [RegExp, string][] = [
  [/papa|yuca|oca/, "\u{1F954}"], [/tomate/, "\u{1F345}"], [/cebolla/, "\u{1F9C5}"], [/zanahoria/, "\u{1F955}"],
  [/locoto|aji/, "\u{1F336}\uFE0F"], [/choclo|maiz/, "\u{1F33D}"], [/haba|arveja|vainita|frejol/, "\u{1FADB}"],
  [/pimenton/, "\u{1FAD1}"], [/zapallo/, "\u{1F383}"], [/lechuga|acelga|espinaca|perejil/, "\u{1F96C}"],
  [/ajo/, "\u{1F9C4}"], [/banana|platano|guineo/, "\u{1F34C}"], [/manzana/, "\u{1F34E}"],
  [/naranja|mandarina/, "\u{1F34A}"], [/limon/, "\u{1F34B}"], [/pina/, "\u{1F34D}"], [/papaya/, "\u{1F348}"],
  [/uva/, "\u{1F347}"], [/frutilla/, "\u{1F353}"], [/sandia/, "\u{1F349}"], [/durazno/, "\u{1F351}"],
  [/arroz/, "\u{1F35A}"], [/fideo/, "\u{1F35D}"], [/aceite|manteca/, "\u{1FAD9}"], [/azucar/, "\u{1F36C}"],
  [/harina|quinua|trigo/, "\u{1F33E}"], [/mani/, "\u{1F95C}"], [/leche/, "\u{1F95B}"], [/queso/, "\u{1F9C0}"],
  [/pollo/, "\u{1F357}"], [/res|carne|cerdo/, "\u{1F969}"], [/huevo/, "\u{1F95A}"],
  [/trucha|pejerrey|pacu|surubi|pescado|sabalo/, "\u{1F41F}"], [/pan/, "\u{1F35E}"],
];
const ICONO_CATEGORIA: Record<string, string> = {
  hortaliza: "\u{1F96C}", tuberculo: "\u{1F954}", fruta: "\u{1F34E}", carne: "\u{1F969}", pescado: "\u{1F41F}",
  lacteo: "\u{1F95B}", abarrote: "\u{1F6D2}",
};

export function iconoProducto(codigo: string, categoria = ""): string {
  const c = sinTildes(codigo);
  return ICONO_PRODUCTO.find(([r]) => r.test(c))?.[1] ?? ICONO_CATEGORIA[categoria] ?? "\u{1F9FA}";
}

export interface PuestoConInventario {
  readonly puesto: Puesto;
  /** Puede venir recortada: total dice cuántos tiene en realidad. */
  readonly articulos: readonly ArticuloInventario[];
  readonly total: number;
}

export interface PuestosDeMercado {
  readonly mercado: Mercado;
  readonly puestos: readonly PuestoConInventario[];
}

/** "Puesto 14 · Verduras Rosa", o solo el nombre si es el local de una distribuidora. */
export function nombreDelPuesto(p: Puesto): string {
  return p.esLocal ? p.nombre || "Local" : tituloPuesto(p.numero, p.nombre);
}

/** "Mercado Rodríguez · Puesto 14". */
export function dondeEsta(mercado: Mercado, p: Puesto): string {
  return p.esLocal ? mercado.nombre : `${mercado.nombre} · Puesto ${p.numero}`;
}
