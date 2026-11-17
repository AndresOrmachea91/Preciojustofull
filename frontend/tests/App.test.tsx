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
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import App from "@/ui/App";
import { elegirProducto } from "./ayudas";

afterEach(cleanup);

describe("App sobre React 19", () => {
  it("monta la comparativa y marca el mercado más conveniente", async () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "PrecioJusto" })).toBeDefined();

    await waitFor(() => {
      expect(document.querySelector(".tarjeta")?.textContent).toContain("Mercado Villa Fátima");
    });

    // La respuesta corta va junto al mapa: los lugares medidos, del más barato al más caro.
    expect(screen.getByRole("heading", { name: "Dónde está más barato" })).toBeDefined();
    expect(document.querySelector(".baratos__lugar")?.textContent).toContain("Mercado Villa Fátima");

    // El adaptador en memoria devuelve el tomate más barato en Villa Fátima.
    // Cinco de consumidor final y un mayorista aparte, que no compite.
    const tarjetas = document.querySelectorAll(".tarjeta");
    expect(tarjetas.length).toBe(6);
    expect(tarjetas[0].textContent).toContain("Mercado Villa Fátima");
    expect(tarjetas[0].className).toContain("tarjeta--destacada");
    expect(screen.getByText("Más conveniente")).toBeDefined();
    expect(screen.getByRole("heading", { name: "Precio mayorista" })).toBeDefined();
    expect(tarjetas[5].textContent).toContain("Distribuidora Central");
  });

  it("cambia de producto sin que el componente conozca el origen de datos", async () => {
    render(<App />);

    await waitFor(() => expect(document.querySelector(".tarjeta")?.textContent).toContain("Mercado Villa Fátima"));

    await elegirProducto("Arroz de primera");

    await waitFor(() => {
      const tarjetas = document.querySelectorAll(".tarjeta");
      expect(tarjetas.length).toBe(5);
      expect(tarjetas[0].textContent).toContain("Mercado Rodríguez");
    });
  });

  it("muestra siempre el nivel de confianza de cada precio", async () => {
    render(<App />);

    await waitFor(() => {
      expect(document.querySelectorAll(".tarjeta .confianza").length).toBe(6);
    });
    expect(screen.getAllByText("Verificado en campo").length).toBeGreaterThan(0);
  });

  it("todo precio dice si es observado o estimado, de un vistazo", async () => {
    render(<App />);
    await waitFor(() => expect(document.querySelectorAll(".tarjeta").length).toBe(6));

    const tarjetas = [...document.querySelectorAll(".tarjeta")];
    expect(tarjetas.every((t) => t.querySelector(".procedencia") !== null)).toBe(true);
    const estimadas = tarjetas.filter((t) => t.getAttribute("data-procedencia") === "estimado");
    expect(estimadas.length).toBe(2);   // San Pedro y la distribuidora: nadie midió ahí
    expect(estimadas[0].textContent).toContain("Todavía nadie verificó este precio");
    // El resumen al lado del mapa cuenta lo mismo: de 6 lugares, 2 sin medir.
    expect(screen.getByLabelText("4 de 6 lugares con precio medido")).toBeDefined();
  });
});
