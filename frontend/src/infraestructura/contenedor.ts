/**
 * Raíz de composición.
 *
 * El ÚNICO lugar del frontend donde se decide qué adaptador concreto se
 * enchufa a cada puerto. Cambiar de datos en memoria a la API real es
 * cambiar una variable de entorno; ningún caso de uso ni componente se
 * entera.
 */
import { CalcularCanasta } from "@/aplicacion/casosUso/calcularCanasta";
import { CompararMercados } from "@/aplicacion/casosUso/compararMercados";
import { ConsultarCatalogo } from "@/aplicacion/casosUso/consultarCatalogo";
import { VerMapa } from "@/aplicacion/casosUso/verMapa";
import type { CatalogoRepositorio, PrecioRepositorio } from "@/aplicacion/puertos";
import { ClienteHttp } from "@/infraestructura/http/clienteHttp";
import { PreciosApi } from "@/infraestructura/http/PreciosApi";
import { PreciosMemoria } from "@/infraestructura/memoria/PreciosMemoria";

export interface Contenedor {
  readonly compararMercados: CompararMercados;
  readonly calcularCanasta: CalcularCanasta;
  readonly catalogo: ConsultarCatalogo;
  readonly verMapa: VerMapa;
}

export function crearContenedor(origen?: string): Contenedor {
  const modo = origen ?? import.meta.env?.VITE_ORIGEN_DATOS ?? "memoria";

  let precios: PrecioRepositorio;
  let catalogo: CatalogoRepositorio;

  if (modo === "http") {
    const http = new ClienteHttp(
      import.meta.env?.VITE_API_URL ?? "http://localhost:8000/api/v1",
    );
    const api = new PreciosApi(http);
    precios = api;
    catalogo = api;
  } else {
    const memoria = new PreciosMemoria();
    precios = memoria;
    catalogo = memoria;
  }

  return {
    compararMercados: new CompararMercados(precios),
    calcularCanasta: new CalcularCanasta(precios),
    catalogo: new ConsultarCatalogo(catalogo),
    verMapa: new VerMapa(catalogo, precios),
  };
}

