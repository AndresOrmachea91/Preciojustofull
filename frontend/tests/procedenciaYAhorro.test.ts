/**
 * C125 procedencia en lenguaje llano, C128 empates, C129 "Ahorra X Bs" y
 * C127 la planilla de campo. Reglas puras: sin navegador ni red.
 */
import { describe, expect, it } from "vitest";

import { resumirCanasta } from "@/aplicacion/casosUso/publico/calcularCanasta";
import { OperarSistema, PLANTILLA_CAMPO } from "@/aplicacion/casosUso/administracion/operarSistema";
import type { OperacionRepositorio } from "@/aplicacion/puertos";
import {
  empatan,
  esPrecioViejo,
  explicacionProcedencia,
  lecturaDelSesgo,
  porcentaje,
  quienesHablan,
  type CostoCanasta,
  type Precio,
} from "@/dominio/modelo";

function precio(cambios: Partial<Precio> = {}): Precio {
  return {
    codigoProducto: "papa", codigoMercado: "rodriguez", periodo: "2026-10-12",
    rango: { minimo: 7.5, maximo: 8.5, centro: 8 }, unidad: "kg", confianza: "alto", procedencia: "observado",
    observacionesUsadas: 3, fechaObservacionMasReciente: "2026-10-12", conflictos: [],
    voces: { vendedor: 1, ciudadano: 2 }, factorMercado: null, antiguedadDias: 2, motivosRango: [],
    ...cambios,
  };
}

function costo(nombre: string, total: number, margen = 0.08, cambios: Partial<CostoCanasta> = {}): CostoCanasta {
  return {
    codigoMercado: nombre.toLowerCase(), nombreMercado: nombre, zona: "Centro", costoTotal: total,
    productosCubiertos: 3, productosPedidos: 3, cobertura: 1, faltantes: [], productosEstimados: 0,
    nivelPrecio: "minorista", costoMinimo: total * (1 - margen), costoMaximo: total * (1 + margen), ...cambios,
  };
}

describe("procedencia en lenguaje llano", () => {
  it("dice quién y cuándo, contando a cada persona una vez", () => {
    expect(quienesHablan({ vendedor: 1, ciudadano: 2 })).toBe("2 compradores y un vendedor del puesto");
    expect(explicacionProcedencia(precio())).toBe("Visto el 12/10 por 2 compradores y un vendedor del puesto.");
  });

  it("un estimado dice de qué referencia sale y cuánto se ajustó por el mercado", () => {
    const estimado = precio({
      procedencia: "estimado", periodo: "2026-09", voces: { siip_ipc: 1 }, factorMercado: 1.06, observacionesUsadas: 1,
    });
    const texto = explicacionProcedencia(estimado, {
      codigo: "lanza", nombre: "Mercado Lanza", tipo: "mercado", zona: "Centro", macrodistrito: "Centro",
      codigoPadre: null, nivelPrecio: "minorista",
    });
    expect(texto).toContain("precio al consumidor de la ciudad (SIIP)");
    expect(texto).toContain("septiembre de 2026");
    expect(texto).toContain("+6 % porque Mercado Lanza suele estar más caro");
    expect(texto).toContain("Todavía nadie verificó este precio en Mercado Lanza");
  });

  it("un dato de más de una semana se marca como viejo", () => {
    expect(esPrecioViejo(precio({ antiguedadDias: 7 }))).toBe(false);
    expect(esPrecioViejo(precio({ antiguedadDias: 8 }))).toBe(true);
    expect(esPrecioViejo(precio({ antiguedadDias: null }))).toBe(false);
  });
});

describe("empates y ahorro", () => {
  it("empatan cuando la diferencia es menor que el margen de error", () => {
    expect(empatan({ minimo: 9, maximo: 11, centro: 10 }, { minimo: 9.6, maximo: 10.6, centro: 10.1 })).toBe(true);
    expect(empatan({ minimo: 9, maximo: 10, centro: 9.5 }, { minimo: 12, maximo: 13, centro: 12.5 })).toBe(false);
    // Sin rango conocido no se declara empate: no hay con qué medir el margen.
    expect(empatan({ minimo: 10, maximo: 10, centro: 10 }, { minimo: 10.2, maximo: 10.2, centro: 10.2 })).toBe(false);
  });

  it("dice cuánto se ahorra frente al más caro y quiénes empatan con el mejor", () => {
    const r = resumirCanasta([costo("Lanza", 104), costo("Rodríguez", 100), costo("Sopocachi", 140)]);
    expect(r.masBarato?.nombreMercado).toBe("Rodríguez");
    expect(r.masCaro?.nombreMercado).toBe("Sopocachi");
    expect(r.ahorro).toBe(40);
    expect(r.empatanConElMejor.map((c) => c.nombreMercado)).toEqual(["Lanza"]);
  });

  it("un lugar al que le falta un producto no entra en el ahorro", () => {
    const r = resumirCanasta([costo("Rodríguez", 100), costo("Incompleto", 20, 0.08, { cobertura: 0.5, productosCubiertos: 1 })]);
    expect(r.ahorro).toBe(0);
    expect(r.masCaro).toBeNull();
  });
});

describe("confiabilidad", () => {
  it("lee el sesgo en una frase", () => {
    expect(porcentaje(0.084)).toBe("8,4 %");
    expect(lecturaDelSesgo(-0.05)).toContain("quedarse corto");
    expect(lecturaDelSesgo(0.003)).toContain("ni a quedarse corto ni a pasarse");
  });
});

describe("planilla de campo", () => {
  const repositorio: OperacionRepositorio = {
    importarCampo: async (csv, _archivo, soloRevisar) => ({
      leidas: csv.trim().split("\n").length - 1, validas: 2, guardadas: soloRevisar ? 0 : 2, soloRevisar, rechazadas: [],
    }),
    salud: async () => { throw new Error("no se usa"); },
  };

  it("la plantilla trae las columnas que exige el backend y se acepta tal cual", async () => {
    const r = await new OperarSistema(repositorio).importarCampo(PLANTILLA_CAMPO, "plantilla.csv", true);
    expect(r.leidas).toBe(2);
    expect(r.guardadas).toBe(0);
  });

  it("frena una planilla sin las columnas obligatorias antes de enviarla", async () => {
    await expect(new OperarSistema(repositorio).importarCampo("fecha;mercado\n2026-10-01;x", "x.csv", true))
      .rejects.toThrow(/producto, monto, presentacion/);
    await expect(new OperarSistema(repositorio).importarCampo("  ", "x.csv", true)).rejects.toThrow(/vacía/);
  });
});
