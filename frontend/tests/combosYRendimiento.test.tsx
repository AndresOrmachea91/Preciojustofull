/**
 * @vitest-environment jsdom
 *
 * C145: el casero arma un combo (2 o 3 productos que cuentan como UNA
 * oferta), y ve cómo le va a su puesto con datos de ejemplo que lo dicen.
 */
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { ofertasQueCuentan } from "@/dominio/modelo";
import { rendimientoDeEjemplo } from "@/dominio/servicio/rendimientoDeEjemplo";
import App from "@/ui/App";

beforeEach(() => {
  window.location.hash = "";
});
afterEach(cleanup);

describe("rendimientoDeEjemplo", () => {
  it("da siempre lo mismo para el mismo puesto, y los combos llegan a más gente", () => {
    const a = rendimientoDeEjemplo("rodriguez/14");
    expect(rendimientoDeEjemplo("rodriguez/14")).toEqual(a);
    expect(a.porDia).toHaveLength(7);
    expect(a.visitasSemana).toBe(a.porDia.reduce((s, x) => s + x, 0));
    expect(a.vieronOfertas).toBe(0);                 // sin ofertas, nadie vio ofertas
    expect(a.alcanceCombo).toBeGreaterThan(a.alcanceOferta);
    const conCombo = rendimientoDeEjemplo("rodriguez/14", { sueltas: 0, combos: 1 });
    expect(conCombo.visitasSemana).toBeGreaterThan(a.visitasSemana);
  });
});

describe("ofertasQueCuentan", () => {
  it("un combo entero cuenta como una", () => {
    expect(ofertasQueCuentan([
      { id: 1, combo: "Combo sopa" }, { id: 2, combo: "Combo sopa" }, { id: 3, combo: null },
    ])).toBe(2);
  });
});

async function ingresar(correo: string, contrasena: string) {
  fireEvent.click(await screen.findByRole("link", { name: "Ingresar" }));
  fireEvent.change(screen.getByLabelText(/^Correo/), { target: { value: correo } });
  fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: contrasena } });
  fireEvent.submit(screen.getByRole("button", { name: "Ingresar" }).closest("form")!);
  await screen.findByRole("button", { name: "Salir" });
}

describe("el casero y sus combos", () => {
  it("publica un combo de dos productos, que aparece con su nombre", async () => {
    render(<App />);
    await ingresar("vendedora@preciojusto.bo", "puesto1234");
    fireEvent.click(await screen.findByRole("tab", { name: "Mis ofertas" }));
    expect(await screen.findByText("Datos de ejemplo")).toBeDefined();
    expect(screen.getByText(/Sus ofertas en combo pueden llegar a más gente/)).toBeDefined();

    fireEvent.click(screen.getByRole("button", { name: /Combo de 2 o 3 productos/ }));
    const form = screen.getByRole("form", { name: "Publicar un combo" });
    fireEvent.change(within(form).getByLabelText("Nombre del combo"), { target: { value: "Combo sopa" } });
    fireEvent.change(within(form).getByLabelText("Producto 1"), { target: { value: "tomate" } });
    fireEvent.change(within(form).getByLabelText("Producto 2"), { target: { value: "papa" } });
    const precios = within(form).getAllByLabelText("Precio de oferta (Bs)");
    fireEvent.change(precios[0]!, { target: { value: "1" } });
    fireEvent.change(precios[1]!, { target: { value: "0.5" } });
    fireEvent.submit(form);

    expect(await screen.findByText(/Combo «Combo sopa» publicado/)).toBeDefined();
    const tabla = await screen.findByRole("table", { name: "Mis ofertas" });
    expect(within(tabla).getAllByText("Combo sopa")).toHaveLength(2);
  });

  it("un combo de un solo producto se avisa antes de mandarlo", async () => {
    render(<App />);
    await ingresar("vendedora@preciojusto.bo", "puesto1234");
    fireEvent.click(await screen.findByRole("tab", { name: "Mis ofertas" }));
    fireEvent.click(await screen.findByRole("button", { name: /Combo de 2 o 3 productos/ }));
    const form = screen.getByRole("form", { name: "Publicar un combo" });
    fireEvent.change(within(form).getByLabelText("Nombre del combo"), { target: { value: "Solo tomate" } });
    fireEvent.change(within(form).getByLabelText("Producto 1"), { target: { value: "tomate" } });
    fireEvent.change(within(form).getAllByLabelText("Precio de oferta (Bs)")[0]!, { target: { value: "1" } });
    fireEvent.submit(form);
    expect(await screen.findByText(/de 2 a 3 productos/)).toBeDefined();
  });
});
