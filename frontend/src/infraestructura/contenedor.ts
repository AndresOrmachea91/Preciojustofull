/**
 * Raíz de composición.
 *
 * El ÚNICO lugar del frontend donde se decide qué adaptador concreto se
 * enchufa a cada puerto. Cambiar de datos en memoria a la API real es
 * cambiar una variable de entorno; ningún caso de uso ni componente se
 * entera.
 */
import { Administrar } from "@/aplicacion/casosUso/administrar";
import { CalcularCanasta } from "@/aplicacion/casosUso/calcularCanasta";
import { CompararMercados } from "@/aplicacion/casosUso/compararMercados";
import { ConsultarCatalogo } from "@/aplicacion/casosUso/consultarCatalogo";
import { GestionarSesion } from "@/aplicacion/casosUso/gestionarSesion";
import { VerMapa } from "@/aplicacion/casosUso/verMapa";
import type {
  AdministracionRepositorio,
  AlmacenSesion,
  CatalogoRepositorio,
  PrecioRepositorio,
  SesionRepositorio,
} from "@/aplicacion/puertos";
import { AlmacenSesionLocal, AlmacenSesionMemoria } from "@/infraestructura/almacen/almacenSesion";
import { ClienteHttp } from "@/infraestructura/http/clienteHttp";
import { CuentasApi } from "@/infraestructura/http/CuentasApi";
import { PreciosApi } from "@/infraestructura/http/PreciosApi";
import { CuentasMemoria } from "@/infraestructura/memoria/CuentasMemoria";
import { PreciosMemoria } from "@/infraestructura/memoria/PreciosMemoria";

export interface Contenedor {
  readonly compararMercados: CompararMercados;
  readonly calcularCanasta: CalcularCanasta;
  readonly catalogo: ConsultarCatalogo;
  readonly verMapa: VerMapa;
  readonly sesion: GestionarSesion;
  readonly administrar: Administrar;
}

export function crearContenedor(origen?: string, almacen?: AlmacenSesion): Contenedor {
  const modo = origen ?? import.meta.env?.VITE_ORIGEN_DATOS ?? "memoria";

  let precios: PrecioRepositorio;
  let catalogo: CatalogoRepositorio;
  let cuentas: SesionRepositorio & AdministracionRepositorio;

  if (modo === "http") {
    const almacenSesion = almacen ?? new AlmacenSesionLocal();
    // Sin VITE_API_URL se asume el MISMO origen: es el caso cuando el
    // backend sirve la interfaz construida.
    // "||" y no "??": una VITE_API_URL vacía también significa mismo origen.
    const http = new ClienteHttp(import.meta.env?.VITE_API_URL || "/api/v1", () => almacenSesion.leer());
    const api = new PreciosApi(http);
    precios = api;
    catalogo = api;
    cuentas = new CuentasApi(http);
    almacen = almacenSesion;
  } else {
    const memoria = new PreciosMemoria();
    precios = memoria;
    catalogo = memoria;
    // En memoria la sesión tampoco sobrevive a la recarga: es coherente
    // con unos datos que se reinician en cada carga.
    almacen = almacen ?? new AlmacenSesionMemoria();
    cuentas = new CuentasMemoria(almacen);
  }

  return {
    compararMercados: new CompararMercados(precios),
    calcularCanasta: new CalcularCanasta(precios),
    catalogo: new ConsultarCatalogo(catalogo),
    verMapa: new VerMapa(catalogo, precios),
    sesion: new GestionarSesion(cuentas, almacen),
    administrar: new Administrar(cuentas),
  };
}
