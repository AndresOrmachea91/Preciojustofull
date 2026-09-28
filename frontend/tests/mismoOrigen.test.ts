/**
 * @vitest-environment jsdom
 *
 * Cuando el backend sirve la interfaz construida, todo vive en el mismo
 * origen y la base de la API es una ruta relativa ("/api/v1"). Esta prueba
 * fija ese caso: sin ella, el día que alguien sirva la demo en otro puerto
 * o desde otra máquina, el frontend seguiría pidiendo a localhost:8000.
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { ClienteHttp } from "@/infraestructura/http/clienteHttp";
import { crearContenedor } from "@/infraestructura/contenedor";

afterEach(() => vi.unstubAllGlobals());

function espiarFetch() {
  const pedidos: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (entrada: RequestInfo | URL) => {
      pedidos.push(String(entrada));
      return new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } });
    }),
  );
  return pedidos;
}

describe("base de la API relativa (el backend sirve la interfaz)", () => {
  it("resuelve contra el origen de la página, sea cual sea el puerto", async () => {
    const pedidos = espiarFetch();

    await new ClienteHttp("/api/v1").get("/mercados");

    // jsdom sirve la página en localhost:3000; lo que importa es que use
    // ESE origen y no uno escrito a mano.
    expect(pedidos[0]).toBe(`${window.location.origin}/api/v1/mercados`);
  });

  it("una base absoluta sigue funcionando (desarrollo con Vite en 5173)", async () => {
    const pedidos = espiarFetch();

    await new ClienteHttp("http://localhost:8000/api/v1").get("/mercados");

    expect(pedidos[0]).toBe("http://localhost:8000/api/v1/mercados");
  });

  it("sin VITE_API_URL el contenedor asume el mismo origen", async () => {
    const pedidos = espiarFetch();

    await crearContenedor("http").catalogo.mercados();

    expect(pedidos[0]).toBe(`${window.location.origin}/api/v1/mercados`);
  });
});
