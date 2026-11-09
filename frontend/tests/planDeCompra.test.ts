/**
 * C144: el plan de compra cuenta el pasaje. Repartir la lista en varios
 * mercados solo se recomienda si deja más plata que el pasaje que cuesta;
 * y dice qué se gana y qué se pierde frente a ir a un solo lugar.
 */
import { describe, expect, it } from "vitest";

import { agruparReferencias } from "@/aplicacion/casosUso/publico/verPreciosReferenciales";
import { PlanificarCompra } from "@/aplicacion/casosUso/usuario/planificarCompra";
import { panoramaDeMercados, type EntradaDirectorio, type Mercado, type PrecioReferencial } from "@/dominio/modelo";
import { planificarCompra, type Necesidad, type PrecioEnLugar } from "@/dominio/servicio/planificarCompra";
import { PreciosMemoria } from "@/infraestructura/memoria/PreciosMemoria";

function mercado(codigo: string, latitud: number, longitud: number, extra: Partial<Mercado> = {}): Mercado {
  return {
    codigo, nombre: `Mercado ${codigo}`, tipo: "mercado", zona: "Centro", macrodistrito: "Centro",
    codigoPadre: null, nivelPrecio: "minorista", latitud, longitud, ...extra,
  } as Mercado;
}

// Rodríguez y Lanza están lejos entre sí (más de 800 m); Lanza y Camacho, a una cuadra.
const RODRIGUEZ = mercado("rodriguez", -16.5002, -68.1416);
const LANZA = mercado("lanza", -16.4952, -68.1355);
const CAMACHO = mercado("camacho", -16.4968, -68.1342);
const MAYORISTA = mercado("mayorista", -16.49, -68.14, { tipo: "mayorista", nivelPrecio: "mayorista" });

const papa: Necesidad = { codigoProducto: "papa", nombre: "Papa", cantidadBase: 10, unidad: "kg" };
const tomate: Necesidad = { codigoProducto: "tomate", nombre: "Tomate", cantidadBase: 2, unidad: "kg" };

const p = (m: Mercado, precioUnidad: number): PrecioEnLugar => ({ mercado: m, precioUnidad, procedencia: "observado" });

describe("planificarCompra", () => {
  it("si repartir ahorra menos que el pasaje, recomienda un solo lugar y muestra la cuenta", () => {
    // Ir al Lanza por el tomate ahorra Bs 0,40, pero cuesta un minibús más.
    const precios = new Map([
      ["papa", [p(RODRIGUEZ, 4), p(LANZA, 4.5)]],
      ["tomate", [p(RODRIGUEZ, 8), p(LANZA, 7.8)]],
    ]);
    const r = planificarCompra([papa, tomate], precios, { pasaje: 1.5, origen: null });

    expect(r.mejor!.paradas.map((x) => x.mercado.codigo)).toEqual(["rodriguez"]);
    expect(r.mejor!.costoProductos).toBe(56);       // 10 × 4 + 2 × 8
    expect(r.mejor!.costoPasajes).toBe(3);          // ida y vuelta
    expect(r.mejor!.total).toBe(59);
    expect(r.neto).toBe(0);
    const repartido = r.porParadas.find((x) => x.paradas.length === 2)!;
    expect(repartido.costoProductos).toBe(55.6);
    expect(repartido.costoPasajes).toBe(4.5);       // un tramo más
  });

  it("si repartir ahorra más que el pasaje, reparte y dice qué gana y qué pierde", () => {
    const precios = new Map([
      ["papa", [p(RODRIGUEZ, 4), p(LANZA, 6)]],
      ["tomate", [p(RODRIGUEZ, 12), p(LANZA, 7)]],
    ]);
    const r = planificarCompra([papa, tomate], precios, { pasaje: 1.5, origen: null });

    expect(r.mejor!.paradas.map((x) => x.mercado.codigo).sort()).toEqual(["lanza", "rodriguez"]);
    // Un solo lugar: Rodríguez, 40 + 24 = 64 (+3). Repartido: 40 + 14 = 54 (+4,5).
    expect(r.unSoloLugar!.total).toBe(67);
    expect(r.ganaEnPrecios).toBe(10);
    expect(r.pierdeEnPasajes).toBe(1.5);
    expect(r.neto).toBe(8.5);
  });

  it("entre mercados vecinos se camina: no se paga pasaje", () => {
    const precios = new Map([
      ["papa", [p(LANZA, 4), p(CAMACHO, 6)]],
      ["tomate", [p(LANZA, 12), p(CAMACHO, 7)]],
    ]);
    const r = planificarCompra([papa, tomate], precios, { pasaje: 1.5, origen: null });
    expect(r.mejor!.paradas).toHaveLength(2);
    expect(r.mejor!.tramos).toBe(3);
    expect(r.mejor!.tramosPagados).toBe(2);         // solo la ida y la vuelta
  });

  it("si se sale de cerca del mercado, la ida es a pie", () => {
    const precios = new Map([["papa", [p(LANZA, 4)]]]);
    const r = planificarCompra([papa], precios, { pasaje: 1.5, origen: { latitud: -16.4955, longitud: -68.1352 } });
    expect(r.mejor!.tramosPagados).toBe(0);
    expect(r.mejor!.distanciaKm).not.toBeNull();
  });

  it("no mezcla precios mayoristas y dice lo que falta", () => {
    const precios = new Map([
      ["papa", [p(MAYORISTA, 1), p(RODRIGUEZ, 4)]],
      ["tomate", [p(MAYORISTA, 2)]],
    ]);
    const r = planificarCompra([papa, tomate], precios, { pasaje: 1.5, origen: null });
    expect(r.mejor!.paradas.map((x) => x.mercado.codigo)).toEqual(["rodriguez"]);
    expect(r.faltantes.map((f) => f.codigoProducto)).toEqual(["tomate"]);
  });

  it("ir del Centro a la Zona Sur cuesta el pasaje más caro (Bs 3 y Bs 3,50)", () => {
    const ACHUMANI = mercado("achumani", -16.5305, -68.0745, { macrodistrito: "Sur" });
    const centro = { latitud: -16.4958, longitud: -68.1336 };
    const precios = new Map([["papa", [p(ACHUMANI, 4)]]]);
    const alSur = planificarCompra([papa], precios, { pasaje: 3, pasajeZonaSur: 3.5, origen: centro });
    expect(alSur.mejor!.tramosZonaSur).toBe(2);       // ida y vuelta cruzan a la Zona Sur
    expect(alSur.mejor!.costoPasajes).toBe(7);
    const enElCentro = planificarCompra([papa], new Map([["papa", [p(RODRIGUEZ, 4)]]]), {
      pasaje: 3, pasajeZonaSur: 3.5, origen: centro,
    });
    expect(enElCentro.mejor!.costoPasajes).toBe(6);   // Bs 3 la ida y Bs 3 la vuelta
    expect(enElCentro.mejor!.tramosZonaSur).toBe(0);
  });

  it("sin ningún precio no inventa un plan", () => {
    const r = planificarCompra([papa], new Map(), { pasaje: 1.5, origen: null });
    expect(r.mejor).toBeNull();
    expect(r.faltantes).toHaveLength(1);
  });
});

