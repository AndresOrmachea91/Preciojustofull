/**
 * @vitest-environment jsdom
 *
 * Lo que hacen el usuario (listas, reportes) y el vendedor (precios de su
 * puesto) sobre la interfaz, con los adaptadores en memoria.
 */
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import App from "@/ui/App";
import { elegirProducto } from "./ayudas";

beforeEach(() => {
  window.location.hash = "";
});
afterEach(cleanup);

async function ingresar(correo: string, contrasena: string) {
  render(<App />);
  fireEvent.click(await screen.findByRole("link", { name: "Ingresar" }));
  fireEvent.change(screen.getByLabelText("Correo"), { target: { value: correo } });
  fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: contrasena } });
  fireEvent.submit(screen.getByRole("button", { name: "Ingresar" }).closest("form")!);
  await screen.findByRole("button", { name: "Salir" });
}

describe("usuario", () => {
  it("arma una lista en arrobas y ve dónde le conviene comprarla", async () => {
    await ingresar("vecino@correo.bo", "vecino1234");
    fireEvent.click(screen.getByRole("link", { name: "Mis listas y reportes" }));
    fireEvent.click(await screen.findByRole("button", { name: "Nueva lista" }));

    const form = screen.getByRole("form", { name: "Nueva lista" });
    fireEvent.change(within(form).getByLabelText("Nombre de la lista"), { target: { value: "Compra del mes" } });
    await elegirProducto("Papa holandesa", "Agregar un producto", form);
    fireEvent.change(within(form).getByLabelText("Cantidad de Papa holandesa"), { target: { value: "2" } });
    fireEvent.change(within(form).getByLabelText("Presentación de Papa holandesa"), { target: { value: "arroba" } });
    fireEvent.submit(form);

    const tarjeta = await screen.findByRole("article", { name: "Lista Compra del mes" });
    expect(within(tarjeta).getByText("2 arrobas de Papa holandesa")).toBeDefined();

    fireEvent.click(within(tarjeta).getByRole("button", { name: "¿Dónde conviene?" }));
    const cotizacion = await within(tarjeta).findByLabelText("Dónde conviene comprar esta lista");
    // 2 arrobas = 23 kg: el más barato de la memoria es Villa Fátima (6,78 Bs/kg).
    expect(within(cotizacion).getAllByRole("listitem")[0].textContent).toMatch(/Mercado Villa Fátima.*Bs 155\.94/);
    // El mayorista va aparte: no compite con los precios de consumidor final.
    const mayorista = within(cotizacion).getByRole("list", { name: "Precio mayorista de esta lista" });
    expect(within(mayorista).getByText("Makro")).toBeDefined();
  });

  it("reporta un precio y lo ve pendiente en sus reportes", async () => {
    await ingresar("vecino@correo.bo", "vecino1234");
    fireEvent.click(screen.getByRole("link", { name: "Mis listas y reportes" }));
    fireEvent.click(screen.getByRole("tab", { name: "Reportar un precio" }));

    const form = screen.getByRole("form", { name: "Reportar un precio" });
    await elegirProducto("Tomate", "Producto", form);
    fireEvent.change(within(form).getByLabelText("Dónde lo vio"), { target: { value: "lanza" } });
    fireEvent.change(within(form).getByLabelText("Precio (Bs)"), { target: { value: "7.5" } });
    fireEvent.change(within(form).getByLabelText("Por"), { target: { value: "libra" } });
    fireEvent.submit(form);

    // El más nuevo va primero (el vecino de la demo ya tenía un reporte de tomate).
    const [reporte] = await screen.findAllByRole("article", { name: "Reporte de Tomate" });
    expect(within(reporte).getByText("Esperando revisión")).toBeDefined();
    expect(reporte.textContent).toMatch(/Bs 7\.50 por libra/);
  });

  it("un usuario común no ve «Mi puesto»", async () => {
    await ingresar("vecino@correo.bo", "vecino1234");
    expect(screen.queryByRole("link", { name: "Mi puesto" })).toBeNull();
  });
});

describe("vendedor", () => {
  it("entra directo a su puesto, publica un precio y lo ve con su equivalencia por kilo", async () => {
    await ingresar("vendedora@preciojusto.bo", "puesto1234");
    expect(await screen.findByRole("heading", { name: /Mi puesto/ })).toBeDefined();

    const form = screen.getByRole("form", { name: "Publicar un precio" });
    await elegirProducto("Papa holandesa", "Producto", form);
    fireEvent.change(within(form).getByLabelText("Por"), { target: { value: "arroba" } });
    fireEvent.change(within(form).getByLabelText("Precio (Bs)"), { target: { value: "80" } });
    fireEvent.submit(form);

    const tabla = await screen.findByRole("table", { name: "Mis precios publicados" });
    const fila = within(tabla).getByText("Papa holandesa").closest("tr")!;
    expect(fila.textContent).toMatch(/Bs 80\.00 por arroba/);
    expect(fila.textContent).toMatch(/Bs 6\.96 por kilo/);   // 80 / 11,5
  });
});
