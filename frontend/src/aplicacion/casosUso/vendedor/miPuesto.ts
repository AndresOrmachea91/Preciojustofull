import type {
  DatosPuesto,
  NuevaOferta,
  OfertasVendedorRepositorio,
  PreciosVendedorRepositorio,
} from "@/aplicacion/puertos";
import { DURACIONES_OFERTA, type MiOferta, type PrecioPublicado, type Puesto } from "@/dominio/modelo";

/** El vendedor publica los precios de su puesto, registra el puesto y maneja sus ofertas. */
export class MiPuesto {
  constructor(
    private readonly repositorio: PreciosVendedorRepositorio,
    private readonly ofertas: OfertasVendedorRepositorio,
  ) {}

  misPrecios(): Promise<PrecioPublicado[]> {
    return this.repositorio.misPrecios();
  }

  publicar(entrada: { codigoProducto: string; monto: number; presentacion: string }): Promise<void> {
    if (!entrada.codigoProducto) return Promise.reject(new Error("Elija el producto"));
    if (!(entrada.monto > 0)) return Promise.reject(new Error("El precio tiene que ser mayor a cero"));
    return this.repositorio.publicarPrecio(entrada);
  }

  puesto(): Promise<Puesto | null> {
    return this.ofertas.miPuesto();
  }

  guardarPuesto(datos: DatosPuesto): Promise<Puesto> {
    if (!datos.numero.trim()) return Promise.reject(new Error("Escriba el número del puesto"));
    return this.ofertas.guardarMiPuesto({ ...datos, numero: datos.numero.trim(), nombre: datos.nombre.trim() });
  }

  misOfertas(): Promise<MiOferta[]> {
    return this.ofertas.misOfertas();
  }

  /** Los candados que se pueden ver antes de enviar; el resto (más barata que el sistema) lo decide la API. */
  publicarOferta(oferta: NuevaOferta): Promise<void> {
    if (!oferta.codigoProducto) return Promise.reject(new Error("Elija el producto"));
    if (!(oferta.monto > 0)) return Promise.reject(new Error("El precio tiene que ser mayor a cero"));
    if (!(DURACIONES_OFERTA as readonly number[]).includes(oferta.horas)) {
      return Promise.reject(new Error("La oferta dura 24, 48 o 72 horas"));
    }
    if (oferta.nota.length > 80) return Promise.reject(new Error("La nota es de 80 letras como mucho"));
    return this.ofertas.publicarOferta(oferta);
  }

  retirarOferta(id: number): Promise<void> {
    return this.ofertas.retirarOferta(id);
  }
}
