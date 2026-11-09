import type { PrecioRepositorio } from "@/aplicacion/puertos";
import { enUnidadBase, type Coordenadas, type ItemLista, type Producto } from "@/dominio/modelo";
import {
  planificarCompra,
  type Necesidad,
  type PrecioEnLugar,
  type ResultadoPlan,
} from "@/dominio/servicio/planificarCompra";

/**
 * Pasaje del minibús en La Paz por tramo, en Bs: 3 dentro de la ciudad y 3,50
 * si el tramo entra o sale de la Zona Sur (Centro ↔ Sur). Son los valores con
 * que arranca la pantalla: la persona los cambia si paga otra cosa.
 */
export const PASAJE_POR_DEFECTO = 3;
export const PASAJE_ZONA_SUR = 3.5;

/**
 * Caso de uso (C144): dónde comprar la lista para gastar menos, contando el
 * pasaje. Pide el precio de cada producto en todos los lugares y deja la
 * cuenta a la regla del dominio.
 */
export class PlanificarCompra {
  constructor(private readonly precios: PrecioRepositorio) {}

  async ejecutar(
    items: readonly ItemLista[],
    productos: readonly Producto[],
    opciones: { pasaje: number; pasajeZonaSur?: number; origen: Coordenadas | null },
  ): Promise<ResultadoPlan> {
    if (!(opciones.pasaje >= 0) || !((opciones.pasajeZonaSur ?? 0) >= 0)) throw new Error("El pasaje tiene que ser un monto en Bs, 0 o más.");
    const necesidades: Necesidad[] = items.flatMap((item) => {
      const producto = productos.find((p) => p.codigo === item.codigoProducto);
      return producto
        ? [{ codigoProducto: producto.codigo, nombre: producto.nombre, cantidadBase: enUnidadBase(item, producto), unidad: producto.unidadBase }]
        : [];
    });
    const porProducto = await Promise.all(
      necesidades.map(async (n) => {
        const lista = await this.precios.compararMercados(n.codigoProducto).catch(() => []);
        const enLugares: PrecioEnLugar[] = lista.map((x) => ({
          mercado: x.mercado,
          precioUnidad: x.precio.rango.centro,
          procedencia: x.precio.procedencia,
        }));
        return [n.codigoProducto, enLugares] as const;
      }),
    );
    return planificarCompra(necesidades, new Map(porProducto), opciones);
  }
}
