import type {
  DatosDistribuidora,
  DatosPuesto,
  NuevaOferta,
  NuevoCombo,
  NuevoArticulo,
  OfertasVendedorRepositorio,
  PreciosVendedorRepositorio,
} from "@/aplicacion/puertos";
import {
  DURACIONES_OFERTA, PRODUCTOS_POR_COMBO,
  type ArticuloInventario,
  type MiOferta,
  type PrecioPublicado,
  type Puesto,
} from "@/dominio/modelo";

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

  registrarDistribuidora(datos: DatosDistribuidora): Promise<Puesto> {
    if (!datos.nombre.trim()) return Promise.reject(new Error("Escriba el nombre de la distribuidora"));
    if (!Number.isFinite(datos.latitud) || !Number.isFinite(datos.longitud)) {
      return Promise.reject(new Error("Marque en el mapa dónde está la distribuidora"));
    }
    return this.ofertas.registrarDistribuidora({ ...datos, nombre: datos.nombre.trim() });
  }

  ponerFoto(imagen: string): Promise<Puesto> {
    if (!imagen.startsWith("data:image/")) return Promise.reject(new Error("Elija una foto"));
    return this.ofertas.ponerFoto(imagen);
  }

  inventario(): Promise<ArticuloInventario[]> {
    return this.ofertas.inventario();
  }

  guardarArticulo(articulo: NuevoArticulo): Promise<ArticuloInventario> {
    if (!articulo.codigoProducto) return Promise.reject(new Error("Elija el producto"));
    if (!(articulo.monto > 0)) return Promise.reject(new Error("El precio tiene que ser mayor a cero"));
    return this.ofertas.guardarArticulo(articulo);
  }

  quitarArticulo(codigoProducto: string): Promise<void> {
    return this.ofertas.quitarArticulo(codigoProducto);
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

  /** C145: un combo. Cada producto pasa el mismo candado que una oferta suelta (lo revisa el backend). */
  publicarCombo(combo: NuevoCombo): Promise<void> {
    if (!combo.nombre.trim()) return Promise.reject(new Error("Póngale un nombre al combo: «Combo sopa», «Para el almuerzo»…"));
    const renglones = combo.renglones.filter((r) => r.codigoProducto);
    if (renglones.length < PRODUCTOS_POR_COMBO.minimo || renglones.length > PRODUCTOS_POR_COMBO.maximo) {
      return Promise.reject(new Error("Un combo junta de 2 a 3 productos"));
    }
    if (new Set(renglones.map((r) => r.codigoProducto)).size !== renglones.length) {
      return Promise.reject(new Error("Un producto aparece dos veces en el combo"));
    }
    if (renglones.some((r) => !(r.monto > 0))) return Promise.reject(new Error("Cada precio tiene que ser mayor a cero"));
    if (!(DURACIONES_OFERTA as readonly number[]).includes(combo.horas)) {
      return Promise.reject(new Error("La oferta dura 24, 48 o 72 horas"));
    }
    return this.ofertas.publicarCombo({ ...combo, nombre: combo.nombre.trim(), renglones });
  }

  retirarOferta(id: number): Promise<void> {
    return this.ofertas.retirarOferta(id);
  }
}
