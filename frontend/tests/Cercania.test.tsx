/**
 * @vitest-environment jsdom
 *
 * "Cerca de mí": la distancia y el orden son del dominio; el GPS se simula
 * (el único que lo toca de verdad es el adaptador de ubicación).
 */
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { distanciaKm, masCercanos, textoDistancia, type MarcadorMapa } from "@/dominio/modelo";
import App from "@/ui/App";

beforeEach(() => {
  window.location.hash = "";
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function gpsEn(latitud: number, longitud: number) {
  vi.stubGlobal("navigator", {
    ...navigator,
    geolocation: { getCurrentPosition: (ok: PositionCallback) => ok({ coords: { latitude: latitud, longitude: longitud } } as GeolocationPosition) },
  });
}

describe("distancias (dominio)", () => {
  it("mide en km y escribe la distancia como se dice", () => {
    // Plaza Murillo → Mercado Rodríguez: un poco más de 1 km.
    const km = distanciaKm({ latitud: -16.4955, longitud: -68.1336 }, { latitud: -16.500192, longitud: -68.138992 });
    expect(km).toBeGreaterThan(0.6);
    expect(km).toBeLessThan(1.2);
    expect(textoDistancia(0.347)).toBe("350 m");
    expect(textoDistancia(1.43)).toBe("1,4 km");
  });

  it("ordena por cercanía y deja fuera los lugares sin precio", () => {
    const punto = (codigo: string, longitud: number, conPrecio = true): MarcadorMapa =>
      ({
        mercado: { codigo, nombre: codigo, latitud: -16.5, longitud },
        precio: conPrecio ? { rango: { centro: 1 } } : null,
      }) as unknown as MarcadorMapa;
    const orden = masCercanos([punto("lejos", -68.2), punto("cerca", -68.131), punto("sin", -68.1301, false)], {
      latitud: -16.5,
      longitud: -68.13,
    }).map((c) => c.marcador.mercado.codigo);
    expect(orden).toEqual(["cerca", "lejos"]);
  });
});

describe("Cerca de mí (interfaz)", () => {
  it("muestra los puntos con precio más cercanos y elige uno en el mapa", async () => {
    gpsEn(-16.4955, -68.1336);
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Cerca de mí" }));

    const lista = await screen.findByRole("region", { name: "Más cerca de usted" });
    const puntos = within(within(lista).getByRole("list")).getAllByRole("button");
    expect(puntos.length).toBeGreaterThan(0);
    expect(puntos[0].textContent).toMatch(/\d+ m|km/);
    expect(puntos[0].textContent).toMatch(/Bs \d/);

    fireEvent.click(puntos[0]);
    expect(puntos[0].getAttribute("aria-pressed")).toBe("true");
  });

  it("fuera de La Paz lo dice en vez de mostrar lugares lejanos", async () => {
    gpsEn(-17.78, -63.18); // Santa Cruz
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Cerca de mí" }));
    expect((await screen.findByRole("alert")).textContent).toMatch(/fuera de La Paz/);
  });
});
