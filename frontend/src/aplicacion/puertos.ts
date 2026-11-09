/**
 * Puertos: lo que la aplicación necesita del mundo exterior.
 *
 * Son interfaces. Los adaptadores de infraestructura las implementan —el de
 * HTTP contra la API real, el de memoria con datos fijos— y la aplicación
 * no sabe cuál está usando.
 */
import type {
  EntradaDirectorio,
  FichaMercado,
  MiOferta,
  Oferta,
  OfertaEnRevision,
  Puesto,
  ResultadoConfirmacion,
  EvaluacionEstimador,
  ResultadoImportacion,
  SaludSistema,
  Coordenadas,
  HistorialPrecio,
  Referencias,
  RegistroAuditado,
  CostoCanasta,
  ListaCompras,
  ItemLista,
  PrecioPublicado,
  TipoPuntoVenta,
  UnidadBase,
  EstadoReporte,
  ItemCanasta,
  Mercado,
  Precio,
  PrecioEnMercado,
  Producto,
  ReporteEnRevision,
  Rol,
  Usuario,
  PlanDeVerificacion,
  ArticuloInventario,
  Disponibilidad,
  PuestosDeMercado,
  PrecioReferencial,
  NuevaCasera,
  CaseraRegistrada,
} from "@/dominio/modelo";

export interface PrecioRepositorio {
  compararMercados(codigoProducto: string, zona?: string): Promise<PrecioEnMercado[]>;
  precioEnMercado(codigoProducto: string, codigoMercado: string): Promise<Precio>;
  calcularCanasta(items: readonly ItemCanasta[], zona?: string): Promise<CostoCanasta[]>;
}

/** Los precios referenciales de la ciudad (C144). */
export interface ReferenciasRepositorio {
  referencias(): Promise<PrecioReferencial[]>;
}

/** El precio de la ciudad mes a mes. Puerto aparte: no todo el que compara precios necesita historia. */
export interface HistorialRepositorio {
  historial(codigoProducto: string, meses?: number): Promise<HistorialPrecio>;
}

/** Dónde está la persona ahora. Lo da el GPS del navegador, con su permiso. */
export interface UbicacionRepositorio {
  actual(): Promise<Coordenadas>;
}

export interface CatalogoRepositorio {
  productos(): Promise<Producto[]>;
  mercados(zona?: string): Promise<Mercado[]>;
}

export interface ReporteRepositorio {
  reportar(entrada: {
    codigoProducto: string;
    codigoMercado: string;
    monto: number;
    unidad: string;
  }): Promise<void>;
}


export interface NuevaCuenta {
  correo: string;
  nombre: string;
  contrasena: string;
  /** Tiene un puesto o una distribuidora: la cuenta nace como vendedor (decisión 27). */
  quiereVender?: boolean;
}

export interface SesionRepositorio {
  /** Devuelve el token y la cuenta; rechaza con un error legible si falla. */
  ingresar(correo: string, contrasena: string): Promise<{ token: string; usuario: Usuario }>;
  registrarse(cuenta: NuevaCuenta): Promise<Usuario>;
  /** La cuenta del token vigente; rechaza si el token ya no sirve. */
  yo(): Promise<Usuario>;
}

/** Recuperar la contraseña con un enlace al correo. Aparte de la sesión: no hace falta estar dentro. */
export interface RecuperacionRepositorio {
  /** Siempre resuelve igual, exista o no la cuenta: no revela qué correos hay. */
  pedirEnlace(correo: string): Promise<void>;
  restablecerConEnlace(token: string, contrasena: string): Promise<void>;
}

/** Dónde se guarda el token entre recargas. El navegador es un detalle. */
export interface AlmacenSesion {
  leer(): string | null;
  guardar(token: string): void;
  borrar(): void;
}

export interface AdministracionRepositorio {
  /** Sin el argumento, solo las vigentes: lo eliminado no se lista. */
  usuarios(incluirEliminados?: boolean): Promise<Usuario[]>;
  /** Eliminado LÓGICO: la cuenta deja de existir para el sistema, su fila y su auditoría quedan. */
  eliminarUsuario(id: number): Promise<void>;
  crearUsuario(cuenta: NuevaCuenta & { rol: Rol }): Promise<Usuario>;
  actualizarUsuario(
    id: number,
    cambios: { rol?: Rol; activo?: boolean; codigoPuntoVenta?: string | null },
  ): Promise<Usuario>;
  restablecerContrasena(id: number, contrasena: string): Promise<Usuario>;
  /** C144: la casera queda con cuenta (entra con su celular) y su puesto, en un solo paso. */
  registrarCasera(casera: NuevaCasera): Promise<CaseraRegistrada>;
  reportes(estado: EstadoReporte | "todos"): Promise<ReporteEnRevision[]>;
  aprobarReporte(id: number): Promise<ReporteEnRevision>;
  rechazarReporte(id: number, motivo: string): Promise<ReporteEnRevision>;
}

export interface DatosPuntoVenta {
  nombre: string;
  tipo: TipoPuntoVenta;
  zona: string;
  macrodistrito: string;
  latitud: number | null;
  longitud: number | null;
  codigoPadre: string | null;
}

export interface DatosProducto {
  nombre: string;
  categoria: string;
  unidadBase: UnidadBase;
  /** Códigos de presentación (kilo, quintal...). Vacío = todas las compatibles. */
  presentaciones: string[];
  diasConservacion: number;
}

