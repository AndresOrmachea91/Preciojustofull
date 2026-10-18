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
