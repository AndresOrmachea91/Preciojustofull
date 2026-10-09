/**
 * Listas de compras y precios del vendedor en memoria: el plan B de la demo
 * y el adaptador de las pruebas. Cada cosa queda a nombre de la cuenta de
 * la sesión, igual que en el backend.
 */
import type {
  AlmacenSesion,
  CatalogoRepositorio,
  ListasRepositorio,
  PrecioRepositorio,
  PreciosVendedorRepositorio,
} from "@/aplicacion/puertos";
import { enUnidadBase, type CostoCanasta, type ItemLista, type ListaCompras, type PrecioPublicado } from "@/dominio/modelo";
import { idDeSesion } from "@/infraestructura/memoria/CuentasMemoria";

function exigirSesion(almacen: AlmacenSesion): number {
  const id = idDeSesion(almacen);
  if (id === null) throw new Error("Sesión inválida o vencida. Vuelva a ingresar.");
  return id;
}

export class ListasMemoria implements ListasRepositorio {
  private readonly datos = new Map<number, ListaCompras & { idUsuario: number }>();
  private siguiente = 1;

  constructor(
    private readonly almacen: AlmacenSesion,
    private readonly catalogo: CatalogoRepositorio,
    private readonly precios: PrecioRepositorio,
  ) {}

  async listas(): Promise<ListaCompras[]> {
    const yo = exigirSesion(this.almacen);
    return [...this.datos.values()].filter((l) => l.idUsuario === yo).map(({ idUsuario: _, ...l }) => l);
  }

  async crearLista(nombre: string, items: readonly ItemLista[]): Promise<ListaCompras> {
    const lista = { id: this.siguiente++, nombre, items: [...items], idUsuario: exigirSesion(this.almacen) };
    this.datos.set(lista.id, lista);
    return { id: lista.id, nombre, items: lista.items };
  }

  async actualizarLista(id: number, nombre: string, items: readonly ItemLista[]): Promise<ListaCompras> {
    this.propia(id);
    const lista = { id, nombre, items: [...items], idUsuario: exigirSesion(this.almacen) };
    this.datos.set(id, lista);
    return { id, nombre, items: lista.items };
  }

  async eliminarLista(id: number): Promise<void> {
    this.propia(id);
    this.datos.delete(id);
  }

  async cotizarLista(id: number, zona?: string): Promise<CostoCanasta[]> {
    const lista = this.propia(id);
    const productos = await this.catalogo.productos();
    const items = lista.items.flatMap((i) => {
      const producto = productos.find((p) => p.codigo === i.codigoProducto);
      return producto ? [{ codigoProducto: i.codigoProducto, cantidad: enUnidadBase(i, producto) }] : [];
    });
    return this.precios.calcularCanasta(items, zona);
  }

  private propia(id: number): ListaCompras {
    const lista = this.datos.get(id);
    if (!lista || lista.idUsuario !== exigirSesion(this.almacen)) throw new Error(`No existe la lista ${id}`);
    return lista;
  }
}

export class PreciosVendedorMemoria implements PreciosVendedorRepositorio {
  private readonly publicados: (PrecioPublicado & { idVendedor: number })[] = [];

  constructor(
    private readonly almacen: AlmacenSesion,
    private readonly catalogo: CatalogoRepositorio,
  ) {}

  async misPrecios(): Promise<PrecioPublicado[]> {
    const yo = exigirSesion(this.almacen);
    const ultimos = new Map<string, PrecioPublicado>();
    for (const p of [...this.publicados].reverse()) {
      if (p.idVendedor === yo && !ultimos.has(p.codigoProducto)) ultimos.set(p.codigoProducto, p);
    }
    return [...ultimos.values()].sort((a, b) => a.nombreProducto.localeCompare(b.nombreProducto));
  }

  async publicarPrecio(entrada: { codigoProducto: string; monto: number; presentacion: string }): Promise<void> {
    const idVendedor = exigirSesion(this.almacen);
    const producto = (await this.catalogo.productos()).find((p) => p.codigo === entrada.codigoProducto);
    const presentacion = producto?.presentaciones.find((p) => p.codigo === entrada.presentacion);
    if (!producto || !presentacion) throw new Error("Ese producto no se vende en esa presentación");
    this.publicados.push({
      idVendedor,
      codigoProducto: producto.codigo,
      nombreProducto: producto.nombre,
      monto: entrada.monto,
      presentacion: presentacion.codigo,
      precioPorUnidadBase: entrada.monto / presentacion.factor,
      unidadBase: producto.unidadBase,
      publicadoEn: new Date().toISOString(),
    });
  }
}
