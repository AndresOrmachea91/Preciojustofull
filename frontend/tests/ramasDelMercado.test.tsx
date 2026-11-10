/**
 * @vitest-environment jsdom
 *
 * C143: al elegir un mercado con varios puestos, el mapa los abre como
 * ramas; cada rama abre la ventana del puesto con sus ofertas y precios.
 * Sin GPS, la zona elegida a mano sirve para ver los mercados cercanos.
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { VerMapa } from "@/aplicacion/casosUso/publico/verMapa";
import { masCercanos, ubicacionValida, ZONAS_DE_LA_PAZ, type Oferta, type PuestoConInventario } from "@/dominio/modelo";
import { PreciosMemoria } from "@/infraestructura/memoria/PreciosMemoria";
import { MapaPuntosVenta, posicionesDeRamas, type RamasDelMercado } from "@/ui/componentes/MapaPuntosVenta";
import { VentanaPuesto } from "@/ui/componentes/VentanaPuesto";

afterEach(cleanup);

describe("posicionesDeRamas", () => {
  it("reparte las ramas en vueltas sin que dos queden encimadas", () => {
    for (const cuantas of [2, 5, 9, 14, 25]) {
      const lugares = posicionesDeRamas(cuantas);
      expect(lugares).toHaveLength(cuantas);
      for (let i = 0; i < lugares.length; i++) {
        const [x, y] = lugares[i]!;
        expect(Math.hypot(x, y)).toBeGreaterThanOrEqual(70);   // lejos del pin del mercado
        for (let j = i + 1; j < lugares.length; j++) {
          const [u, v] = lugares[j]!;
          expect(Math.hypot(x - u, y - v)).toBeGreaterThan(40);
        }
      }
    }
  });
});

describe("MapaPuntosVenta con ramas", () => {
  it("abre los puestos del mercado elegido como ramas y la ventana del que se toca", async () => {
    const memoria = new PreciosMemoria();
    const { marcadores } = await new VerMapa(memoria, memoria).ejecutar("tomate");
    const elegido = marcadores.find((m) => m.mercado.latitud !== undefined)!;
    const ramas: RamasDelMercado = {
      codigo: elegido.mercado.codigo,
      nombre: elegido.mercado.nombre,
      enlace: "#/mercado",
      lista: [
        { clave: "14", numero: "14", titulo: "Puesto 14 · Verduras Rosa", foto: null, precio: 8.5, agotado: false, oferta: true },
        { clave: "22", numero: "22", titulo: "Puesto 22 · Papas Feliciano", foto: null, precio: null, agotado: false, oferta: false },
        { clave: "31", numero: "31", titulo: "Puesto 31 · Frutería", foto: null, precio: 9, agotado: true, oferta: false },
      ],
    };

    render(
      <MapaPuntosVenta
        marcadores={marcadores}
        seleccionado={elegido.mercado.codigo}
        onSeleccionar={() => {}}
        ramas={ramas}
        ventana={() => <p>ventana del mercado</p>}
        ventanaRama={(clave) => <p>ventana del puesto {clave}</p>}
      />,
    );

    await waitFor(() => expect(document.querySelectorAll(".rama").length).toBe(3));
    expect(document.querySelector(".rama--oferta .rama__oferta")).not.toBeNull();
    expect(document.querySelector(".rama--agotado")).not.toBeNull();
    expect(screen.getByText(/3 puestos · 1 con oferta/)).toBeDefined();
    // Con ramas no se abre la ventana del mercado.
    expect(screen.queryByText("ventana del mercado")).toBeNull();

    fireEvent.click(document.querySelector('[aria-label="Puesto 14 · Verduras Rosa"]')!);
    await waitFor(() => expect(screen.getByText("ventana del puesto 14")).toBeDefined());
  });

  it("un mercado sin puestos abre su ventana de siempre", async () => {
    const memoria = new PreciosMemoria();
    const { marcadores } = await new VerMapa(memoria, memoria).ejecutar("tomate");
    const elegido = marcadores.find((m) => m.mercado.latitud !== undefined)!;

    render(
      <MapaPuntosVenta
        marcadores={marcadores}
        seleccionado={elegido.mercado.codigo}
        onSeleccionar={() => {}}
        ramas={{ codigo: elegido.mercado.codigo, nombre: elegido.mercado.nombre, enlace: "#", lista: [] }}
        ventana={() => <p>ventana del mercado</p>}
      />,
    );

    // (La ventana del mercado se abre al terminar el vuelo, que jsdom no anima.)
    await waitFor(() => expect(document.querySelector(".pin--activo")).not.toBeNull());
    expect(document.querySelectorAll(".rama").length).toBe(0);
    expect(screen.queryByText(/toque uno para ver sus precios/)).toBeNull();
  });
});

describe("VentanaPuesto", () => {
  const mercado = {
    codigo: "lanza", nombre: "Mercado Lanza", tipo: "mercado", zona: "Centro", macrodistrito: "Centro",
    codigoPadre: null, nivelPrecio: "minorista",
  } as unknown as Parameters<typeof VentanaPuesto>[0]["mercado"];
  const datos: PuestoConInventario = {
    puesto: {
      id: 1, codigoMercado: "lanza", numero: "B-12", nombre: "Verduras Doña Elena", rubros: ["hortaliza"],
      referencia: "Segundo piso", registrado: true, foto: null, esLocal: false, celular: null,
    },
    articulos: [
      { codigoProducto: "cebolla", nombreProducto: "Cebolla", categoria: "hortaliza", monto: 6, presentacion: "kg",
        precioPorUnidadBase: 6, unidadBase: "kg", disponibilidad: "poco", actualizadoEn: null },
      { codigoProducto: "tomate", nombreProducto: "Tomate", categoria: "hortaliza", monto: 8.5, presentacion: "kg",
        precioPorUnidadBase: 8.5, unidadBase: "kg", disponibilidad: "hay", actualizadoEn: null },
    ],
    total: 2,
  };
  const oferta = {
    id: 7, codigoProducto: "cebolla", nombreProducto: "Cebolla", unidadBase: "kg", codigoMercado: "lanza",
    nombreMercado: "Mercado Lanza", numeroPuesto: "B-12", nombrePuesto: "Verduras Doña Elena", monto: 5.2,
    presentacion: "kg", precioPorUnidadBase: 5.2, desde: new Date().toISOString(),
    hasta: new Date(Date.now() + 50 * 3_600_000).toISOString(), nota: "Hoy llegó fresquito", precioSistema: 6.1,
    procedenciaSistema: "estimado", ahorroPorUnidad: 0.9, ahorroRelativo: 0.15, confirmaron: 0, desmintieron: 0,
  } as Oferta;

  it("muestra sus ofertas, el producto buscado primero y lo que le queda", () => {
    render(<VentanaPuesto mercado={mercado} datos={datos} ofertas={[oferta]} codigoProducto="tomate" />);

    expect(screen.getByText("Puesto B-12 · Verduras Doña Elena")).toBeDefined();
    expect(screen.getByText("★ −15 %")).toBeDefined();
    expect(screen.getByText(/Hoy llegó fresquito/)).toBeDefined();
    const filas = document.querySelectorAll(".ventana__articulos--todos li");
    expect(filas[0]!.textContent).toContain("Tomate");
    expect(filas[0]!.className).toContain("ventana__buscado");
    expect(screen.getByText("Queda poco")).toBeDefined();
    expect(screen.getByRole("link", { name: /Ver su puesto completo/ }).getAttribute("href")).toBe(
      "#/mercado?codigo=lanza&puesto=B-12",
    );
  });
});

describe("Zonas de La Paz", () => {
  it("todas caen dentro de La Paz y El Alto y ordenan los mercados por cercanía", async () => {
    for (const z of ZONAS_DE_LA_PAZ) expect(ubicacionValida(z.latitud, z.longitud)).toBe(true);
    const memoria = new PreciosMemoria();
    const { marcadores } = await new VerMapa(memoria, memoria).ejecutar("tomate");
    const centro = ZONAS_DE_LA_PAZ.find((z) => z.nombre === "Centro")!;
    const cercanos = masCercanos(marcadores, centro);
    expect(cercanos.length).toBeGreaterThan(0);
    for (let i = 1; i < cercanos.length; i++) {
      expect(cercanos[i]!.distanciaKm).toBeGreaterThanOrEqual(cercanos[i - 1]!.distanciaKm);
    }
  });
});
