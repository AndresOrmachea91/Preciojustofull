/**
 * Prueba de un caso de uso COMPLETO con el backend apagado.
 *
 * Esta es la demostración de la arquitectura hexagonal en el frontend: el
 * caso de uso recibe el adaptador en memoria en lugar del de HTTP, porque
 * depende del puerto y no de la implementación.
 */
import { describe, expect, it } from "vitest";

import { CalcularCanasta } from "@/aplicacion/casosUso/calcularCanasta";
import { CompararMercados } from "@/aplicacion/casosUso/compararMercados";
import { PreciosMemoria } from "@/infraestructura/memoria/PreciosMemoria";
import { crearContenedor } from "@/infraestructura/contenedor";

describe("CompararMercados", () => {
  const caso = new CompararMercados(new PreciosMemoria());

  it("devuelve el más conveniente primero", async () => {
    const resultado = await caso.ejecutar("tomate");
    expect(resultado.opciones.length).toBeGreaterThan(1);
    expect(resultado.masConveniente).not.toBeNull();
    expect(resultado.masConveniente!.mercado.codigo).toBe("villafatima");
  });

  it("informa cuánto se puede ahorrar", async () => {
    const resultado = await caso.ejecutar("tomate");
    expect(resultado.ahorro).toBeGreaterThan(0);
  });

  it("el minimarket sale más caro que el mercado", async () => {
    const resultado = await caso.ejecutar("tomate");
    const porCodigo = Object.fromEntries(
      resultado.opciones.map((o) => [o.mercado.codigo, o.precio.rango.centro]),
    );
    expect(porCodigo["minimarket_sopocachi"]).toBeGreaterThan(porCodigo["rodriguez"]);
  });

  it("filtra por zona", async () => {
    const resultado = await caso.ejecutar("tomate", "Centro");
    expect(resultado.opciones.every((o) => o.mercado.zona === "Centro")).toBe(true);
  });

  it("un producto sin datos devuelve lista vacía, no un error", async () => {
    const resultado = await caso.ejecutar("no_existe");
    expect(resultado.opciones).toHaveLength(0);
    expect(resultado.masConveniente).toBeNull();
  });
});

describe("CalcularCanasta", () => {
  const caso = new CalcularCanasta(new PreciosMemoria());

  it("prioriza los mercados que cubren toda la lista", async () => {
    const resultado = await caso.ejecutar([
      { codigoProducto: "tomate", cantidad: 2 },
      { codigoProducto: "papa", cantidad: 1 },
      { codigoProducto: "arroz", cantidad: 1 },
    ]);
    expect(resultado.opciones.length).toBeGreaterThan(0);
    expect(resultado.opciones[0].cobertura).toBeGreaterThanOrEqual(
      resultado.opciones[resultado.opciones.length - 1].cobertura,
    );
  });

  it("una canasta vacía no rompe nada", async () => {
    const resultado = await caso.ejecutar([]);
    expect(resultado.opciones).toHaveLength(0);
    expect(resultado.masBarato).toBeNull();
  });
});

describe("Contenedor", () => {
  it("arma los casos de uso con el adaptador en memoria", async () => {
    const contenedor = crearContenedor("memoria");
    const resultado = await contenedor.compararMercados.ejecutar("papa");
    expect(resultado.opciones.length).toBeGreaterThan(0);
  });
});

