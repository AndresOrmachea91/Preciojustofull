/**
 * Adaptador en memoria de los mismos puertos.
 *
 * Permite desarrollar la interfaz y correr las pruebas sin backend. No es
 * un simulacro improvisado: implementa exactamente el mismo contrato que
 * el adaptador HTTP, y por eso se pueden intercambiar sin tocar nada más.
 *
 * Los datos imitan la situación real de hoy: un puñado de mercados con
 * mediciones propias, el resto estimado desde la ciudad, y un mayorista
 * cuyo precio no compite con los de consumidor final.
 */
import type {
  CostoCanasta,
  HistorialPrecio,
  ItemCanasta,
  Mercado,
  Precio,
  PrecioEnMercado,
  Producto,
  PrecioReferencial,
} from "@/dominio/modelo";
import { PRESENTACIONES_POR_UNIDAD, ubicacionValida } from "@/dominio/modelo";
import type {
  CatalogoAdminRepositorio,
  CatalogoRepositorio,
  DatosProducto,
  DatosPuntoVenta,
  HistorialRepositorio,
  PrecioRepositorio,
  ReferenciasRepositorio,
} from "@/aplicacion/puertos";

const MERCADOS: Mercado[] = [
  { codigo: "rodriguez", nombre: "Mercado Rodríguez", tipo: "mercado", zona: "Cotahuma", macrodistrito: "Cotahuma", codigoPadre: null, nivelPrecio: "minorista", latitud: -16.500192, longitud: -68.138992 },
  { codigo: "rodriguez_cubierto", nombre: "Mercado Rodríguez - sector cubierto", tipo: "mercado", zona: "Cotahuma", macrodistrito: "Cotahuma", codigoPadre: "rodriguez", nivelPrecio: "minorista", latitud: -16.500676, longitud: -68.139072 },
  { codigo: "lanza", nombre: "Mercado Lanza", tipo: "mercado", zona: "Centro", macrodistrito: "Centro", codigoPadre: null, nivelPrecio: "minorista", latitud: -16.4957, longitud: -68.136 },
  { codigo: "villafatima", nombre: "Mercado Villa Fátima", tipo: "mercado", zona: "Periférica", macrodistrito: "Periférica", codigoPadre: null, nivelPrecio: "minorista", latitud: -16.4816, longitud: -68.1194 },
  { codigo: "mercado_sopocachi", nombre: "Mercado Sopocachi", tipo: "mercado", zona: "Cotahuma", macrodistrito: "Cotahuma", codigoPadre: null, nivelPrecio: "minorista", latitud: -16.51, longitud: -68.13 },
  { codigo: "mercado_san_pedro", nombre: "Mercado San Pedro", tipo: "mercado", zona: "Cotahuma", macrodistrito: "Cotahuma", codigoPadre: null, nivelPrecio: "minorista", latitud: -16.501668, longitud: -68.135871 },
  { codigo: "distribuidora_central", nombre: "Distribuidora Central", tipo: "distribuidor", zona: "Centro", macrodistrito: "Centro", codigoPadre: null, nivelPrecio: "mayorista", latitud: -16.493233, longitud: -68.14427 },
];

const PRODUCTOS: Producto[] = [
  { codigo: "tomate", nombre: "Tomate", categoria: "hortaliza", esPerecedero: true, unidadBase: "kg", diasConservacion: 5, presentaciones: PRESENTACIONES_POR_UNIDAD.kg },
  { codigo: "papa", nombre: "Papa holandesa", categoria: "tuberculo", esPerecedero: false, unidadBase: "kg", diasConservacion: 60, presentaciones: PRESENTACIONES_POR_UNIDAD.kg },
  { codigo: "arroz", nombre: "Arroz de primera", categoria: "abarrote", esPerecedero: false, unidadBase: "kg", diasConservacion: 365, presentaciones: PRESENTACIONES_POR_UNIDAD.kg },
];

interface Fila {
  producto: string;
  mercado: string;
  centro: number;
  confianza: Precio["confianza"];
  procedencia: Precio["procedencia"];
  observaciones: number;
  fecha: string | null;
}

