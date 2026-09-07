/**
 * @vitest-environment jsdom
 *
 * Prueba de humo de la interfaz sobre React 19.
 *
 * No verifica estilos ni maquetación: verifica que el árbol de React se
 * monta con el runtime nuevo (createRoot bajo StrictMode, que en React 19
 * vuelve a ejecutar los efectos en desarrollo) y que el camino completo
 * componente -> caso de uso -> puerto -> adaptador sigue entregando datos.
 * Si la actualización hubiera roto el render, esta prueba lo detecta.
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import App from "@/ui/App";

afterEach(cleanup);

describe("App sobre React 19", () => {
  it("monta la comparativa y marca el mercado más conveniente", async () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "PrecioJusto" })).toBeDefined();

    await waitFor(() => {
      expect(screen.getByText("Mercado Villa Fátima")).toBeDefined();
    });

    // El adaptador en memoria devuelve el tomate más barato en Villa Fátima.
    const tarjetas = document.querySelectorAll(".tarjeta");
    expect(tarjetas.length).toBe(4);
    expect(tarjetas[0].textContent).toContain("Mercado Villa Fátima");
    expect(tarjetas[0].className).toContain("tarjeta--destacada");
    expect(screen.getByText("Más conveniente")).toBeDefined();
  });

  it("cambia de producto sin que el componente conozca el origen de datos", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByText("Mercado Villa Fátima")).toBeDefined());

    fireEvent.click(screen.getByRole("button", { name: "Arroz de primera" }));

    await waitFor(() => {
      const tarjetas = document.querySelectorAll(".tarjeta");
      expect(tarjetas.length).toBe(3);
      expect(tarjetas[0].textContent).toContain("Mercado Rodríguez");
    });
  });

  it("muestra siempre el nivel de confianza de cada precio", async () => {
    render(<App />);

    await waitFor(() => {
      expect(document.querySelectorAll(".confianza").length).toBe(4);
    });
    expect(screen.getAllByText("Verificado en campo").length).toBeGreaterThan(0);
  });
});
