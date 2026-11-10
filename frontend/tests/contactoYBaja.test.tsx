/**
 * @vitest-environment jsdom
 *
 * C146: el proveedor deja su teléfono para que lo llamen o le escriban por
 * WhatsApp, y el administrador puede dar de baja cualquier oferta vigente.
 */
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { enlaceLlamar, enlaceWhatsapp, type Puesto } from "@/dominio/modelo";
import App from "@/ui/App";
import { ContactoPuesto } from "@/ui/componentes/ContactoPuesto";

beforeEach(() => {
  window.location.hash = "";
});
afterEach(cleanup);

const local: Puesto = {
  id: 9, codigoMercado: "distribuidora_el_sol", numero: "LOCAL", nombre: "Distribuidora El Sol", rubros: [],
  referencia: "", registrado: true, foto: null, esLocal: true, celular: "71234567",
};

describe("contacto del proveedor", () => {
  it("arma los enlaces para llamar y para WhatsApp (solo celular)", () => {
    expect(enlaceLlamar("71234567")).toBe("tel:+59171234567");
    expect(enlaceWhatsapp("71234567")).toBe("https://wa.me/59171234567");
    expect(enlaceWhatsapp("2234567")).toBeNull(); // un fijo no tiene WhatsApp
  });

  it("muestra los botones si hay teléfono, y nada si no", () => {
    const { container, rerender } = render(<ContactoPuesto puesto={local} />);
    expect(screen.getByRole("link", { name: /Llamar 71234567/ }).getAttribute("href")).toBe("tel:+59171234567");
    expect(screen.getByRole("link", { name: "WhatsApp" }).getAttribute("href")).toContain("wa.me/59171234567");
    rerender(<ContactoPuesto puesto={{ ...local, celular: null }} />);
    expect(container.textContent).toBe("");
  });
});

async function ingresar(correo: string, contrasena: string) {
  fireEvent.click(await screen.findByRole("link", { name: "Ingresar" }));
  fireEvent.change(screen.getByLabelText(/^Correo/), { target: { value: correo } });
  fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: contrasena } });
  fireEvent.submit(screen.getByRole("button", { name: "Ingresar" }).closest("form")!);
  await screen.findByRole("button", { name: "Salir" });
}

describe("el administrador y las ofertas vigentes", () => {
  it("da de baja una oferta activa y deja de mostrarse", async () => {
    render(<App />);
    await ingresar("admin@preciojusto.bo", "admin1234");
    fireEvent.click(within(screen.getByRole("navigation", { name: "Secciones" })).getByRole("link", { name: "Administración" }));
    fireEvent.click(await screen.findByRole("tab", { name: "Ofertas" }));
    const tabla = await screen.findByRole("table", { name: "Ofertas vigentes" });
    const fila = within(tabla).getByText(/Arroz de primera/).closest("tr")!;
    fireEvent.click(within(fila).getByRole("button", { name: "Dar de baja" }));
    expect(await screen.findByText(/Dada de baja: Arroz de primera/)).toBeDefined();
    expect(within(await screen.findByRole("table", { name: "Ofertas vigentes" })).queryByText(/Arroz de primera/)).toBeNull();
  });
});
