/**
 * @vitest-environment jsdom
 *
 * Catálogo del administrador y presentaciones de venta, sobre los
 * adaptadores en memoria. El mapa de Leaflet no se dibuja en jsdom: la
 * ubicación se carga por los campos de latitud y longitud, que es el mismo
 * estado que llena el clic en el mapa.
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { precioEnPresentacion, type Precio } from "@/dominio/modelo";
import { ClienteHttp } from "@/infraestructura/http/clienteHttp";
import { CatalogoAdminApi } from "@/infraestructura/http/CatalogoAdminApi";
import { ADMIN_DEMO } from "@/infraestructura/memoria/CuentasMemoria";
import App from "@/ui/App";

beforeEach(() => {
  window.location.hash = "";
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function ingresarComoAdmin() {
  render(<App />);
  fireEvent.click(await screen.findByRole("link", { name: "Ingresar" }));
  fireEvent.change(screen.getByLabelText("Correo"), { target: { value: ADMIN_DEMO.correo } });
  fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: ADMIN_DEMO.contrasena } });
  fireEvent.submit(screen.getByRole("button", { name: "Ingresar" }).closest("form")!);
  await screen.findByRole("tab", { name: "Mercados y distribuidores" });
}

describe("presentaciones", () => {
  it("el mismo precio por quintal es 46 veces el del kilo, con la misma procedencia", () => {
    const porKilo: Precio = {
      codigoProducto: "arroz", codigoMercado: "rodriguez", periodo: "2026-10",
      rango: { minimo: 8, maximo: 9, centro: 8.5 }, unidad: "kg", confianza: "alto",
      procedencia: "observado", observacionesUsadas: 3, fechaObservacionMasReciente: null, conflictos: [], voces: {}, factorMercado: null, antiguedadDias: null, motivosRango: [],
    };
    const porQuintal = precioEnPresentacion(porKilo, { codigo: "quintal", nombre: "Quintal", factor: 46 });
    expect(porQuintal.rango).toEqual({ minimo: 368, maximo: 414, centro: 391 });
    expect(porQuintal.unidad).toBe("quintal");
    expect(porQuintal.procedencia).toBe("observado");
  });

  it("un precio por unidad no se convierte a arroba: habría que inventar el peso", () => {
    const porUnidad = {
      codigoProducto: "limon", codigoMercado: "x", periodo: "2026-09",
      rango: { minimo: 0.7, maximo: 0.7, centro: 0.7 }, unidad: "u", confianza: "alto" as const,
      procedencia: "estimado" as const, observacionesUsadas: 1, fechaObservacionMasReciente: null, conflictos: [], voces: {}, factorMercado: null, antiguedadDias: null, motivosRango: [],
    };
    const arroba = { codigo: "arroba", nombre: "Arroba", factor: 11.5 };
    expect(precioEnPresentacion(porUnidad, arroba)).toBe(porUnidad);
    const docena = precioEnPresentacion(porUnidad, { codigo: "docena", nombre: "Docena", factor: 12 });
    expect(docena.rango.centro).toBeCloseTo(8.4);
  });

  it("muestra la evolución del precio con su tabla, y la lleva a la presentación elegida", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Cómo cambió el precio en La Paz" })).toBeDefined();
    const tabla = screen.getByRole("table", { name: "Precio por mes" });
    const filas = within(tabla).getAllByRole("row");
    expect(filas).toHaveLength(13); // encabezado + 12 meses
    const porKilo = Number(filas[1].textContent!.match(/Bs ([\d.]+)/)![1]);

    fireEvent.click(within(screen.getByRole("group", { name: "Ver el precio por" })).getByRole("button", { name: "Arroba" }));
    await waitFor(() => {
      const ahora = within(screen.getByRole("table", { name: "Precio por mes" })).getAllByRole("row")[1];
      expect(Number(ahora.textContent!.match(/Bs ([\d.]+)/)![1])).toBeCloseTo(porKilo * 11.5, 1);
    });
    expect(screen.getByRole("img", { name: "Precio por arroba, mes a mes" })).toBeDefined();
  });

  it("el usuario puede ver los precios por arroba", async () => {
    render(<App />);
    const grupo = await screen.findByRole("group", { name: "Ver el precio por" });
    fireEvent.click(within(grupo).getByRole("button", { name: "Arroba" }));
    await waitFor(() => expect(screen.getAllByText(/por arroba/).length).toBeGreaterThan(0));
  });
});

describe("catálogo del administrador", () => {
  it("crea una distribuidora con su ubicación y la ve en la lista", async () => {
    await ingresarComoAdmin();
    fireEvent.click(screen.getByRole("tab", { name: "Mercados y distribuidores" }));
    fireEvent.click(await screen.findByRole("button", { name: "Nuevo punto de venta" }));

    const form = screen.getByRole("form", { name: "Nuevo punto de venta" });
    fireEvent.change(within(form).getByLabelText("Nombre"), { target: { value: "Distribuidora Doña Rosa" } });
    fireEvent.change(within(form).getByLabelText("Tipo"), { target: { value: "distribuidor" } });
    fireEvent.change(within(form).getByLabelText("Latitud"), { target: { value: "-16.51" } });
    fireEvent.change(within(form).getByLabelText("Longitud"), { target: { value: "-68.13" } });
    fireEvent.submit(form);

    expect(await screen.findByRole("status")).toHaveProperty("textContent", "Distribuidora Doña Rosa quedó guardado.");
    expect(within(screen.getByRole("table", { name: "Puntos de venta" })).getByText("Distribuidora Doña Rosa")).toBeDefined();
  });

  it("una ubicación fuera de La Paz no se guarda", async () => {
    await ingresarComoAdmin();
    fireEvent.click(screen.getByRole("tab", { name: "Mercados y distribuidores" }));
    fireEvent.click(await screen.findByRole("button", { name: "Nuevo punto de venta" }));
    const form = screen.getByRole("form", { name: "Nuevo punto de venta" });
    fireEvent.change(within(form).getByLabelText("Nombre"), { target: { value: "Mal ubicado" } });
    fireEvent.change(within(form).getByLabelText("Latitud"), { target: { value: "16.51" } });
    fireEvent.change(within(form).getByLabelText("Longitud"), { target: { value: "-68.13" } });
    fireEvent.submit(form);
    expect((await within(form).findByRole("alert")).textContent).toMatch(/La Paz o El Alto/);
  });

  it("no deja eliminar un mercado que tiene sectores", async () => {
    await ingresarComoAdmin();
    fireEvent.click(screen.getByRole("tab", { name: "Mercados y distribuidores" }));
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar Mercado Rodríguez" }));
    fireEvent.click(screen.getByRole("button", { name: "Sí, eliminar" }));
    expect((await screen.findByRole("alert")).textContent).toMatch(/tiene sectores/);
  });

  it("crea un producto que se vende por unidad y por maple", async () => {
    await ingresarComoAdmin();
    fireEvent.click(screen.getByRole("tab", { name: "Productos" }));
    fireEvent.click(await screen.findByRole("button", { name: "Nuevo producto" }));
    const form = screen.getByRole("form", { name: "Nuevo producto" });
    fireEvent.change(within(form).getByLabelText("Nombre"), { target: { value: "Huevo de granja" } });
    fireEvent.change(within(form).getByLabelText("Se mide en"), { target: { value: "u" } });
    fireEvent.click(within(form).getByLabelText(/Docena/));   // se queda con unidad y maple
    fireEvent.submit(form);

    const tabla = await screen.findByRole("table", { name: "Productos" });
    await waitFor(() => expect(within(tabla).getByText("Huevo de granja")).toBeDefined());
    expect(within(tabla).getByText("Unidad, Maple (30)")).toBeDefined();
  });
});

describe("CatalogoAdminApi", () => {
  it("manda el producto en snake_case y entiende el 204 al eliminar", async () => {
    const pedidos: { url: string; init: RequestInit }[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL, init: RequestInit = {}) => {
        pedidos.push({ url: String(url), init });
        if (init.method === "DELETE") return new Response(null, { status: 204 });
        return new Response(
          JSON.stringify({
            codigo: "huevo", nombre: "Huevo", categoria: "otro", es_perecedero: false, unidad_base: "u",
            dias_conservacion: 20, presentaciones: [{ codigo: "unidad", nombre: "Unidad", factor: 1 }],
          }),
          { status: 201 },
        );
      }),
    );
    const api = new CatalogoAdminApi(new ClienteHttp("http://api.test/api/v1"));
    const p = await api.crearProducto({
      nombre: "Huevo", categoria: "otro", unidadBase: "u", presentaciones: ["unidad"], diasConservacion: 20,
    });
    expect(p).toMatchObject({ codigo: "huevo", unidadBase: "u", diasConservacion: 20 });
    expect(JSON.parse(String(pedidos[0].init.body))).toMatchObject({ unidad_base: "u", dias_conservacion: 20 });

    await expect(api.eliminarPuntoVenta("lanza")).resolves.toBeUndefined();
    expect(pedidos[1].url).toBe("http://api.test/api/v1/admin/mercados/lanza");
  });
});