describe("PlanificarCompra (caso de uso)", () => {
  it("cotiza una lista con los precios en memoria y rechaza un pasaje negativo", async () => {
    const memoria = new PreciosMemoria();
    const productos = await memoria.productos();
    const caso = new PlanificarCompra(memoria);
    const items = [{ codigoProducto: "tomate", cantidad: 2, presentacion: "kilo" }];
    const r = await caso.ejecutar(items, productos, { pasaje: 1.5, origen: null });
    expect(r.mejor).not.toBeNull();
    expect(r.mejor!.total).toBeCloseTo(r.mejor!.costoProductos + r.mejor!.costoPasajes, 2);
    await expect(caso.ejecutar(items, productos, { pasaje: -1, origen: null })).rejects.toThrow(/pasaje/);
  });
});

describe("panoramaDeMercados", () => {
  it("cuenta mercados, cuántos tienen caseras y los agrupa por macrodistrito", () => {
    const entrada = (m: Mercado, puestos: number, ofertas = 0): EntradaDirectorio => ({ mercado: m, puestos, ofertas, sectores: 0 });
    const sector = mercado("rodriguez_sector", -16.5, -68.14, { codigoPadre: "rodriguez" });
    const sur = mercado("achumani", -16.53, -68.08, { macrodistrito: "Sur" });
    const p = panoramaDeMercados([
      entrada(RODRIGUEZ, 3, 1), entrada(LANZA, 0), entrada(sector, 2), entrada(sur, 1),
      entrada(MAYORISTA, 0),
    ]);
    expect(p.mercados).toBe(3);                     // el sector no cuenta como mercado aparte
    expect(p.conCaseras).toBe(2);
    expect(p.puestos).toBe(6);                      // los del sector suman a su mercado
    expect(p.ofertas).toBe(1);
    expect(p.mayoristas).toBe(1);
    expect(p.porMacrodistrito[0]).toEqual({ nombre: "Centro", mercados: 2, conCaseras: 1 });
  });
});

describe("agruparReferencias", () => {
  it("agrupa por categoría y busca sin tildes", async () => {
    const filas: PrecioReferencial[] = await new PreciosMemoria().referencias();
    const grupos = agruparReferencias(filas);
    expect(grupos.reduce((s, g) => s + g.filas.length, 0)).toBe(filas.length);
    const papa = filas.find((f) => f.producto.nombre.toLowerCase().includes("papa"));
    if (papa) expect(agruparReferencias(filas, "PAPA").flatMap((g) => g.filas)).toContain(papa);
  });
});