const PRECIOS: Fila[] = [
  { producto: "tomate", mercado: "villafatima", centro: 13.04, confianza: "medio", procedencia: "observado", observaciones: 1, fecha: "2026-09-10" },
  { producto: "tomate", mercado: "rodriguez", centro: 14.35, confianza: "verificado", procedencia: "observado", observaciones: 2, fecha: "2026-09-14" },
  { producto: "tomate", mercado: "lanza", centro: 16.3, confianza: "bajo", procedencia: "observado", observaciones: 1, fecha: null },
  { producto: "tomate", mercado: "mercado_sopocachi", centro: 19.57, confianza: "verificado", procedencia: "observado", observaciones: 1, fecha: "2026-09-12" },
  { producto: "tomate", mercado: "mercado_san_pedro", centro: 17.8, confianza: "medio", procedencia: "estimado", observaciones: 104, fecha: null },
  { producto: "tomate", mercado: "distribuidora_central", centro: 5.41, confianza: "medio", procedencia: "estimado", observaciones: 103, fecha: "2026-07-30" },
  { producto: "papa", mercado: "villafatima", centro: 6.78, confianza: "verificado", procedencia: "observado", observaciones: 1, fecha: "2026-09-10" },
  { producto: "papa", mercado: "rodriguez", centro: 6.96, confianza: "alto", procedencia: "observado", observaciones: 1, fecha: "2026-09-14" },
  { producto: "papa", mercado: "lanza", centro: 7.39, confianza: "bajo", procedencia: "observado", observaciones: 1, fecha: null },
  { producto: "papa", mercado: "distribuidora_central", centro: 3.72, confianza: "medio", procedencia: "estimado", observaciones: 103, fecha: "2026-07-30" },
  { producto: "arroz", mercado: "rodriguez", centro: 8.2, confianza: "alto", procedencia: "observado", observaciones: 1, fecha: "2026-09-14" },
  { producto: "arroz", mercado: "lanza", centro: 8.6, confianza: "alto", procedencia: "observado", observaciones: 1, fecha: "2026-09-13" },
  { producto: "arroz", mercado: "mercado_sopocachi", centro: 10.5, confianza: "verificado", procedencia: "observado", observaciones: 1, fecha: "2026-09-12" },
  { producto: "arroz", mercado: "mercado_san_pedro", centro: 14.83, confianza: "medio", procedencia: "estimado", observaciones: 104, fecha: null },
  { producto: "arroz", mercado: "distribuidora_central", centro: 12.28, confianza: "medio", procedencia: "estimado", observaciones: 103, fecha: "2026-07-30" },
];

const VOZ_POR_CONFIANZA: Record<Precio["confianza"], string> = {
  verificado: "campo",
  alto: "vendedor",
  medio: "medios",
  bajo: "ciudadano",
};

// Los datos de ejemplo son de mediados de septiembre: su antigüedad se mide
// desde ese día, no desde hoy, para que el modo demo se vea igual siempre.
const HOY_DE_LOS_DATOS = Date.parse("2026-09-15T12:00:00");

function diasDesde(fecha: string): number {
  return Math.max(0, Math.floor((HOY_DE_LOS_DATOS - Date.parse(`${fecha}T12:00:00`)) / 86_400_000));
}

function aPrecio(f: Fila): Precio {
  return {
    codigoProducto: f.producto,
    codigoMercado: f.mercado,
    periodo: "2026-08",
    rango: {
      minimo: Math.round(f.centro * 0.92 * 100) / 100,
      maximo: Math.round(f.centro * 1.08 * 100) / 100,
      centro: f.centro,
    },
    unidad: "kg",
    confianza: f.confianza,
    procedencia: f.procedencia,
    observacionesUsadas: f.observaciones,
    fechaObservacionMasReciente: f.fecha,
    conflictos: [],
    // Quién lo dijo, a partir de la confianza: así el modo demo cuenta la
    // procedencia igual que la API.
    voces: f.procedencia === "estimado" ? { siip_ipc: 1 } : { [VOZ_POR_CONFIANZA[f.confianza]]: f.observaciones },
    factorMercado: f.procedencia === "estimado" ? 1.05 : null,
    antiguedadDias: f.fecha ? diasDesde(f.fecha) : null,
    motivosRango: [],
  };
}

const ORDEN_NIVEL = { minorista: 0, mayorista: 1 } as const;

function codigoDesdeNombre(nombre: string): string {
  return (
    nombre
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "")
      .slice(0, 60) || "sin_nombre"
  );
}

function codigoLibre(base: string, existe: (codigo: string) => boolean): string {
  let codigo = base;
  for (let n = 2; existe(codigo); n++) codigo = `${base}_${n}`;
  return codigo;
}

