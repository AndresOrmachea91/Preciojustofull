/**
 * Pruebas de una regla de dominio pura: sin React, sin red, sin navegador.
 */
import { describe, expect, it } from "vitest";

import type { PrecioEnMercado, NivelConfianza } from "@/dominio/modelo";
import {
  ahorroPosible,
  ordenarPorConveniencia,
} from "@/dominio/servicio/ordenarPorConveniencia";

function hacer(codigo: string, centro: number, confianza: NivelConfianza = "alto"): PrecioEnMercado {
  return {
    mercado: { codigo, nombre: codigo, tipo: "mercado", zona: "Centro" },
    precio: {
      codigoProducto: "tomate",
      codigoMercado: codigo,
      periodo: "2026-08",
      rango: { minimo: centro * 0.9, maximo: centro * 1.1, centro },
      unidad: "kg",
      confianza,
      observacionesUsadas: 1,
      conflictos: [],
    },
  };
}

describe("ordenarPorConveniencia", () => {
  it("sin distancias, ordena de más barato a más caro", () => {
    const orden = ordenarPorConveniencia([hacer("c", 20), hacer("a", 10), hacer("b", 15)]);
    expect(orden.map((o) => o.mercado.codigo)).toEqual(["a", "b", "c"]);
  });

  it("un mercado lejano deja de convenir aunque sea más barato", () => {
    const orden = ordenarPorConveniencia([hacer("lejos", 10), hacer("cerca", 12)], {
      costoPorKm: 1.5,
      distancias: { lejos: 8, cerca: 0 },
    });
    expect(orden[0].mercado.codigo).toBe("cerca");
  });

  it("penaliza el precio de confianza baja frente a uno verificado", () => {
    const orden = ordenarPorConveniencia([
      hacer("dudoso", 10.0, "bajo"),
      hacer("verificado", 10.5, "verificado"),
    ]);
    expect(orden[0].mercado.codigo).toBe("verificado");
  });

  it("calcula el ahorro entre el más barato y el más caro", () => {
    expect(ahorroPosible([hacer("a", 10), hacer("b", 16.5)])).toBe(6.5);
  });

  it("con un solo mercado no hay ahorro que mostrar", () => {
    expect(ahorroPosible([hacer("a", 10)])).toBe(0);
  });
});

