/**
 * @vitest-environment jsdom
 *
 * La barra lateral (secciones y cuenta a la izquierda) y la caja de búsqueda
 * de productos que reemplazó a la fila de botones.
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Producto } from "@/dominio/modelo";
import { PRESENTACIONES_POR_UNIDAD } from "@/dominio/modelo";
import App from "@/ui/App";
import { SelectorProducto } from "@/ui/componentes/SelectorProducto";

beforeEach(() => {
  window.location.hash = "";
});
afterEach(cleanup);

const producto = (codigo: string, nombre: string, categoria: string): Producto => ({
  codigo, nombre, categoria, esPerecedero: true, unidadBase: "kg", diasConservacion: 5,
  presentaciones: PRESENTACIONES_POR_UNIDAD.kg,
});
const PRODUCTOS = [
  producto("papa", "Papa holandesa", "tuberculo"),
  producto("platano", "Plátano", "fruta"),
  producto("tomate", "Tomate", "hortaliza"),
];

describe("barra lateral", () => {
  it("la página de confiabilidad es pública y explica qué se compara", async () => {
    render(<App />);
    const secciones = await screen.findByRole("navigation", { name: "Secciones" });
    fireEvent.click(within(secciones).getByRole("link", { name: "¿Qué tan confiable es?" }));
    expect(await screen.findByRole("heading", { name: "¿Qué tan confiable es el estimado?" })).toBeDefined();
    // En el modo demo no hay mediciones de campo: lo dice, no inventa un error.
    expect(await screen.findByText(/Todavía no hay precios medidos/)).toBeDefined();
  });

  it("sin sesión ofrece ingresar y crear cuenta, cada una con su formulario", async () => {
    render(<App />);
    const cuenta = await screen.findByRole("navigation", { name: "Cuenta" });

    fireEvent.click(within(cuenta).getByRole("link", { name: "Crear cuenta" }));
    expect(screen.getByRole("heading", { name: "Crear una cuenta" })).toBeDefined();
    expect(within(cuenta).getByRole("link", { name: "Crear cuenta" }).getAttribute("aria-current")).toBe("page");

    fireEvent.click(within(cuenta).getByRole("link", { name: "Ingresar" }));
    expect(screen.getByRole("heading", { name: "Ingresar" })).toBeDefined();
    expect(window.location.hash).toBe("#/ingresar");
  });
});

describe("caja de búsqueda de productos", () => {
  it("encuentra sin importar tildes ni mayúsculas y agrupa por categoría", () => {
    render(<SelectorProducto productos={PRODUCTOS} valor={null} onElegir={() => {}} etiqueta="Producto" />);
    const caja = screen.getByRole("combobox", { name: "Producto" });

    fireEvent.focus(caja);
    expect(screen.getAllByRole("option")).toHaveLength(3);
    expect(screen.getByText("Tubérculo")).toBeDefined();

    fireEvent.change(caja, { target: { value: "PLATANO" } });
    expect(screen.getAllByRole("option").map((o) => o.textContent)).toEqual(["Plátano"]);

    fireEvent.change(caja, { target: { value: "zzz" } });
    expect(screen.getByText("Ningún producto coincide.")).toBeDefined();
  });

  it("se elige con el teclado y Enter no envía el formulario", () => {
    const onElegir = vi.fn();
    const enviar = vi.fn((e: Event) => e.preventDefault());
    render(
      <form onSubmit={(e) => enviar(e.nativeEvent)}>
        <SelectorProducto productos={PRODUCTOS} valor={null} onElegir={onElegir} etiqueta="Producto" />
      </form>,
    );
    const caja = screen.getByRole("combobox", { name: "Producto" });
    fireEvent.focus(caja);
    fireEvent.keyDown(caja, { key: "ArrowDown" });
    fireEvent.keyDown(caja, { key: "Enter" });

    // Orden: Fruta, Hortaliza, Tubérculo. La flecha baja del primero al segundo.
    expect(onElegir).toHaveBeenCalledWith("tomate");
    expect(enviar).not.toHaveBeenCalled();
    expect(screen.queryByRole("listbox")).toBeNull();
  });

  it("muestra el elegido y lo marca en la lista", async () => {
    render(<SelectorProducto productos={PRODUCTOS} valor="papa" onElegir={() => {}} etiqueta="Producto" />);
    const caja = screen.getByRole("combobox", { name: "Producto" }) as HTMLInputElement;
    expect(caja.value).toBe("Papa holandesa");
    fireEvent.focus(caja);
    await waitFor(() =>
      expect(screen.getByRole("option", { name: "Papa holandesa" }).getAttribute("aria-selected")).toBe("true"),
    );
  });
});
