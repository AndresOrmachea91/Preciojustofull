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
  ItemCanasta,
  Mercado,
  Precio,
  PrecioEnMercado,
  Producto,
} from "@/dominio/modelo";
import type { CatalogoRepositorio, PrecioRepositorio } from "@/aplicacion/puertos";

const MERCADOS: Mercado[] = [
  { codigo: "rodriguez", nombre: "Mercado Rodríguez", tipo: "mercado", zona: "Cotahuma", macrodistrito: "Cotahuma", codigoPadre: null, nivelPrecio: "minorista", latitud: -16.500192, longitud: -68.138992 },
  { codigo: "rodriguez_cubierto", nombre: "Mercado Rodríguez - sector cubierto", tipo: "mercado", zona: "Cotahuma", macrodistrito: "Cotahuma", codigoPadre: "rodriguez", nivelPrecio: "minorista", latitud: -16.500676, longitud: -68.139072 },
  { codigo: "lanza", nombre: "Mercado Lanza", tipo: "mercado", zona: "Centro", macrodistrito: "Centro", codigoPadre: null, nivelPrecio: "minorista", latitud: -16.4957, longitud: -68.136 },
  { codigo: "villafatima", nombre: "Mercado Villa Fátima", tipo: "mercado", zona: "Periférica", macrodistrito: "Periférica", codigoPadre: null, nivelPrecio: "minorista", latitud: -16.4816, longitud: -68.1194 },
  { codigo: "minimarket_sopocachi", nombre: "Minimarket Sopocachi", tipo: "minimarket", zona: "Cotahuma", macrodistrito: "Cotahuma", codigoPadre: null, nivelPrecio: "minorista", latitud: -16.51, longitud: -68.13 },
  { codigo: "ketal_san_pedro", nombre: "Ketal San Pedro", tipo: "supermercado", zona: "Cotahuma", macrodistrito: "Cotahuma", codigoPadre: null, nivelPrecio: "minorista", latitud: -16.501668, longitud: -68.135871 },
  { codigo: "makro_centro", nombre: "Makro", tipo: "mayorista", zona: "Centro", macrodistrito: "Centro", codigoPadre: null, nivelPrecio: "mayorista", latitud: -16.493233, longitud: -68.14427 },
];

const PRODUCTOS: Producto[] = [
  { codigo: "tomate", nombre: "Tomate", categoria: "hortaliza", esPerecedero: true },
  { codigo: "papa", nombre: "Papa holandesa", categoria: "tuberculo", esPerecedero: false },
  { codigo: "arroz", nombre: "Arroz de primera", categoria: "abarrote", esPerecedero: false },
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
  { producto: "tomate", mercado: "minimarket_sopocachi", centro: 19.57, confianza: "verificado", procedencia: "observado", observaciones: 1, fecha: "2026-09-12" },
  { producto: "tomate", mercado: "ketal_san_pedro", centro: 17.8, confianza: "medio", procedencia: "estimado", observaciones: 104, fecha: null },
  { producto: "tomate", mercado: "makro_centro", centro: 5.41, confianza: "medio", procedencia: "estimado", observaciones: 103, fecha: "2026-07-30" },
  { producto: "papa", mercado: "villafatima", centro: 6.78, confianza: "verificado", procedencia: "observado", observaciones: 1, fecha: "2026-09-10" },
  { producto: "papa", mercado: "rodriguez", centro: 6.96, confianza: "alto", procedencia: "observado", observaciones: 1, fecha: "2026-09-14" },
  { producto: "papa", mercado: "lanza", centro: 7.39, confianza: "bajo", procedencia: "observado", observaciones: 1, fecha: null },
  { producto: "papa", mercado: "makro_centro", centro: 3.72, confianza: "medio", procedencia: "estimado", observaciones: 103, fecha: "2026-07-30" },
  { producto: "arroz", mercado: "rodriguez", centro: 8.2, confianza: "alto", procedencia: "observado", observaciones: 1, fecha: "2026-09-14" },
  { producto: "arroz", mercado: "lanza", centro: 8.6, confianza: "alto", procedencia: "observado", observaciones: 1, fecha: "2026-09-13" },
  { producto: "arroz", mercado: "minimarket_sopocachi", centro: 10.5, confianza: "verificado", procedencia: "observado", observaciones: 1, fecha: "2026-09-12" },
  { producto: "arroz", mercado: "ketal_san_pedro", centro: 14.83, confianza: "medio", procedencia: "estimado", observaciones: 104, fecha: null },
  { producto: "arroz", mercado: "makro_centro", centro: 12.28, confianza: "medio", procedencia: "estimado", observaciones: 103, fecha: "2026-07-30" },
];

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
  };
}

const ORDEN_NIVEL = { minorista: 0, mayorista: 1 } as const;

export class PreciosMemoria implements PrecioRepositorio, CatalogoRepositorio {
  async compararMercados(codigoProducto: string, zona?: string): Promise<PrecioEnMercado[]> {
    return PRECIOS.filter((f) => f.producto === codigoProducto)
      .map((f) => ({ mercado: MERCADOS.find((m) => m.codigo === f.mercado)!, precio: aPrecio(f) }))
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
    const mercados = MERCADOS.filter((m) => !zona || m.zona === zona);
    const resultado: CostoCanasta[] = [];

    for (const mercado of mercados) {
      let total = 0;
      let cubiertos = 0;
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
      });
    }

    return resultado.sort(
      (a, b) => b.cobertura - a.cobertura || a.costoTotal - b.costoTotal,
    );
  }

  async productos(): Promise<Producto[]> {
    return PRODUCTOS;
  }

  async mercados(zona?: string): Promise<Mercado[]> {
    return zona ? MERCADOS.filter((m) => m.zona === zona) : MERCADOS;
  }
}
