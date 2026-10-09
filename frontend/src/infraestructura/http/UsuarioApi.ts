/**
 * Adaptador HTTP de lo que hace el USUARIO con su cuenta: sus reportes
 * (/api/v1/reportes/mios) y sus listas de compras (/api/v1/listas).
 */
import type { ListasRepositorio, MisReportesRepositorio } from "@/aplicacion/puertos";
import type { CostoCanasta, ItemLista, ListaCompras, ReporteEnRevision } from "@/dominio/modelo";
import type { ClienteHttp } from "@/infraestructura/http/clienteHttp";
import { aReporte, type ReporteDto } from "@/infraestructura/http/CuentasApi";
import { aCostoCanasta, type CanastaDto } from "@/infraestructura/http/PreciosApi";

interface ListaDto {
  id: number;
  nombre: string;
  items: { codigo_producto: string; cantidad: number; presentacion: string }[];
}

function aLista(d: ListaDto): ListaCompras {
  return {
    id: d.id,
    nombre: d.nombre,
    items: d.items.map((i) => ({ codigoProducto: i.codigo_producto, cantidad: i.cantidad, presentacion: i.presentacion })),
  };
}

function listaADto(nombre: string, items: readonly ItemLista[]) {
  return {
    nombre,
    items: items.map((i) => ({ codigo_producto: i.codigoProducto, cantidad: i.cantidad, presentacion: i.presentacion })),
  };
}

export class UsuarioApi implements MisReportesRepositorio, ListasRepositorio {
  constructor(private readonly http: ClienteHttp) {}

  async misReportes(): Promise<ReporteEnRevision[]> {
    return (await this.http.get<ReporteDto[]>("/reportes/mios")).map(aReporte);
  }

  async listas(): Promise<ListaCompras[]> {
    return (await this.http.get<ListaDto[]>("/listas")).map(aLista);
  }

  async crearLista(nombre: string, items: readonly ItemLista[]): Promise<ListaCompras> {
    return aLista(await this.http.post<ListaDto>("/listas", listaADto(nombre, items)));
  }

  async actualizarLista(id: number, nombre: string, items: readonly ItemLista[]): Promise<ListaCompras> {
    return aLista(await this.http.put<ListaDto>(`/listas/${id}`, listaADto(nombre, items)));
  }

  eliminarLista(id: number): Promise<void> {
    return this.http.delete(`/listas/${id}`);
  }

  async cotizarLista(id: number, zona?: string): Promise<CostoCanasta[]> {
    return (await this.http.get<CanastaDto[]>(`/listas/${id}/cotizar`, { zona })).map(aCostoCanasta);
  }
}