export class PreciosMemoria
  implements PrecioRepositorio, CatalogoRepositorio, CatalogoAdminRepositorio, HistorialRepositorio, ReferenciasRepositorio
{
  // Copias por instancia: lo que el administrador cambie en una sesión de
  // memoria no se filtra a otra (ni a otra prueba).
  private readonly listaMercados: Mercado[] = [...MERCADOS];
  private readonly listaProductos: Producto[] = [...PRODUCTOS];

  /**
   * Historia de demostración: 12 meses alrededor del precio medio de la
   * tabla, con una oscilación fija. Sirve para ver el gráfico sin servidor;
   * no son datos reales.
   */
  async historial(codigoProducto: string, meses = 12): Promise<HistorialPrecio> {
    const filas = PRECIOS.filter((f) => f.producto === codigoProducto);
    if (filas.length === 0) return { unidad: "kg", puntos: [] };
    const base = filas.reduce((suma, f) => suma + f.centro, 0) / filas.length;
    const n = Math.min(meses, 12);
    const puntos: HistorialPrecio["puntos"][number][] = [];
    for (let i = 0; i < n; i++) {
      const fecha = new Date(Date.UTC(2026, 8 - (n - 1 - i), 1));
      const periodo = `${fecha.getUTCFullYear()}-${String(fecha.getUTCMonth() + 1).padStart(2, "0")}`;
      const ola = 1 + 0.06 * Math.sin(i / 1.7) + i * 0.006;
      puntos.push({ periodo, nivel: "mayorista", precio: Math.round(base * 0.68 * ola * 100) / 100, observaciones: 20 });
      puntos.push({ periodo, nivel: "minorista", precio: Math.round(base * ola * 100) / 100, observaciones: 1 });
    }
    return { unidad: "kg", puntos };
  }

  /** La referencia de la ciudad en memoria: el precio estimado (sin medir) de cada nivel. */
  async referencias(): Promise<PrecioReferencial[]> {
    return Promise.all(
      this.listaProductos.map(async (producto) => {
        const lugares = await this.compararMercados(producto.codigo);
        const del = (nivel: string) =>
          lugares.find((x) => x.mercado.nivelPrecio === nivel && x.precio.procedencia === "estimado")?.precio ??
          lugares.find((x) => x.mercado.nivelPrecio === nivel)?.precio ??
          null;
        return { producto, consumidor: del("minorista"), mayorista: del("mayorista") };
      }),
    );
  }

  async compararMercados(codigoProducto: string, zona?: string): Promise<PrecioEnMercado[]> {
    return PRECIOS.filter((f) => f.producto === codigoProducto)
      .map((f) => ({ mercado: this.listaMercados.find((m) => m.codigo === f.mercado)!, precio: aPrecio(f) }))
      .filter((x) => !zona || x.mercado.zona === zona)
      .sort(
        (a, b) =>
          ORDEN_NIVEL[a.mercado.nivelPrecio] - ORDEN_NIVEL[b.mercado.nivelPrecio] ||
          a.precio.rango.centro - b.precio.rango.centro,
      );
  }

  async precioEnMercado(codigoProducto: string, codigoMercado: string): Promise<Precio> {
    const fila = PRECIOS.find((f) => f.producto === codigoProducto && f.mercado === codigoMercado);
    if (!fila) throw new Error(`Sin datos para ${codigoProducto} en ${codigoMercado}`);
    return aPrecio(fila);
  }

  async calcularCanasta(items: readonly ItemCanasta[], zona?: string): Promise<CostoCanasta[]> {
    const mercados = this.listaMercados.filter((m) => !zona || m.zona === zona);
    const resultado: CostoCanasta[] = [];

    for (const mercado of mercados) {
      let total = 0;
      let cubiertos = 0;
      let estimados = 0;
      const faltantes: string[] = [];

      for (const item of items) {
        const fila = PRECIOS.find(
          (f) => f.producto === item.codigoProducto && f.mercado === mercado.codigo,
        );
        if (!fila) {
          faltantes.push(item.codigoProducto);
          continue;
        }
        total += fila.centro * item.cantidad;
        cubiertos += 1;
        if (fila.procedencia === "estimado") estimados += 1;
      }
      if (cubiertos === 0) continue;

      resultado.push({
        codigoMercado: mercado.codigo,
        nombreMercado: mercado.nombre,
        zona: mercado.zona,
        costoTotal: Math.round(total * 100) / 100,
        productosCubiertos: cubiertos,
        productosPedidos: items.length,
        cobertura: cubiertos / items.length,
        faltantes,
        productosEstimados: estimados,
        nivelPrecio: mercado.nivelPrecio,
        costoMinimo: Math.round(total * 0.92 * 100) / 100,
        costoMaximo: Math.round(total * 1.08 * 100) / 100,
      });
    }

    return resultado.sort(
      (a, b) => b.cobertura - a.cobertura || a.costoTotal - b.costoTotal,
    );
  }

  async productos(): Promise<Producto[]> {
    return [...this.listaProductos];
  }

  async mercados(zona?: string): Promise<Mercado[]> {
    return zona ? this.listaMercados.filter((m) => m.zona === zona) : [...this.listaMercados];
  }

  // --- catálogo del administrador (mismas reglas mínimas que el backend) ---

  async crearPuntoVenta(datos: DatosPuntoVenta): Promise<Mercado> {
    const codigo = codigoLibre(codigoDesdeNombre(datos.nombre), (c) => this.listaMercados.some((m) => m.codigo === c));
    const mercado = this.aMercado(codigo, datos);
    this.listaMercados.push(mercado);
    return mercado;
  }

  async actualizarPuntoVenta(codigo: string, datos: DatosPuntoVenta): Promise<Mercado> {
    const i = this.listaMercados.findIndex((m) => m.codigo === codigo);
    if (i < 0) throw new Error(`No existe el mercado ${codigo}`);
    const mercado = this.aMercado(codigo, datos);
    this.listaMercados[i] = mercado;
    return mercado;
  }

  async eliminarPuntoVenta(codigo: string): Promise<void> {
    if (this.listaMercados.some((m) => m.codigoPadre === codigo)) {
      throw new Error(`No se puede eliminar ${codigo}: tiene sectores`);
    }
    const i = this.listaMercados.findIndex((m) => m.codigo === codigo);
    if (i < 0) throw new Error(`No existe el mercado ${codigo}`);
    this.listaMercados.splice(i, 1);
  }

  async crearProducto(datos: DatosProducto): Promise<Producto> {
    const codigo = codigoLibre(codigoDesdeNombre(datos.nombre), (c) => this.listaProductos.some((p) => p.codigo === c));
    const producto = this.aProducto(codigo, datos);
    this.listaProductos.push(producto);
    return producto;
  }

  async actualizarProducto(codigo: string, datos: DatosProducto): Promise<Producto> {
    const i = this.listaProductos.findIndex((p) => p.codigo === codigo);
    if (i < 0) throw new Error(`No existe el producto ${codigo}`);
    const producto = this.aProducto(codigo, datos);
    this.listaProductos[i] = producto;
    return producto;
  }

  async eliminarProducto(codigo: string): Promise<void> {
    const i = this.listaProductos.findIndex((p) => p.codigo === codigo);
    if (i < 0) throw new Error(`No existe el producto ${codigo}`);
    this.listaProductos.splice(i, 1);
  }

  private aMercado(codigo: string, d: DatosPuntoVenta): Mercado {
    if (!d.nombre.trim()) throw new Error("El punto de venta necesita un nombre");
    if (!ubicacionValida(d.latitud, d.longitud)) {
      throw new Error("La ubicación tiene que tener latitud y longitud, dentro de La Paz o El Alto");
    }
    return {
      codigo,
      nombre: d.nombre.trim(),
      tipo: d.tipo,
      zona: d.zona,
      macrodistrito: d.macrodistrito,
      codigoPadre: d.codigoPadre,
      nivelPrecio: d.tipo === "mayorista" ? "mayorista" : "minorista",
      latitud: d.latitud ?? undefined,
      longitud: d.longitud ?? undefined,
    };
  }

  private aProducto(codigo: string, d: DatosProducto): Producto {
    if (!d.nombre.trim()) throw new Error("El producto necesita un nombre");
    const posibles = PRESENTACIONES_POR_UNIDAD[d.unidadBase];
    const elegidas = d.presentaciones.length ? posibles.filter((p) => d.presentaciones.includes(p.codigo)) : posibles;
    if (!elegidas.some((p) => p.factor === 1)) {
      throw new Error("Falta la presentación de la unidad base (kilo, litro, unidad o atado)");
    }
    return {
      codigo,
      nombre: d.nombre.trim(),
      categoria: d.categoria,
      esPerecedero: d.diasConservacion <= 7,
      unidadBase: d.unidadBase,
      diasConservacion: d.diasConservacion,
      presentaciones: elegidas,
    };
  }
}
