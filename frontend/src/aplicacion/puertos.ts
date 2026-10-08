/**
 * Puertos: lo que la aplicación necesita del mundo exterior.
 *
 * Son interfaces. Los adaptadores de infraestructura las implementan —el de
 * HTTP contra la API real, el de memoria con datos fijos— y la aplicación
 * no sabe cuál está usando.
 */
import type {
  CostoCanasta,
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
