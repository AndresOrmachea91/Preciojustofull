import type { CostoCanasta, ItemLista, ListaCompras } from "@/dominio/modelo";
import type { ListasRepositorio } from "@/aplicacion/puertos";
import { resumirCanasta, type ResultadoCanasta } from "@/aplicacion/casosUso/publico/calcularCanasta";

/**
 * Una cotización de lista. Lo de consumidor final y lo mayorista van
 * separados: el mayorista vende por bulto para revender, a otro nivel de la
 * cadena, y su precio no compite con el de un puesto de mercado.
 */
export interface CotizacionLista {
  readonly minoristas: ResultadoCanasta;
  readonly mayoristas: readonly CostoCanasta[];
}

/**
 * Las listas de compras del usuario. Las reglas de verdad están en el
 * backend; acá se avisa antes de enviar lo que ya se sabe que va a fallar.
 */
export class ListasDeCompras {
  constructor(private readonly repositorio: ListasRepositorio) {}

  listas(): Promise<ListaCompras[]> {
    return this.repositorio.listas();
  }

  guardar(id: number | null, nombre: string, items: readonly ItemLista[]): Promise<ListaCompras> {
    if (!nombre.trim()) return Promise.reject(new Error("Póngale un nombre a la lista"));
    if (items.some((i) => !(i.cantidad > 0))) {
      return Promise.reject(new Error("Cada producto necesita una cantidad mayor a cero"));
    }
    const codigos = items.map((i) => i.codigoProducto);
    if (new Set(codigos).size !== codigos.length) {
      return Promise.reject(new Error("Cada producto puede aparecer una sola vez en la lista"));
    }
    return id === null
      ? this.repositorio.crearLista(nombre.trim(), items)
      : this.repositorio.actualizarLista(id, nombre.trim(), items);
  }

  eliminar(id: number): Promise<void> {
    return this.repositorio.eliminarLista(id);
  }

  async cotizar(id: number, zona?: string): Promise<CotizacionLista> {
    const costos = await this.repositorio.cotizarLista(id, zona);
    return {
      minoristas: resumirCanasta(costos.filter((c) => c.nivelPrecio === "minorista")),
      mayoristas: costos.filter((c) => c.nivelPrecio === "mayorista"),
    };
  }
}
