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
  fireEvent.change(screen.getByLabelText(/^Correo/), { target: { value: "vendedora@preciojusto.bo" } });
  fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: "puesto1234" } });
  fireEvent.submit(screen.getByRole("button", { name: "Ingresar" }).closest("form")!);
  await screen.findByRole("button", { name: "Salir" });
}

describe("nombres del puesto", () => {
  const puesto: Puesto = {
    id: 1, codigoMercado: "rodriguez", numero: "14", nombre: "Verduras Rosa", rubros: [], referencia: "",
    registrado: true, foto: null, esLocal: false, celular: null,
  };
  it("un puesto se nombra por su número; el local de una distribuidora, por su nombre", () => {
    expect(nombreDelPuesto(puesto)).toBe("Puesto 14 · Verduras Rosa");
    expect(nombreDelPuesto({ ...puesto, numero: "LOCAL", nombre: "Distribuidora El Sol", esLocal: true })).toBe("Distribuidora El Sol");
    const rodriguez = { codigo: "rodriguez", nombre: "Mercado Rodríguez" } as Parameters<typeof dondeEsta>[0];
    expect(dondeEsta(rodriguez, puesto)).toBe("Mercado Rodríguez · Puesto 14");
  });
});

describe("el inventario del casero", () => {
  it("abre en el inventario con cuánto le queda, vende en un toque y agrega un producto con su cantidad", async () => {
    await ingresarComoVendedora();
    // Arriba, cómo está el puesto hoy (C148).
    expect(await screen.findByRole("heading", { name: "Su puesto hoy" })).toBeDefined();
    const lista = await screen.findByRole("list", { name: "Mi inventario" });
    const tomate = within(lista).getByText("Tomate").closest("li")!;
    expect(within(tomate).getByText("24 kilos")).toBeDefined();
    fireEvent.click(within(tomate).getByRole("button", { name: "Vendí 1" }));
    expect(await within(tomate).findByText("23 kilos")).toBeDefined();
    // La papa quedaba en 2 arrobas con aviso en 3: el estado sale solo.
    const papa = within(lista).getByText("Papa holandesa").closest("li")!;
    expect(within(papa).getByText("Queda poco")).toBeDefined();

    const form = screen.getByRole("form", { name: "Agregar un producto" });
    await elegirProducto("Arroz de primera", "Producto", form);
    fireEvent.change(within(form).getByLabelText("Precio (Bs)"), { target: { value: "8,50" } });
    fireEvent.change(within(form).getByLabelText(/¿Cuánto tiene\?/), { target: { value: "30" } });
    fireEvent.submit(form);
    expect(await screen.findByText(/Agregado: Arroz de primera a Bs 8,50 por kilo/)).toBeDefined();
    const arroz = within(lista).getByText("Arroz de primera").closest("li")!;
    expect(within(arroz).getByText("30 kilos")).toBeDefined();
  });

  it("sin cantidad, sigue el «hay / queda poco / se acabó» y se puede anotar cuánto queda", async () => {
    await ingresarComoVendedora();
    const form = await screen.findByRole("form", { name: "Agregar un producto" });
    await elegirProducto("Arroz de primera", "Producto", form);
    fireEvent.change(within(form).getByLabelText("Precio (Bs)"), { target: { value: "8" } });
    fireEvent.submit(form);
    const lista = await screen.findByRole("list", { name: "Mi inventario" });
    const arroz = (await within(lista).findByText("Arroz de primera")).closest("li")!;
    const grupo = within(arroz).getByRole("group", { name: "¿Le queda Arroz de primera?" });
    fireEvent.click(within(grupo).getByRole("button", { name: "Se acabó" }));
    expect(await within(grupo).findByRole("button", { name: "Se acabó", pressed: true })).toBeDefined();
    fireEvent.click(within(arroz).getByRole("button", { name: "Anotar cuánto me queda" }));
    fireEvent.change(within(arroz).getByLabelText(/¿Cuánto le queda\?/), { target: { value: "12" } });
    fireEvent.submit(within(arroz).getByLabelText(/¿Cuánto le queda\?/).closest("form")!);
    expect(await within(arroz).findByText("12 kilos")).toBeDefined();
  });

  it("tocar el precio deja cambiarlo", async () => {
    await ingresarComoVendedora();
    const lista = await screen.findByRole("list", { name: "Mi inventario" });
    fireEvent.click(within(lista).getByRole("button", { name: /Precio de Tomate/ }));
    const caja = within(lista).getByLabelText("Nuevo precio de Tomate");
    fireEvent.change(caja, { target: { value: "11" } });
    fireEvent.submit(caja.closest("form")!);
    expect(await screen.findByText("Tomate: ahora a Bs 11,00 por kilo.")).toBeDefined();
  });
});

describe("la ventana del mercado en el mapa", () => {
  async function marcador(codigo: string) {
    const memoria = new PreciosMemoria();
    const { marcadores } = await new VerMapa(memoria, memoria).ejecutar("tomate");
    return marcadores.find((m) => m.mercado.codigo === codigo)!;
  }

  it("muestra el mercado en miniatura con sus puestos y cuántos tienen el producto", async () => {
    render(<VentanaMercado contenedor={crearContenedor("memoria")} marcador={await marcador("rodriguez")} producto={TOMATE} />);
    expect(await screen.findByText(/2 puestos · 1 con tomate/)).toBeDefined();
    const puesto = screen.getByRole("button", { name: /^Puesto 14 · Verduras Doña Rosa/ });
    fireEvent.click(puesto);
    expect(window.location.hash).toBe("#/mercado?codigo=rodriguez&puesto=14");
    expect(screen.getByRole("link", { name: /Entrar al mercado: sus puestos y precios/ })).toBeDefined();
  });

  it("sin puestos, invita al casero a registrarse", async () => {
    render(<VentanaMercado contenedor={crearContenedor("memoria")} marcador={await marcador("villafatima")} producto={TOMATE} />);
    expect(await screen.findByRole("link", { name: /¿Vende aquí\? Regístrese gratis/ })).toBeDefined();
  });
});

describe("la vitrina del casero", () => {
  it("el enlace compartido abre los puestos del mercado con el suyo resaltado", async () => {
    window.location.hash = "#/mercado?codigo=rodriguez&puesto=14";
    render(<App />);
    const detalle = await screen.findByRole("article", { name: "Detalle de Puesto 14 · Verduras Doña Rosa" });
    expect(within(detalle).getByText(/Le quedan 24 kilos/)).toBeDefined();
    expect(screen.getByRole("button", { name: /^Puesto 14 · Verduras Doña Rosa/, pressed: true })).toBeDefined();
    expect(screen.getByRole("tab", { name: /El mercado/, selected: true })).toBeDefined();
  });

  it("en Mi negocio aparece para compartir por WhatsApp", async () => {
    await ingresarComoVendedora();
    fireEvent.click(await screen.findByRole("tab", { name: "Mi negocio" }));
    const whatsapp = await screen.findByRole("link", { name: /Mandar por WhatsApp/ });
    expect(decodeURIComponent(whatsapp.getAttribute("href") ?? "")).toContain("#/mercado?codigo=rodriguez&puesto=14");
  });
});