/** Lo que el administrador hace con el catálogo. Listar usa CatalogoRepositorio, el público. */
/** Lo que el administrador consulta para rendir cuentas: auditoría y catálogos. */
export interface AuditoriaRepositorio {
  tablasAuditadas(): Promise<string[]>;
  auditoria(tabla?: string, limite?: number): Promise<RegistroAuditado[]>;
  referencias(): Promise<Referencias>;
}

export interface CatalogoAdminRepositorio {
  crearPuntoVenta(datos: DatosPuntoVenta): Promise<Mercado>;
  actualizarPuntoVenta(codigo: string, datos: DatosPuntoVenta): Promise<Mercado>;
  eliminarPuntoVenta(codigo: string): Promise<void>;
  crearProducto(datos: DatosProducto): Promise<Producto>;
  actualizarProducto(codigo: string, datos: DatosProducto): Promise<Producto>;
  eliminarProducto(codigo: string): Promise<void>;
}

/** Lo que el USUARIO hace con su cuenta: sus reportes y sus listas. */
export interface MisReportesRepositorio {
  misReportes(): Promise<ReporteEnRevision[]>;
}

export interface ListasRepositorio {
  listas(): Promise<ListaCompras[]>;
  crearLista(nombre: string, items: readonly ItemLista[]): Promise<ListaCompras>;
  actualizarLista(id: number, nombre: string, items: readonly ItemLista[]): Promise<ListaCompras>;
  eliminarLista(id: number): Promise<void>;
  /** Cuánto cuesta la lista completa en cada punto de venta, de más conveniente a menos. */
  cotizarLista(id: number, zona?: string): Promise<CostoCanasta[]>;
}

/** Lo que el VENDEDOR hace con su puesto. */
export interface PreciosVendedorRepositorio {
  misPrecios(): Promise<PrecioPublicado[]>;
  publicarPrecio(entrada: { codigoProducto: string; monto: number; presentacion: string }): Promise<void>;
}

/** Cuánto se equivoca el estimado frente a lo medido (backtest). Es público. */
export interface ConfiabilidadRepositorio {
  evaluacion(): Promise<EvaluacionEstimador>;
}

/** Lo que el ADMINISTRADOR opera: la planilla de campo y la salud del sistema. */
export interface OperacionRepositorio {
  importarCampo(csv: string, archivo: string, soloRevisar: boolean): Promise<ResultadoImportacion>;
  salud(): Promise<SaludSistema>;
}

// --- mercados por dentro, puestos y ofertas (C133, C134) -------------------------

/** Entrar a un lugar: el directorio y la ficha de cada mercado. Público. */
export interface MercadosRepositorio {
  directorio(): Promise<EntradaDirectorio[]>;
  ficha(codigoMercado: string): Promise<FichaMercado>;
  /** Qué conviene medir primero y cuánto se mueve cada precio (A4230, A5020). */
  verificaciones(): Promise<PlanDeVerificacion>;
  /** Los puestos de un mercado con foto e inventario: la ventana del mapa (C137). */
  puestos(codigoMercado: string, filtro?: { producto?: string; articulos?: number }): Promise<PuestosDeMercado>;
}

/** Las ofertas vigentes (públicas) y el "¿Lo viste así?" de quien tiene sesión. */
export interface OfertasRepositorio {
  vigentes(filtro?: { mercado?: string; producto?: string }): Promise<Oferta[]>;
  confirmar(idOferta: number, laVioAsi: boolean): Promise<ResultadoConfirmacion>;
}

export interface DatosPuesto {
  numero: string;
  nombre: string;
  rubros: string[];
  referencia: string;
  /** El mercado lo elige el casero (decisión 26). Sin él, el que ya tenía. */
  codigoMercado?: string;
}

export interface DatosDistribuidora {
  nombre: string;
  zona: string;
  macrodistrito: string;
  latitud: number;
  longitud: number;
  rubros: string[];
  referencia: string;
}

export interface NuevoArticulo {
  codigoProducto: string;
  monto: number;
  presentacion: string;
  disponibilidad: Disponibilidad;
}

export interface NuevaOferta {
  codigoProducto: string;
  monto: number;
  presentacion: string;
  horas: number;
  nota: string;
}

/** C145: 2 o 3 productos en oferta bajo un nombre, que vencen juntos. */
export interface NuevoCombo {
  nombre: string;
  renglones: { codigoProducto: string; monto: number; presentacion: string }[];
  horas: number;
  nota: string;
}

/** Lo que el VENDEDOR hace con su puesto y sus ofertas. */
export interface OfertasVendedorRepositorio {
  miPuesto(): Promise<Puesto | null>;
  guardarMiPuesto(datos: DatosPuesto): Promise<Puesto>;
  registrarDistribuidora(datos: DatosDistribuidora): Promise<Puesto>;
  /** La foto como data URL, ya achicada en el celular. */
  ponerFoto(imagen: string): Promise<Puesto>;
  inventario(): Promise<ArticuloInventario[]>;
  guardarArticulo(articulo: NuevoArticulo): Promise<ArticuloInventario>;
  quitarArticulo(codigoProducto: string): Promise<void>;
  misOfertas(): Promise<MiOferta[]>;
  publicarOferta(oferta: NuevaOferta): Promise<void>;
  publicarCombo(combo: NuevoCombo): Promise<void>;
  retirarOferta(id: number): Promise<void>;
}

/** Las ofertas que los compradores desmintieron: las decide el administrador. */
export interface RevisionOfertasRepositorio {
  ofertasEnRevision(): Promise<OfertaEnRevision[]>;
  reactivarOferta(id: number): Promise<void>;
  retirarOfertaRevisada(id: number): Promise<void>;
}
