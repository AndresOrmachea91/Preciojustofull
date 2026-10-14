/**
 * Raíz de composición.
 *
 * El ÚNICO lugar del frontend donde se decide qué adaptador concreto se
 * enchufa a cada puerto. Cambiar de datos en memoria a la API real es
 * cambiar una variable de entorno; ningún caso de uso ni componente se
 * entera.
 */
import { Administrar } from "@/aplicacion/casosUso/administracion/administrarCuentas";
import { AdministrarCatalogo } from "@/aplicacion/casosUso/administracion/administrarCatalogo";
import { VerAuditoria } from "@/aplicacion/casosUso/administracion/verAuditoria";
import { ListasDeCompras } from "@/aplicacion/casosUso/usuario/listasCompras";
import { ReportarPrecio } from "@/aplicacion/casosUso/usuario/reportarPrecio";
import { MiPuesto } from "@/aplicacion/casosUso/vendedor/miPuesto";
import { CalcularCanasta } from "@/aplicacion/casosUso/publico/calcularCanasta";
import { CompararMercados } from "@/aplicacion/casosUso/publico/compararMercados";
import { ConsultarCatalogo } from "@/aplicacion/casosUso/publico/consultarCatalogo";
import { GestionarSesion } from "@/aplicacion/casosUso/cuentas/gestionarSesion";
import { VerHistorial } from "@/aplicacion/casosUso/publico/verHistorial";
import { VerMapa } from "@/aplicacion/casosUso/publico/verMapa";
import type {
  AdministracionRepositorio,
  AlmacenSesion,
  AuditoriaRepositorio,
  CatalogoAdminRepositorio,
  CatalogoRepositorio,
  HistorialRepositorio,
  ListasRepositorio,
  MisReportesRepositorio,
  PrecioRepositorio,
  PreciosVendedorRepositorio,
  ReporteRepositorio,
  SesionRepositorio,
} from "@/aplicacion/puertos";
import { AlmacenSesionLocal, AlmacenSesionMemoria } from "@/infraestructura/almacen/almacenSesion";
import { CatalogoAdminApi } from "@/infraestructura/http/CatalogoAdminApi";
import { ClienteHttp } from "@/infraestructura/http/clienteHttp";
import { CuentasApi } from "@/infraestructura/http/CuentasApi";
import { PreciosApi } from "@/infraestructura/http/PreciosApi";
import { UsuarioApi } from "@/infraestructura/http/UsuarioApi";
import { VendedorApi } from "@/infraestructura/http/VendedorApi";
import { CuentasMemoria } from "@/infraestructura/memoria/CuentasMemoria";
import { PreciosMemoria } from "@/infraestructura/memoria/PreciosMemoria";
import { ListasMemoria, PreciosVendedorMemoria } from "@/infraestructura/memoria/UsuarioMemoria";

export interface Contenedor {
  readonly compararMercados: CompararMercados;
  readonly calcularCanasta: CalcularCanasta;
  readonly catalogo: ConsultarCatalogo;
  readonly verMapa: VerMapa;
  readonly verHistorial: VerHistorial;
  readonly sesion: GestionarSesion;
  readonly administrar: Administrar;
  readonly administrarCatalogo: AdministrarCatalogo;
  readonly verAuditoria: VerAuditoria;
  readonly listas: ListasDeCompras;
  readonly reportarPrecio: ReportarPrecio;
  readonly miPuesto: MiPuesto;
}

export function crearContenedor(origen?: string, almacen?: AlmacenSesion): Contenedor {
  const modo = origen ?? import.meta.env?.VITE_ORIGEN_DATOS ?? "memoria";

  let precios: PrecioRepositorio & HistorialRepositorio;
  let catalogo: CatalogoRepositorio;
  let cuentas: SesionRepositorio & AdministracionRepositorio & AuditoriaRepositorio;
  let catalogoAdmin: CatalogoAdminRepositorio;
  let reportes: ReporteRepositorio;
  let misReportes: MisReportesRepositorio;
  let listas: ListasRepositorio;
  let preciosVendedor: PreciosVendedorRepositorio;

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
    catalogoAdmin = new CatalogoAdminApi(http);
    reportes = api;
    const usuario = new UsuarioApi(http);
    misReportes = usuario;
    listas = usuario;
    preciosVendedor = new VendedorApi(http);
    almacen = almacenSesion;
  } else {
    const memoria = new PreciosMemoria();
    precios = memoria;
    catalogo = memoria;
    catalogoAdmin = memoria;
    // En memoria la sesión tampoco sobrevive a la recarga: es coherente
    // con unos datos que se reinician en cada carga.
    almacen = almacen ?? new AlmacenSesionMemoria();
    const cuentasMemoria = new CuentasMemoria(almacen);
    cuentas = cuentasMemoria;
    reportes = cuentasMemoria;
    misReportes = cuentasMemoria;
    listas = new ListasMemoria(almacen, memoria, memoria);
    preciosVendedor = new PreciosVendedorMemoria(almacen, memoria);
  }

  return {
    compararMercados: new CompararMercados(precios),
    calcularCanasta: new CalcularCanasta(precios),
    catalogo: new ConsultarCatalogo(catalogo),
    verMapa: new VerMapa(catalogo, precios),
    verHistorial: new VerHistorial(precios),
    sesion: new GestionarSesion(cuentas, almacen),
    administrar: new Administrar(cuentas),
    administrarCatalogo: new AdministrarCatalogo(catalogo, catalogoAdmin),
    verAuditoria: new VerAuditoria(cuentas),
    listas: new ListasDeCompras(listas),
    reportarPrecio: new ReportarPrecio(reportes, misReportes),
    miPuesto: new MiPuesto(preciosVendedor),
  };
}
