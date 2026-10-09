import type { Mercado, Producto } from "@/dominio/modelo";
import { PRESENTACIONES_POR_UNIDAD, ubicacionValida } from "@/dominio/modelo";
import type {
  CatalogoAdminRepositorio,
  CatalogoRepositorio,
  DatosProducto,
  DatosPuntoVenta,
} from "@/aplicacion/puertos";

/**
 * El administrador gestiona mercados, tiendas y productos. Las reglas de
 * verdad están en el backend; acá se avisa antes de enviar lo que ya se
 * sabe que va a fallar (ubicación fuera del área, presentación sin base).
 */
export class AdministrarCatalogo {
  constructor(
    private readonly catalogo: CatalogoRepositorio,
    private readonly admin: CatalogoAdminRepositorio,
  ) {}

  puntosVenta(): Promise<Mercado[]> {
    return this.catalogo.mercados();
  }

  productos(): Promise<Producto[]> {
    return this.catalogo.productos();
  }

  guardarPuntoVenta(codigo: string | null, datos: DatosPuntoVenta): Promise<Mercado> {
    if (!datos.nombre.trim()) return Promise.reject(new Error("Escriba el nombre del punto de venta"));
    if (!ubicacionValida(datos.latitud, datos.longitud)) {
      return Promise.reject(new Error("La ubicación tiene que estar dentro de La Paz o El Alto (marque el punto en el mapa)"));
    }
    return codigo ? this.admin.actualizarPuntoVenta(codigo, datos) : this.admin.crearPuntoVenta(datos);
  }

  eliminarPuntoVenta(codigo: string): Promise<void> {
    return this.admin.eliminarPuntoVenta(codigo);
  }

  guardarProducto(codigo: string | null, datos: DatosProducto): Promise<Producto> {
    if (!datos.nombre.trim()) return Promise.reject(new Error("Escriba el nombre del producto"));
    const base = PRESENTACIONES_POR_UNIDAD[datos.unidadBase].find((p) => p.factor === 1)!;
    if (datos.presentaciones.length && !datos.presentaciones.includes(base.codigo)) {
      return Promise.reject(new Error(`Incluya la presentación «${base.nombre}»: es en la que se publica el precio`));
    }
    return codigo ? this.admin.actualizarProducto(codigo, datos) : this.admin.crearProducto(datos);
  }

  eliminarProducto(codigo: string): Promise<void> {
    return this.admin.eliminarProducto(codigo);
  }
}
