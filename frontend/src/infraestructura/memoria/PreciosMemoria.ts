/**
 * Adaptador en memoria de los mismos puertos.
 *
 * Permite desarrollar la interfaz y correr las pruebas sin backend. No es
 * un simulacro improvisado: implementa exactamente el mismo contrato que
 * el adaptador HTTP, y por eso se pueden intercambiar sin tocar nada más.
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
  { codigo: "rodriguez", nombre: "Mercado Rodríguez", tipo: "mercado", zona: "San Pedro", latitud: -16.4998, longitud: -68.1385 },
  { codigo: "lanza", nombre: "Mercado Lanza", tipo: "mercado", zona: "Centro", latitud: -16.4957, longitud: -68.136 },
  { codigo: "villafatima", nombre: "Mercado Villa Fátima", tipo: "mercado", zona: "Villa Fátima", latitud: -16.4816, longitud: -68.1194 },
  { codigo: "minimarket_sopocachi", nombre: "Minimarket Sopocachi", tipo: "minimarket", zona: "Sopocachi", latitud: -16.51, longitud: -68.13 },
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
  observaciones: number;
}

const PRECIOS: Fila[] = [
  { producto: "tomate", mercado: "villafatima", centro: 13.04, confianza: "medio", observaciones: 1 },
  { producto: "tomate", mercado: "rodriguez", centro: 14.35, confianza: "verificado", observaciones: 2 },
  { producto: "tomate", mercado: "lanza", centro: 16.3, confianza: "bajo", observaciones: 1 },
  { producto: "tomate", mercado: "minimarket_sopocachi", centro: 19.57, confianza: "verificado", observaciones: 1 },
  { producto: "papa", mercado: "villafatima", centro: 6.78, confianza: "verificado", observaciones: 1 },
  { producto: "papa", mercado: "rodriguez", centro: 6.96, confianza: "alto", observaciones: 1 },
  { producto: "papa", mercado: "lanza", centro: 7.39, confianza: "bajo", observaciones: 1 },
  { producto: "arroz", mercado: "rodriguez", centro: 8.2, confianza: "alto", observaciones: 1 },
  { producto: "arroz", mercado: "lanza", centro: 8.6, confianza: "alto", observaciones: 1 },
  { producto: "arroz", mercado: "minimarket_sopocachi", centro: 10.5, confianza: "verificado", observaciones: 1 },
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
    observacionesUsadas: f.observaciones,
    conflictos: [],
  };
}

export class PreciosMemoria implements PrecioRepositorio, CatalogoRepositorio {
  async compararMercados(codigoProducto: string, zona?: string): Promise<PrecioEnMercado[]> {
    return PRECIOS.filter((f) => f.producto === codigoProducto)
      .map((f) => ({ mercado: MERCADOS.find((m) => m.codigo === f.mercado)!, precio: aPrecio(f) }))
      .filter((x) => !zona || x.mercado.zona === zona)
      .sort((a, b) => a.precio.rango.centro - b.precio.rango.centro);
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

