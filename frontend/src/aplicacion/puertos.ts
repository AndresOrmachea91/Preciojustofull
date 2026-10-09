/**
 * Puertos: lo que la aplicación necesita del mundo exterior.
 *
 * Son interfaces. Los adaptadores de infraestructura las implementan —el de
 * HTTP contra la API real, el de memoria con datos fijos— y la aplicación
 * no sabe cuál está usando.
 */
import type {
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
} from "@/dominio/modelo";

export interface PrecioRepositorio {
  compararMercados(codigoProducto: string, zona?: string): Promise<PrecioEnMercado[]>;
  precioEnMercado(codigoProducto: string, codigoMercado: string): Promise<Precio>;
  calcularCanasta(items: readonly ItemCanasta[], zona?: string): Promise<CostoCanasta[]>;
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
}

export interface SesionRepositorio {
  /** Devuelve el token y la cuenta; rechaza con un error legible si falla. */
  ingresar(correo: string, contrasena: string): Promise<{ token: string; usuario: Usuario }>;
  registrarse(cuenta: NuevaCuenta): Promise<Usuario>;
  /** La cuenta del token vigente; rechaza si el token ya no sirve. */
  yo(): Promise<Usuario>;
}

/** Dónde se guarda el token entre recargas. El navegador es un detalle. */
export interface AlmacenSesion {
  leer(): string | null;
  guardar(token: string): void;
  borrar(): void;
}

export interface AdministracionRepositorio {
  usuarios(): Promise<Usuario[]>;
  crearUsuario(cuenta: NuevaCuenta & { rol: Rol }): Promise<Usuario>;
  actualizarUsuario(
    id: number,
    cambios: { rol?: Rol; activo?: boolean; codigoPuntoVenta?: string | null },
  ): Promise<Usuario>;
  restablecerContrasena(id: number, contrasena: string): Promise<Usuario>;
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
