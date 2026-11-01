/**
 * @vitest-environment jsdom
 *
 * C137: el casero maneja su inventario a un toque y elige su mercado; en el
 * mapa, la ventana de un mercado muestra sus puestos con lo que tiene cada
 * uno (no todos venden lo mismo).
 */
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { VerMapa } from "@/aplicacion/casosUso/publico/verMapa";
import { PRESENTACIONES_POR_UNIDAD, dondeEsta, nombreDelPuesto, type Producto, type Puesto } from "@/dominio/modelo";
import { crearContenedor } from "@/infraestructura/contenedor";
import { PreciosMemoria } from "@/infraestructura/memoria/PreciosMemoria";
import App from "@/ui/App";
import { VentanaMercado } from "@/ui/componentes/VentanaMercado";
import { elegirProducto } from "./ayudas";

beforeEach(() => {
  window.location.hash = "";
});
afterEach(cleanup);

const TOMATE: Producto = {
  codigo: "tomate", nombre: "Tomate", categoria: "hortaliza", esPerecedero: true, unidadBase: "kg",
  diasConservacion: 5, presentaciones: PRESENTACIONES_POR_UNIDAD.kg,
};

async function ingresarComoVendedora() {
  render(<App />);
  fireEvent.click(await screen.findByRole("link", { name: "Ingresar" }));
  fireEvent.change(screen.getByLabelText("Correo"), { target: { value: "vendedora@preciojusto.bo" } });
  fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: "puesto1234" } });
  fireEvent.submit(screen.getByRole("button", { name: "Ingresar" }).closest("form")!);
  await screen.findByRole("button", { name: "Salir" });
}

describe("nombres del puesto", () => {
  const puesto: Puesto = {
    id: 1, codigoMercado: "rodriguez", numero: "14", nombre: "Verduras Rosa", rubros: [], referencia: "",
    registrado: true, foto: null, esLocal: false,
  };
  it("un puesto se nombra por su número; el local de una distribuidora, por su nombre", () => {
    expect(nombreDelPuesto(puesto)).toBe("Puesto 14 · Verduras Rosa");
    expect(nombreDelPuesto({ ...puesto, numero: "LOCAL", nombre: "Distribuidora El Sol", esLocal: true })).toBe("Distribuidora El Sol");
    const rodriguez = { codigo: "rodriguez", nombre: "Mercado Rodríguez" } as Parameters<typeof dondeEsta>[0];
    expect(dondeEsta(rodriguez, puesto)).toBe("Mercado Rodríguez · Puesto 14");
  });
});

describe("el inventario del casero", () => {
  it("abre en el inventario, cambia la disponibilidad en un toque y agrega un producto", async () => {
    await ingresarComoVendedora();
    const lista = await screen.findByRole("list", { name: "Mi inventario" });
    const tomate = within(lista).getByText("Tomate").closest("li")!;
    const grupo = within(tomate).getByRole("group", { name: "¿Le queda Tomate?" });
    fireEvent.click(within(grupo).getByRole("button", { name: "Se acabó" }));
    expect(await within(grupo).findByRole("button", { name: "Se acabó", pressed: true })).toBeDefined();

    const form = screen.getByRole("form", { name: "Agregar un producto" });
    await elegirProducto("Arroz de primera", "Producto", form);
    fireEvent.change(within(form).getByLabelText("Precio (Bs)"), { target: { value: "8,50" } });
    fireEvent.submit(form);
    expect(await screen.findByText(/Agregado: Arroz de primera a Bs 8,50 por kilo/)).toBeDefined();
  });

  it("tocar el precio deja cambiarlo", async () => {
    await ingresarComoVendedora();
    const lista = await screen.findByRole("list", { name: "Mi inventario" });
    fireEvent.click(within(lista).getByRole("button", { name: /Precio de Tomate/ }));
    const caja = within(lista).getByLabelText("Nuevo precio de Tomate");
    fireEvent.change(caja, { target: { value: "11" } });
    fireEvent.submit(caja.closest("form")!);
    expect(await screen.findByText("Tomate: Bs 11,00 por kilo.")).toBeDefined();
  });
});

describe("la ventana del mercado en el mapa", () => {
  async function marcador(codigo: string) {
    const memoria = new PreciosMemoria();
    const { marcadores } = await new VerMapa(memoria, memoria).ejecutar("tomate");
    return marcadores.find((m) => m.mercado.codigo === codigo)!;
  }

  it("muestra los puestos con sus precios; primero el que tiene el producto buscado", async () => {
    render(<VentanaMercado contenedor={crearContenedor("memoria")} marcador={await marcador("rodriguez")} producto={TOMATE} />);
    const puestos = await screen.findAllByText(/^Puesto \d+/);
    expect(puestos[0].textContent).toBe("Puesto 14 · Verduras Doña Rosa");
    expect(screen.getByText("Queda poco")).toBeDefined();   // la papa del 14
    expect(screen.getByRole("link", { name: /Entrar: todos los precios y puestos/ })).toBeDefined();
  });

  it("sin puestos, invita al casero a registrarse", async () => {
    render(<VentanaMercado contenedor={crearContenedor("memoria")} marcador={await marcador("villafatima")} producto={TOMATE} />);
    expect(await screen.findByRole("link", { name: /¿Vende aquí\? Regístrese gratis/ })).toBeDefined();
  });
});
