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
import { RecuperarContrasena } from "@/aplicacion/casosUso/cuentas/recuperarContrasena";
import { CercaDeMi } from "@/aplicacion/casosUso/publico/cercaDeMi";
import { VerHistorial } from "@/aplicacion/casosUso/publico/verHistorial";
import { VerMapa } from "@/aplicacion/casosUso/publico/verMapa";
import { VerConfiabilidad } from "@/aplicacion/casosUso/publico/verConfiabilidad";
import { OperarSistema } from "@/aplicacion/casosUso/administracion/operarSistema";
import { RevisarOfertas } from "@/aplicacion/casosUso/administracion/revisarOfertas";
import { ExplorarMercados } from "@/aplicacion/casosUso/publico/explorarMercados";
import { VerOfertas } from "@/aplicacion/casosUso/publico/verOfertas";
import type {
  AdministracionRepositorio,
  AlmacenSesion,
  AuditoriaRepositorio,
  CatalogoAdminRepositorio,
  CatalogoRepositorio,
  ConfiabilidadRepositorio,
  HistorialRepositorio,
  OperacionRepositorio,
  ListasRepositorio,
  MercadosRepositorio,
  OfertasRepositorio,
  OfertasVendedorRepositorio,
  RevisionOfertasRepositorio,
  RecuperacionRepositorio,
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
import { OperacionApi } from "@/infraestructura/http/OperacionApi";
import { MercadosApi } from "@/infraestructura/http/MercadosApi";
import { PreciosApi } from "@/infraestructura/http/PreciosApi";
import { UsuarioApi } from "@/infraestructura/http/UsuarioApi";
import { VendedorApi } from "@/infraestructura/http/VendedorApi";
import { CuentasMemoria } from "@/infraestructura/memoria/CuentasMemoria";
import { OperacionMemoria } from "@/infraestructura/memoria/OperacionMemoria";
import { MercadosMemoria } from "@/infraestructura/memoria/MercadosMemoria";
import { PreciosMemoria } from "@/infraestructura/memoria/PreciosMemoria";
import { ListasMemoria, PreciosVendedorMemoria } from "@/infraestructura/memoria/UsuarioMemoria";
import { UbicacionNavegador } from "@/infraestructura/ubicacion/ubicacionNavegador";

export interface Contenedor {
  readonly compararMercados: CompararMercados;
  readonly calcularCanasta: CalcularCanasta;
  readonly catalogo: ConsultarCatalogo;
  readonly verMapa: VerMapa;
  readonly verHistorial: VerHistorial;
  readonly cercaDeMi: CercaDeMi;
  readonly sesion: GestionarSesion;
  readonly recuperar: RecuperarContrasena;
  readonly administrar: Administrar;
  readonly administrarCatalogo: AdministrarCatalogo;
  readonly verAuditoria: VerAuditoria;
  readonly listas: ListasDeCompras;
  readonly reportarPrecio: ReportarPrecio;
  readonly miPuesto: MiPuesto;
  readonly verConfiabilidad: VerConfiabilidad;
  readonly operarSistema: OperarSistema;
  readonly mercados: ExplorarMercados;
  readonly ofertas: VerOfertas;
  readonly revisarOfertas: RevisarOfertas;
}

export function crearContenedor(origen?: string, almacen?: AlmacenSesion): Contenedor {
  const modo = origen ?? import.meta.env?.VITE_ORIGEN_DATOS ?? "memoria";

  let precios: PrecioRepositorio & HistorialRepositorio;
  let catalogo: CatalogoRepositorio;
  let cuentas: SesionRepositorio & AdministracionRepositorio & AuditoriaRepositorio & RecuperacionRepositorio;
  let catalogoAdmin: CatalogoAdminRepositorio;
  let reportes: ReporteRepositorio;
  let misReportes: MisReportesRepositorio;
  let listas: ListasRepositorio;
  let preciosVendedor: PreciosVendedorRepositorio;
  let operacion: ConfiabilidadRepositorio & OperacionRepositorio;
  let mercados: MercadosRepositorio & OfertasRepositorio & RevisionOfertasRepositorio;
  let ofertasVendedor: OfertasVendedorRepositorio;

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
    const vendedor = new VendedorApi(http);
    preciosVendedor = vendedor;
    ofertasVendedor = vendedor;
    operacion = new OperacionApi(http);
    mercados = new MercadosApi(http);
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
    operacion = new OperacionMemoria();
    const mercadosMemoria = new MercadosMemoria(almacen, memoria, memoria);
    mercados = mercadosMemoria;
    ofertasVendedor = mercadosMemoria;
  }

  return {
    compararMercados: new CompararMercados(precios),
    calcularCanasta: new CalcularCanasta(precios),
    catalogo: new ConsultarCatalogo(catalogo),
    verMapa: new VerMapa(catalogo, precios),
    verHistorial: new VerHistorial(precios),
    // El GPS es del navegador en los dos modos: no depende de dónde salen los precios.
    cercaDeMi: new CercaDeMi(new UbicacionNavegador()),
    sesion: new GestionarSesion(cuentas, almacen),
    recuperar: new RecuperarContrasena(cuentas),
    administrar: new Administrar(cuentas),
    administrarCatalogo: new AdministrarCatalogo(catalogo, catalogoAdmin),
    verAuditoria: new VerAuditoria(cuentas),
    listas: new ListasDeCompras(listas),
    reportarPrecio: new ReportarPrecio(reportes, misReportes),
    miPuesto: new MiPuesto(preciosVendedor, ofertasVendedor),
    verConfiabilidad: new VerConfiabilidad(operacion),
    operarSistema: new OperarSistema(operacion),
    mercados: new ExplorarMercados(mercados),
    ofertas: new VerOfertas(mercados),
    revisarOfertas: new RevisarOfertas(mercados),
  };
}
