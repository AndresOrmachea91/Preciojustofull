/**
 * @vitest-environment jsdom
 *
 * El mapa monta con datos que vienen del caso de uso, y al elegir un punto
 * muestra su precio con procedencia. Leaflet solo dibuja.
 */
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { VerMapa } from "@/aplicacion/casosUso/verMapa";
import { PreciosMemoria } from "@/infraestructura/memoria/PreciosMemoria";
import { MapaPuntosVenta } from "@/ui/componentes/MapaPuntosVenta";
import { PanelPunto } from "@/ui/componentes/PanelPunto";

afterEach(cleanup);

describe("VerMapa", () => {
  it("junta catálogo y precios: un marcador por punto de venta, con o sin precio", async () => {
    const memoria = new PreciosMemoria();
    const { marcadores, resumen } = await new VerMapa(memoria, memoria).ejecutar("papa");

    expect(marcadores).toHaveLength(7);                   // los 7 del catálogo en memoria
    expect(resumen.observados + resumen.estimados + resumen.sinDatos).toBe(7);
    expect(resumen.estimados).toBe(1);                     // Makro
    expect(resumen.sinDatos).toBe(3);                      // sin precio de papa: cubierto, mini, ketal
    expect(resumen.porNivel.mayorista).toBe(1);
  });
});

describe("MapaPuntosVenta", () => {
  it("monta un marcador por punto de venta con coordenadas", async () => {
    const memoria = new PreciosMemoria();
    const { marcadores } = await new VerMapa(memoria, memoria).ejecutar("tomate");

    render(<MapaPuntosVenta marcadores={marcadores} seleccionado={null} onSeleccionar={() => {}} />);

    const mapa = screen.getByRole("region", { name: /Mapa de puntos de venta/ });
    expect(mapa.getAttribute("data-marcadores")).toBe("7");
    await waitFor(() => {
      expect(mapa.querySelectorAll("path.leaflet-interactive").length).toBe(7);
    });
  });
});

describe("PanelPunto", () => {
  it("muestra nombre, macrodistrito, tipo y el precio con su procedencia y respaldo", async () => {
    const memoria = new PreciosMemoria();
    const { marcadores } = await new VerMapa(memoria, memoria).ejecutar("tomate");
    const ketal = marcadores.find((m) => m.mercado.codigo === "ketal_san_pedro")!;

    render(<PanelPunto marcador={ketal} producto={{ codigo: "tomate", nombre: "Tomate", categoria: "hortaliza", esPerecedero: true }} />);

    expect(screen.getByRole("heading", { name: "Ketal San Pedro" })).toBeDefined();
    expect(screen.getByText(/Supermercado · Cotahuma/)).toBeDefined();
    expect(screen.getByText("Precio al consumidor")).toBeDefined();
    expect(document.querySelector(".procedencia--estimado")).not.toBeNull();
    expect(screen.getByText(/Todavía nadie verificó este precio en Ketal San Pedro/)).toBeDefined();
    expect(screen.getByText(/104 observaciones de la fuente oficial/)).toBeDefined();
    expect(document.querySelector(".confianza")).not.toBeNull();
  });

  it("un mayorista se presenta como otro nivel, no como competidor", async () => {
    const memoria = new PreciosMemoria();
    const { marcadores } = await new VerMapa(memoria, memoria).ejecutar("tomate");
    const makro = marcadores.find((m) => m.mercado.codigo === "makro_centro")!;

    render(<PanelPunto marcador={makro} producto={null} />);

    expect(screen.getByText("Precio mayorista")).toBeDefined();
    expect(screen.getByText(/Mayorista · Centro/)).toBeDefined();
  });

  it("sin precio lo dice, no lo inventa", () => {
    render(
      <PanelPunto
        marcador={{
          mercado: { codigo: "x", nombre: "Mercado X", tipo: "mercado", zona: "Sur", macrodistrito: "Sur", codigoPadre: null, nivelPrecio: "minorista" },
          precio: null,
        }}
        producto={null}
      />,
    );
    expect(screen.getByText(/No se inventa/)).toBeDefined();
  });
});
